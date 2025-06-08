"""ElevenLabs TTS provider implementation."""

import os
from typing import Iterator, Optional
import pygame
from io import BytesIO
import threading
import queue
import time
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
import structlog

from .base import TTSProvider, AudioChunk


logger = structlog.get_logger()


class ElevenLabsProvider(TTSProvider):
    """
    ElevenLabs TTS provider with streaming support.
    """

    def __init__(
        self,
        voice_id: str = "pNInz6obpgDQGcFmaJgB",  # Adam voice
        model_id: str = "eleven_flash_v2_5",
        output_format: str = "mp3_22050_32",
        streaming: bool = True,
        stability: float = 0.5,
        similarity_boost: float = 0.8,
        style: float = 0.0,
        speed: float = 1.0,
        use_speaker_boost: bool = True,
    ):
        self.voice_id = voice_id
        self.model_id = model_id
        self.output_format = output_format
        self.streaming = streaming

        # Voice settings
        self.voice_settings = VoiceSettings(
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
            use_speaker_boost=use_speaker_boost,
            speed=speed,
        )

        self.client: Optional[ElevenLabs] = None
        self.is_playing = False
        self.should_stop = False
        self.audio_queue = queue.Queue()
        self.playback_thread: Optional[threading.Thread] = None

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
        pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=1024)
        pygame.mixer.init()

        # Start playback thread
        self.should_stop = False
        self.playback_thread = threading.Thread(
            target=self._playback_worker, daemon=True
        )
        self.playback_thread.start()

        logger.info("ElevenLabs provider initialized")

    def stream_audio(self, text: str) -> Iterator[AudioChunk]:
        """Stream audio from ElevenLabs."""
        if not self.client:
            raise RuntimeError("ElevenLabs not initialized")

        logger.debug("Generating TTS audio", text_length=len(text))

        try:
            # Generate audio - for now, get full audio first, then chunk it
            # In production, we would want to use proper streaming
            audio_bytes = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text,
                model_id=self.model_id,
                output_format=self.output_format,
                voice_settings=self.voice_settings,
            )

            # Convert to bytes if needed
            if hasattr(audio_bytes, "content"):
                audio_data = audio_bytes.content  # type: ignore[attr-defined]
            elif isinstance(audio_bytes, (bytes, bytearray)):
                audio_data = bytes(audio_bytes)
            else:
                # Handle generator or iterator response
                audio_data = b"".join(audio_bytes)

            # Chunk the data for streaming simulation
            chunk_size = 4096  # 4KB chunks
            total_bytes = len(audio_data)
            is_first = True

            for i in range(0, total_bytes, chunk_size):
                if self.should_stop:
                    logger.debug("TTS generation stopped due to interruption")
                    break

                chunk_data = audio_data[i : i + chunk_size]

                yield AudioChunk(
                    data=chunk_data,
                    is_first=is_first,
                    is_final=False,
                    format=self.output_format.split("_")[0],  # Extract format
                )

                is_first = False

            # Send final chunk if not stopped
            if not self.should_stop:
                yield AudioChunk(data=b"", is_first=False, is_final=True)

                logger.debug("TTS generation complete", total_bytes=total_bytes)

        except Exception as e:
            logger.error("Error generating TTS audio", error=str(e))
            raise

    def play_chunk(self, chunk: AudioChunk) -> None:
        """Play audio chunk through speakers."""
        if not chunk.data and not chunk.is_final:
            return

        try:
            # Add chunk to playback queue
            self.audio_queue.put(chunk, timeout=1.0)

            if chunk.is_first:
                self.is_playing = True
                logger.debug("Started audio playback")

        except queue.Full:
            logger.warning("Audio queue full, dropping chunk")
        except Exception as e:
            logger.error("Error queuing audio chunk", error=str(e))
            raise

    def _playback_worker(self) -> None:
        """Worker thread for audio playback."""
        audio_buffer = BytesIO()
        playing = False

        while not self.should_stop:
            try:
                # Get chunk from queue with timeout
                chunk = self.audio_queue.get(timeout=0.1)

                if chunk.data:
                    # Add chunk data to buffer
                    audio_buffer.write(chunk.data)

                    # Start playback on first chunk
                    if chunk.is_first and not playing:
                        audio_buffer.seek(0)
                        pygame.mixer.music.load(audio_buffer)
                        pygame.mixer.music.play()
                        playing = True

                # Handle final chunk
                if chunk.is_final:
                    # Wait for current playback to finish
                    while pygame.mixer.music.get_busy() and not self.should_stop:
                        time.sleep(0.01)

                    self.is_playing = False
                    playing = False
                    audio_buffer = BytesIO()  # Reset buffer
                    logger.debug("Audio playback completed")

                self.audio_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error("Error in playback worker", error=str(e))
                self.is_playing = False
                playing = False

    def stop_playback(self) -> None:
        """Stop current audio playback."""
        logger.debug("Stopping audio playback")

        if self.is_playing:
            pygame.mixer.music.stop()
            self.is_playing = False

            # Clear audio queue
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.task_done()
                except queue.Empty:
                    break

    def stop(self) -> None:
        """Stop ElevenLabs provider."""
        logger.info("Stopping ElevenLabs provider")

        # Signal threads to stop
        self.should_stop = True

        # Stop playback
        self.stop_playback()

        # Wait for playback thread to finish
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=2.0)

        # Cleanup
        pygame.mixer.quit()
        self.client = None

    def get_status(self) -> dict:
        """Get ElevenLabs provider status."""
        return {
            "provider": "elevenlabs",
            "voice_id": self.voice_id,
            "model_id": self.model_id,
            "is_playing": self.is_playing,
            "should_stop": self.should_stop,
            "queue_size": self.audio_queue.qsize(),
            "playback_thread_alive": self.playback_thread.is_alive()
            if self.playback_thread
            else False,
            "initialized": self.client is not None,
            "mixer_initialized": pygame.mixer.get_init() is not None,
        }
