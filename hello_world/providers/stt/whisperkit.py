"""WhisperKit STT provider implementation with sounddevice for low latency."""

import subprocess
import threading
import time
import queue
import collections
import numpy as np
import sounddevice as sd
import soundfile as sf
import tempfile
import os
from typing import Iterator, Optional, Deque
import structlog

from .base import STTProvider, Transcript
from ...utils.interruption_handler import InterruptionHandler


logger = structlog.get_logger()


class RingBuffer:
    """Lock-free ring buffer for audio data."""
    
    def __init__(self, size: int):
        self.size = size
        self.data = np.zeros(size, dtype=np.float32)
        self.write_pos = 0
        self.read_pos = 0
        self._lock = threading.Lock()
    
    def write(self, audio_data: np.ndarray) -> int:
        """Write audio data to buffer. Returns number of samples written."""
        with self._lock:
            available = self.size - self.write_pos + self.read_pos
            if self.write_pos >= self.read_pos:
                available = self.size - self.write_pos + self.read_pos
            else:
                available = self.read_pos - self.write_pos
            
            write_len = min(len(audio_data), available)
            if write_len == 0:
                return 0
            
            # Handle wraparound
            if self.write_pos + write_len <= self.size:
                self.data[self.write_pos:self.write_pos + write_len] = audio_data[:write_len]
            else:
                first_part = self.size - self.write_pos
                self.data[self.write_pos:] = audio_data[:first_part]
                self.data[:write_len - first_part] = audio_data[first_part:write_len]
            
            self.write_pos = (self.write_pos + write_len) % self.size
            return write_len
    
    def read(self, num_samples: int) -> np.ndarray:
        """Read audio data from buffer."""
        with self._lock:
            available = self.write_pos - self.read_pos
            if self.write_pos < self.read_pos:
                available = self.size - self.read_pos + self.write_pos
            
            read_len = min(num_samples, available)
            if read_len == 0:
                return np.array([], dtype=np.float32)
            
            # Handle wraparound
            if self.read_pos + read_len <= self.size:
                result = self.data[self.read_pos:self.read_pos + read_len].copy()
            else:
                first_part = self.size - self.read_pos
                result = np.concatenate([
                    self.data[self.read_pos:],
                    self.data[:read_len - first_part]
                ])
            
            self.read_pos = (self.read_pos + read_len) % self.size
            return result
    
    def available_read(self) -> int:
        """Get number of samples available to read."""
        with self._lock:
            available = self.write_pos - self.read_pos
            if self.write_pos < self.read_pos:
                available = self.size - self.read_pos + self.write_pos
            return available


