"""Interruption handling for conversation flow."""

import threading
import time
from typing import Optional, Callable, Set
import structlog


logger = structlog.get_logger()


class InterruptionHandler:
    """Handles interruption detection and coordination."""
    
    def __init__(self, cooldown_period: float = 1.0):
        self.is_interrupted = False
        self.cooldown_period = cooldown_period
        self._lock = threading.Lock()
        self._callbacks: Set[Callable[[], None]] = set()
        self._last_interruption_time = 0
        self._tts_playing = False
        
    def set_tts_playing(self, playing: bool) -> None:
        """Set TTS playback state for interruption detection."""
        with self._lock:
            self._tts_playing = playing
            
    def is_tts_playing(self) -> bool:
        """Check if TTS is currently playing."""
        with self._lock:
            return self._tts_playing
            
    def detect_speech_interruption(self, transcript_text: str, is_speech_start: bool) -> bool:
        """
        Detect if user speech should interrupt TTS playback.
        
        Args:
            transcript_text: The transcribed text from STT
            is_speech_start: Whether this is the start of a new speech segment
            
        Returns:
            True if interruption should be triggered
        """
        with self._lock:
            # Only interrupt if TTS is playing and we detect meaningful speech
            if not self._tts_playing:
                return False
                
            # Check cooldown period to avoid rapid interruptions
            current_time = time.time()
            if (self._last_interruption_time > 0 and 
                current_time - self._last_interruption_time < self.cooldown_period):
                return False
                
            # Trigger interruption on speech start with meaningful content
            if is_speech_start and len(transcript_text.strip()) > 0:
                logger.info("Speech interruption detected", 
                           text=transcript_text[:50],
                           tts_playing=self._tts_playing)
                return True
                
            # Also trigger on meaningful ongoing speech (fallback)
            if len(transcript_text.strip()) > 3:  # Minimum meaningful text length
                logger.info("Ongoing speech interruption detected", 
                           text=transcript_text[:50])
                return True
                
            return False
        
    def trigger_interruption(self, reason: str = "manual") -> None:
        """Trigger an interruption event."""
        with self._lock:
            if self.is_interrupted:
                # Already interrupted
                return
                
            self.is_interrupted = True
            self._last_interruption_time = time.time()
            
        logger.info("Interruption triggered", reason=reason)
        
        # Execute callbacks in background to avoid blocking
        def execute_callbacks():
            for callback in self._callbacks.copy():  # Copy to avoid modification during iteration
                try:
                    callback()
                except Exception as e:
                    logger.error("Interruption callback error", error=str(e))
                    
        callback_thread = threading.Thread(target=execute_callbacks, daemon=True)
        callback_thread.start()
                
    def reset(self) -> None:
        """Reset interruption state."""
        with self._lock:
            self.is_interrupted = False
            
        logger.debug("Interruption state reset")
        
    def is_interrupted_atomic(self) -> bool:
        """Check interruption state atomically."""
        with self._lock:
            return self.is_interrupted
            
    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called on interruption."""
        with self._lock:
            self._callbacks.add(callback)
        logger.debug("Interruption callback registered", total_callbacks=len(self._callbacks))
        
    def unregister_callback(self, callback: Callable[[], None]) -> None:
        """Unregister an interruption callback."""
        with self._lock:
            self._callbacks.discard(callback)
        logger.debug("Interruption callback unregistered", total_callbacks=len(self._callbacks))
            
    def get_time_since_interruption(self) -> Optional[float]:
        """Get time since last interruption in seconds."""
        if self._last_interruption_time == 0:
            return None
        return time.time() - self._last_interruption_time
        
    def get_status(self) -> dict:
        """Get interruption handler status."""
        with self._lock:
            return {
                "is_interrupted": self.is_interrupted,
                "tts_playing": self._tts_playing,
                "callback_count": len(self._callbacks),
                "last_interruption_time": self._last_interruption_time,
                "time_since_interruption": self.get_time_since_interruption(),
                "cooldown_period": self.cooldown_period
            }


class AudioInterruptionDetector:
    """Specific detector for audio-based interruptions."""
    
    def __init__(self, interruption_handler: InterruptionHandler):
        self.interruption_handler = interruption_handler
        self.is_monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        
    def start_monitoring(self, stt_provider, tts_provider) -> None:
        """Start monitoring for audio interruptions."""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        
        # Register TTS stop callback
        def stop_tts():
            try:
                tts_provider.stop_playback()
                self.interruption_handler.set_tts_playing(False)
                logger.info("TTS playback stopped due to interruption")
            except Exception as e:
                logger.error("Error stopping TTS on interruption", error=str(e))
                
        self.interruption_handler.register_callback(stop_tts)
        
        # Start monitoring thread
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, 
            args=(stt_provider,), 
            daemon=True
        )
        self._monitor_thread.start()
        
        logger.info("Audio interruption monitoring started")
        
    def _monitor_loop(self, stt_provider) -> None:
        """Main monitoring loop for STT transcripts."""
        try:
            for transcript in stt_provider.stream_transcripts():
                if not self.is_monitoring:
                    break
                    
                # Check for speech interruption
                should_interrupt = self.interruption_handler.detect_speech_interruption(
                    transcript.text, 
                    transcript.is_speech_start
                )
                
                if should_interrupt:
                    self.interruption_handler.trigger_interruption("speech_detected")
                    
        except Exception as e:
            logger.error("Error in interruption monitoring loop", error=str(e))
        finally:
            self.is_monitoring = False
            
    def stop_monitoring(self) -> None:
        """Stop monitoring for audio interruptions."""
        self.is_monitoring = False
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)
            
        logger.info("Audio interruption monitoring stopped")