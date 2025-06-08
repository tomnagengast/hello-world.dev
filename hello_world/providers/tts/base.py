"""Base interface for Text-to-Speech providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, Optional
import io


@dataclass
class AudioChunk:
    """Represents an audio chunk from TTS."""
    data: bytes
    is_first: bool = False
    is_final: bool = False
    duration_ms: Optional[int] = None
    format: str = "mp3"


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the TTS provider."""
        pass
        
    @abstractmethod
    def stream_audio(self, text: str) -> Iterator[AudioChunk]:
        """
        Stream audio for the given text.
        
        Args:
            text: The text to convert to speech
            
        Yields:
            AudioChunk objects as audio is generated
        """
        pass
        
    @abstractmethod
    def play_chunk(self, chunk: AudioChunk) -> None:
        """
        Play an audio chunk through speakers.
        
        Args:
            chunk: The audio chunk to play
        """
        pass
        
    @abstractmethod
    def stop_playback(self) -> None:
        """Stop current audio playback."""
        pass
        
    @abstractmethod
    def stop(self) -> None:
        """Stop the TTS provider and clean up resources."""
        pass
        
    @abstractmethod
    def get_status(self) -> dict:
        """Get current status of the TTS provider."""
        pass