class WhisperKitProvider(STTProvider):
    """
    WhisperKit STT provider using sounddevice for low-latency audio capture.
    """
    
    def __init__(self, 
                 model: str = "large-v3_turbo",
                 vad_enabled: bool = True,
                 compute_units: str = "cpuAndNeuralEngine",
                 whisperkit_path: str = "/opt/homebrew/bin/whisperkit-cli",
                 sample_rate: int = 16000,
                 channels: int = 1,
                 block_duration: float = 0.1,  # 100ms blocks for low latency
                 buffer_duration: float = 10.0):  # 10 second ring buffer
        self.model = model
        self.vad_enabled = vad_enabled
        self.compute_units = compute_units
        self.whisperkit_path = whisperkit_path
        self.sample_rate = sample_rate
        self.channels = channels
        self.block_duration = block_duration
        self.buffer_duration = buffer_duration
        
        # Calculate buffer and block sizes
        self.block_size = int(sample_rate * block_duration)
        self.buffer_size = int(sample_rate * buffer_duration)
        
        # Audio processing components
        self.ring_buffer = RingBuffer(self.buffer_size)
        self.audio_queue: queue.Queue = queue.Queue(maxsize=100)
        self.interruption_handler = InterruptionHandler(sample_rate=sample_rate)
        
        # State management
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.is_recording = False
        self.audio_stream: Optional[sd.InputStream] = None
        self.processing_thread: Optional[threading.Thread] = None
        
        # Performance metrics
        self.audio_callback_count = 0
        self.last_audio_time = 0
        self.processing_latency_ms = 0
        
    def audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """Low-latency audio callback for sounddevice."""
        try:
            if status:
                logger.warning("Audio callback status", status=status)
            
            # Convert to mono if needed
            if indata.shape[1] > 1:
                audio_data = np.mean(indata, axis=1)
            else:
                audio_data = indata.flatten()
            
            # Write to ring buffer
            written = self.ring_buffer.write(audio_data)
            if written < len(audio_data):
                logger.warning("Ring buffer overflow", 
                             requested=len(audio_data), 
                             written=written)
            
            # Process for interruption detection
            if len(audio_data) >= self.interruption_handler.frame_size:
                # Process in frame-sized chunks for VAD
                frame_size = self.interruption_handler.frame_size
                for i in range(0, len(audio_data) - frame_size + 1, frame_size):
                    frame = audio_data[i:i + frame_size]
                    if self.interruption_handler.process_audio_frame(frame):
                        # Voice detected - trigger interruption
                        self.interruption_handler.trigger_interruption()
            
            # Update metrics
            self.audio_callback_count += 1
            self.last_audio_time = time.time()
            
            # Queue audio block for processing
            try:
                self.audio_queue.put_nowait(audio_data.copy())
            except queue.Full:
                logger.warning("Audio queue full, dropping frame")
                
        except Exception as e:
            logger.error("Audio callback error", error=str(e))
    
    def initialize(self) -> None:
        """Initialize WhisperKit subprocess and audio capture."""
        logger.info("Initializing WhisperKit provider with sounddevice", 
                   model=self.model,
                   sample_rate=self.sample_rate,
                   block_duration=self.block_duration)
        
        # Check if sounddevice can access the microphone
        try:
            devices = sd.query_devices()
            default_input = sd.query_devices(kind='input')
            logger.info("Audio device info", 
                       default_input=default_input['name'],
                       sample_rate=default_input['default_samplerate'])
        except Exception as e:
            logger.error("Failed to query audio devices", error=str(e))
            raise
        
        # Initialize audio stream
        try:
            self.audio_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.float32,
                blocksize=self.block_size,
                callback=self.audio_callback,
                latency='low'  # Request low latency
            )
            logger.info("Audio stream created", 
                       blocksize=self.block_size,
                       latency=self.audio_stream.latency)
        except Exception as e:
            logger.error("Failed to create audio stream", error=str(e))
            raise
        
        # Start WhisperKit subprocess
        self._start_whisperkit()
        
        # Start audio processing thread
        self.is_running = True
        self.processing_thread = threading.Thread(target=self._audio_processing_loop, daemon=True)
        self.processing_thread.start()
        
        # Start audio capture
        self.audio_stream.start()
        self.is_recording = True
        
        logger.info("WhisperKit provider initialized successfully")
    
    def _start_whisperkit(self) -> None:
        """Start WhisperKit subprocess."""
        # Build command
        cmd = [
            self.whisperkit_path,
            "transcribe",
            "--stream",
            "--model", self.model,
            "--audio-encoder-compute-units", self.compute_units,
            "--text-decoder-compute-units", self.compute_units
        ]
        
        if self.vad_enabled:
            cmd.extend(["--chunking-strategy", "vad"])
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,  # Binary mode for audio data
                bufsize=0   # Unbuffered
            )
            
            logger.info("WhisperKit subprocess started", 
                       pid=self.process.pid,
                       command=" ".join(cmd))
            
        except Exception as e:
            logger.error("Failed to start WhisperKit", error=str(e))
            raise
    
    def _audio_processing_loop(self) -> None:
        """Process audio chunks and stream to WhisperKit."""
        chunk_buffer = []
        chunk_duration_samples = int(self.sample_rate * 2.0)  # 2 second chunks
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_filename = temp_file.name
        
        try:
            while self.is_running:
                try:
                    # Get audio data from queue with timeout
                    audio_data = self.audio_queue.get(timeout=0.5)
                    chunk_buffer.extend(audio_data)
                    
                    # Process when we have enough data
                    if len(chunk_buffer) >= chunk_duration_samples:
                        # Convert to numpy array
                        chunk_array = np.array(chunk_buffer[:chunk_duration_samples], dtype=np.float32)
                        chunk_buffer = chunk_buffer[chunk_duration_samples:]
                        
                        # Save to temporary WAV file
                        sf.write(temp_filename, chunk_array, self.sample_rate)
                        
                        # Send file path to WhisperKit via stdin
                        if self.process and self.process.stdin:
                            try:
                                self.process.stdin.write(f"{temp_filename}\n".encode())
                                self.process.stdin.flush()
                            except Exception as e:
                                logger.error("Failed to send audio to WhisperKit", error=str(e))
                                break
                                
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error("Audio processing error", error=str(e))
                    continue
                    
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_filename)
            except OSError:
                pass
    
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
                text = line.decode().strip()
                if not text:
                    continue
                
                # Detect speech start
                is_speech_start = not speech_started and len(text) > 0
                if is_speech_start:
                    speech_started = True
                
                # Detect speech end
                if speech_started and len(text) == 0:
                    speech_started = False
                
                # Calculate processing latency
                processing_time = time.time()
                latency_ms = (processing_time - self.last_audio_time) * 1000 if self.last_audio_time else None
                
                # Create transcript
                transcript = Transcript(
                    text=text,
                    timestamp=processing_time,
                    is_final=True,
                    is_speech_start=is_speech_start,
                    confidence=None,
                    latency=latency_ms
                )
                
                yield transcript
                last_text = text
                
            except Exception as e:
                logger.error("Error processing WhisperKit output", error=str(e))
                continue
    
    def stop(self) -> None:
        """Stop WhisperKit subprocess and audio capture."""
        logger.info("Stopping WhisperKit provider")
        
        self.is_running = False
        self.is_recording = False
        
        # Stop audio stream
        if self.audio_stream:
            try:
                self.audio_stream.stop()
                self.audio_stream.close()
            except Exception as e:
                logger.error("Error stopping audio stream", error=str(e))
            self.audio_stream = None
        
        # Wait for processing thread
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=2)
        
        # Terminate WhisperKit process
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("WhisperKit didn't terminate, killing process")
                self.process.kill()
                self.process.wait()
            except Exception as e:
                logger.error("Error stopping WhisperKit process", error=str(e))
            
            self.process = None
        
        logger.info("WhisperKit provider stopped")
    
    def get_status(self) -> dict:
        """Get WhisperKit provider status."""
        vad_stats = self.interruption_handler.get_voice_activity_stats()
        
        return {
            "provider": "whisperkit",
            "model": self.model,
            "is_running": self.is_running,
            "is_recording": self.is_recording,
            "process_alive": self.process is not None and self.process.poll() is None,
            "audio_stream_active": self.audio_stream is not None and self.audio_stream.active,
            "vad_enabled": self.vad_enabled,
            "compute_units": self.compute_units,
            "sample_rate": self.sample_rate,
            "block_duration": self.block_duration,
            "buffer_duration": self.buffer_duration,
            "audio_callback_count": self.audio_callback_count,
            "ring_buffer_available": self.ring_buffer.available_read(),
            "audio_queue_size": self.audio_queue.qsize(),
            "vad_stats": vad_stats,
            "last_audio_time": self.last_audio_time,
            "processing_latency_ms": self.processing_latency_ms
        }