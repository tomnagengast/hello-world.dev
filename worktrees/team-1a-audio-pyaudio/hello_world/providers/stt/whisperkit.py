"""WhisperKit STT provider implementation."""

import subprocess
import threading
import time
import json
import pyaudio
import wave
import tempfile
import os
from typing import Iterator, Optional
import structlog

from .base import STTProvider, Transcript


logger = structlog.get_logger()


class WhisperKitProvider(STTProvider):
    """
    WhisperKit STT provider using subprocess streaming.
    """
    
    def __init__(self, 
                 model: str = "large-v3_turbo",
                 vad_enabled: bool = True,
                 compute_units: str = "cpuAndNeuralEngine",
                 whisperkit_path: str = "/opt/homebrew/bin/whisperkit-cli",
                 sample_rate: int = 16000,
                 chunk_duration: int = 30):
        self.model = model
        self.vad_enabled = vad_enabled
        self.compute_units = compute_units
        self.whisperkit_path = whisperkit_path
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.output_thread: Optional[threading.Thread] = None
        self.audio_thread: Optional[threading.Thread] = None
        
        # Audio capture settings
        self.audio = None
        self.temp_file = None
        self.recording = False
        
    def initialize(self) -> None:
        """Initialize WhisperKit subprocess and audio capture."""
        logger.info("Initializing WhisperKit provider", model=self.model)
        
        # Initialize PyAudio
        try:
            self.audio = pyaudio.PyAudio()
            logger.info("PyAudio initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize PyAudio", error=str(e))
            raise
        
        # Create temporary file for audio input
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        self.temp_file.close()
        
        # Build WhisperKit command
        cmd = [
            self.whisperkit_path,
            "transcribe",
            "--stream",
            "--model", self.model,
            "--audio-encoder-compute-units", self.compute_units,
            "--text-decoder-compute-units", self.compute_units,
            "--input-audio-file", self.temp_file.name
        ]
        
        if self.vad_enabled:
            cmd.extend(["--chunking-strategy", "vad"])
            
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )
            
            self.is_running = True
            logger.info("WhisperKit subprocess started")
            
            # Start audio capture
            self._start_audio_capture()
            
        except Exception as e:
            logger.error("Failed to start WhisperKit", error=str(e))
            self._cleanup()
            raise
            
    def _start_audio_capture(self) -> None:
        """Start continuous audio capture in background thread."""
        self.recording = True
        self.audio_thread = threading.Thread(target=self._audio_capture_loop, daemon=True)
        self.audio_thread.start()
        logger.info("Audio capture started")
        
    def _audio_capture_loop(self) -> None:
        """Continuous audio capture loop."""
        try:
            # Configure audio stream
            chunk_size = 1024
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,  # Mono
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=chunk_size
            )
            
            frames = []
            chunk_count = 0
            frames_per_chunk = (self.sample_rate * self.chunk_duration) // chunk_size
            
            logger.info("Audio stream opened", 
                       sample_rate=self.sample_rate, 
                       chunk_duration=self.chunk_duration)
            
            while self.recording:
                try:
                    data = stream.read(chunk_size, exception_on_overflow=False)
                    frames.append(data)
                    chunk_count += 1
                    
                    # Save chunk when duration reached
                    if chunk_count >= frames_per_chunk:
                        self._save_audio_chunk(frames)
                        frames = []
                        chunk_count = 0
                        
                except Exception as e:
                    logger.error("Error reading audio", error=str(e))
                    continue
                    
        except Exception as e:
            logger.error("Audio capture failed", error=str(e))
        finally:
            if 'stream' in locals():
                stream.stop_stream()
                stream.close()
                
    def _save_audio_chunk(self, frames: list) -> None:
        """Save audio frames to temporary file for WhisperKit."""
        try:
            with wave.open(self.temp_file.name, 'wb') as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(frames))
                
        except Exception as e:
            logger.error("Failed to save audio chunk", error=str(e))
    
    def stream_transcripts(self) -> Iterator[Transcript]:
        """Stream transcripts from WhisperKit output."""
        if not self.process:
            raise RuntimeError("WhisperKit not initialized")
            
        last_text = ""
        speech_started = False
        
        while self.is_running:
            try:
                line = self.process.stdout.readline()
                if not line:
                    if self.process.poll() is not None:
                        logger.warning("WhisperKit process terminated")
                        break
                    continue
                    
                # Parse WhisperKit output
                line = line.strip()
                if not line:
                    continue
                    
                # Try to parse as JSON (WhisperKit may output JSON)
                try:
                    data = json.loads(line)
                    text = data.get('text', '').strip()
                except json.JSONDecodeError:
                    # Fallback to plain text
                    text = line
                    
                if not text:
                    continue
                    
                # Detect speech start (first non-empty transcript after silence)
                is_speech_start = not speech_started and len(text) > 0
                if is_speech_start:
                    speech_started = True
                    
                # Detect speech end (empty transcript after speech)
                if speech_started and len(text) == 0:
                    speech_started = False
                    
                # Create transcript
                transcript = Transcript(
                    text=text,
                    timestamp=time.time(),
                    is_final=True,  # WhisperKit streaming outputs final transcripts
                    is_speech_start=is_speech_start,
                    confidence=None,  # WhisperKit doesn't provide confidence in stream mode
                    latency=None  # Calculate if needed
                )
                
                yield transcript
                last_text = text
                
            except Exception as e:
                logger.error("Error processing WhisperKit output", error=str(e))
                continue
        
    def _cleanup(self) -> None:
        """Clean up resources."""
        # Stop audio capture
        self.recording = False
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=2)
            
        # Clean up PyAudio
        if self.audio:
            self.audio.terminate()
            self.audio = None
            
        # Remove temporary file
        if self.temp_file and os.path.exists(self.temp_file.name):
            try:
                os.unlink(self.temp_file.name)
            except OSError:
                pass
                
    def stop(self) -> None:
        """Stop WhisperKit subprocess."""
        logger.info("Stopping WhisperKit provider")
        
        self.is_running = False
        
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("WhisperKit didn't terminate, killing process")
                self.process.kill()
                self.process.wait()
                
            self.process = None
            
        self._cleanup()
            
    def get_status(self) -> dict:
        """Get WhisperKit provider status."""
        return {
            "provider": "whisperkit",
            "model": self.model,
            "is_running": self.is_running,
            "process_alive": self.process is not None and self.process.poll() is None,
            "recording": self.recording,
            "audio_initialized": self.audio is not None,
            "vad_enabled": self.vad_enabled,
            "compute_units": self.compute_units,
            "sample_rate": self.sample_rate,
            "chunk_duration": self.chunk_duration
        }