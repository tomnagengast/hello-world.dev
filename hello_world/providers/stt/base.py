"""Base interface for Speech-to-Text providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, Optional


@dataclass
class Transcript:
    """Represents a transcript segment from STT."""

    text: str
    timestamp: float
    is_final: bool
    is_speech_start: bool = False
    confidence: Optional[float] = None
    latency: Optional[float] = None


class STTProvider(ABC):
    """Abstract base class for STT providers."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the STT provider."""
        pass

    @abstractmethod
    def stream_transcripts(self) -> Iterator[Transcript]:
        """
        Stream transcripts from audio input.

        Yields:
            Transcript objects as audio is processed
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the STT provider and clean up resources."""
        pass

    @abstractmethod
    def get_status(self) -> dict:
        """Get current status of the STT provider."""
        pass
