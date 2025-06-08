"""ElevenLabs TTS provider implementation."""

import os
import threading
from typing import Iterator, Optional
import pygame
from io import BytesIO
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
import structlog

from .base import TTSProvider, AudioChunk


logger = structlog.get_logger()


class ElevenLabsProvider(TTSProvider):
    """
    ElevenLabs TTS provider with streaming support.
    """
    
    def __init__(self, 
                 voice_id: str = "pNInz6obpgDQGcFmaJgB",  # Adam voice
                 model_id: str = "eleven_flash_v2_5",
                 output_format: str = "mp3_22050_32",
                 streaming: bool = True):
        self.voice_id = voice_id
        self.model_id = model_id
        self.output_format = output_format
        self.streaming = streaming
        
        self.client: Optional[ElevenLabs] = None
        self.is_playing = False
        self.audio_buffer = BytesIO()
        self._playback_lock = threading.Lock()
        self._stop_requested = False
        
    def initialize(self) -> None:
        """Initialize ElevenLabs client and pygame mixer."""
        logger.info("Initializing ElevenLabs provider", voice_id=self.voice_id)
        
        # Get API key
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable not set")
            
        # Initialize client
        self.client = ElevenLabs(api_key=api_key)
        
        # Initialize pygame mixer for audio playback
        try:
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            logger.info("Pygame mixer initialized")
        except Exception as e:
            logger.error("Failed to initialize pygame mixer", error=str(e))
            raise
        
        logger.info("ElevenLabs provider initialized")
        
    def stream_audio(self, text: str) -> Iterator[AudioChunk]:
        """Stream audio from ElevenLabs."""
        if not self.client:
            raise RuntimeError("ElevenLabs not initialized")
            
        logger.debug("Generating TTS audio", text_length=len(text))
        
        try:
            # Configure voice settings
            voice_settings = VoiceSettings(
                stability=0.5,
                similarity_boost=0.8,
                style=0.0,
                use_speaker_boost=True,
                speed=1.0
            )
            
            # Stream audio
            response = self.client.text_to_speech.stream(
                voice_id=self.voice_id,
                text=text,
                model_id=self.model_id,
                output_format=self.output_format,
                voice_settings=voice_settings
            )
            
            is_first = True
            total_bytes = 0
            
            for chunk_data in response:
                if chunk_data:
                    total_bytes += len(chunk_data)
                    
                    yield AudioChunk(
                        data=chunk_data,
                        is_first=is_first,
                        is_final=False,
                        format=self.output_format.split('_')[0]  # Extract format
                    )
                    
                    is_first = False
                    
            # Send final chunk
            yield AudioChunk(
                data=b'',
                is_first=False,
                is_final=True,
                format=self.output_format.split('_')[0]
            )
            
            logger.debug("TTS generation complete", total_bytes=total_bytes)
            
        except Exception as e:
            logger.error("Error generating TTS audio", error=str(e))
            raise
        
    def play_chunk(self, chunk: AudioChunk) -> None:
        """Play audio chunk through speakers."""
        with self._playback_lock:
            if self._stop_requested:
                logger.debug("Playback stopped, skipping chunk")
                return
                
            if not chunk.data and not chunk.is_final:
                return
                
            try:
                # Add chunk to buffer
                if chunk.data:
                    self.audio_buffer.write(chunk.data)
                
                # If this is the first chunk, start playback
                if chunk.is_first:
                    self.audio_buffer.seek(0)
                    pygame.mixer.music.load(self.audio_buffer)
                    pygame.mixer.music.play()
                    self.is_playing = True
                    logger.debug("Started audio playback")
                    
                # If final chunk, wait for playback to complete
                if chunk.is_final:
                    # Start a background thread to monitor playback completion
                    monitor_thread = threading.Thread(
                        target=self._monitor_playback_completion, 
                        daemon=True
                    )
                    monitor_thread.start()
                    
            except Exception as e:
                logger.error("Error playing audio chunk", error=str(e))
                self.is_playing = False
                raise
                
    def _monitor_playback_completion(self) -> None:
        """Monitor playback completion in background thread."""
        try:
            while pygame.mixer.music.get_busy() and self.is_playing and not self._stop_requested:
                pygame.time.wait(100)
                
            with self._playback_lock:
                if not self._stop_requested:
                    logger.debug("Audio playback completed")
                    
                self.is_playing = False
                self.audio_buffer = BytesIO()  # Reset buffer
                
        except Exception as e:
            logger.error("Error monitoring playback", error=str(e))
            self.is_playing = False
            
    def stop_playback(self) -> None:
        """Stop current audio playback immediately."""
        logger.debug("Stopping audio playback")
        
        with self._playback_lock:
            self._stop_requested = True
            
            if self.is_playing:
                try:
                    pygame.mixer.music.stop()
                    logger.debug("Pygame music stopped")
                except Exception as e:
                    logger.error("Error stopping pygame music", error=str(e))
                    
                self.is_playing = False
                self.audio_buffer = BytesIO()  # Reset buffer
                
        # Reset stop flag after a short delay
        def reset_stop_flag():
            threading.Timer(0.5, lambda: setattr(self, '_stop_requested', False)).start()
        reset_stop_flag()
            
    def stop(self) -> None:
        """Stop ElevenLabs provider."""
        logger.info("Stopping ElevenLabs provider")
        
        self.stop_playback()
        
        try:
            pygame.mixer.quit()
        except Exception as e:
            logger.error("Error quitting pygame mixer", error=str(e))
            
        self.client = None
        
    def get_status(self) -> dict:
        """Get ElevenLabs provider status."""
        mixer_initialized = False
        try:
            mixer_initialized = pygame.mixer.get_init() is not None
        except:
            pass
            
        return {
            "provider": "elevenlabs",
            "voice_id": self.voice_id,
            "model_id": self.model_id,
            "is_playing": self.is_playing,
            "stop_requested": self._stop_requested,
            "initialized": self.client is not None,
            "mixer_initialized": mixer_initialized,
            "output_format": self.output_format
        }