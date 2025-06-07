"""Base interface for AI providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, Optional, List


@dataclass
class AIResponse:
    """Represents a response chunk from the AI provider."""
    text: str
    is_first: bool = False
    is_final: bool = False
    full_text: Optional[str] = None  # Complete response when is_final=True
    metadata: Optional[dict] = None


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    def __init__(self, system_prompt: str, streaming: bool = True):
        self.system_prompt = system_prompt
        self.streaming = streaming
        self.conversation_history: List[dict] = []
        
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the AI provider."""
        pass
        
    @abstractmethod
    def stream_response(self, user_input: str) -> Iterator[AIResponse]:
        """
        Stream AI response for the given user input.
        
        Args:
            user_input: The user's text input
            
        Yields:
            AIResponse objects as the response is generated
        """
        pass
        
    @abstractmethod
    def stop_streaming(self) -> None:
        """Stop current streaming response."""
        pass
        
    @abstractmethod
    def stop(self) -> None:
        """Stop the AI provider and clean up resources."""
        pass
        
    @abstractmethod
    def get_status(self) -> dict:
        """Get current status of the AI provider."""
        pass
        
    def add_to_history(self, role: str, content: str) -> None:
        """Add a message to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()