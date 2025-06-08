"""
Mock provider implementations for testing the conversation system.
"""

import time
import threading
from typing import Iterator
from hello_world.providers.stt.base import STTProvider, Transcript
from hello_world.providers.ai.base import AIProvider, AIResponse
from hello_world.providers.tts.base import TTSProvider, AudioChunk


class MockSTTProvider(STTProvider):
    """Mock STT provider that generates fake transcripts."""
    
    def __init__(self):
        self.is_running = False
        self.mock_transcripts = [
            "Hello, how are you today?",
            "What's the weather like?",
            "Can you help me with a task?",
            "Tell me a joke.",
            "What time is it?"
        ]
        self.transcript_index = 0
        
    def initialize(self) -> None:
        """Initialize mock STT provider."""
        self.is_running = True
        
    def stream_transcripts(self) -> Iterator[Transcript]:
        """Generate mock transcripts with realistic timing."""
        while self.is_running:
            # Wait 3-5 seconds between transcripts to simulate speech
            time.sleep(3.5)
            
            if not self.is_running:
                break
                
            # Generate a mock transcript
            text = self.mock_transcripts[self.transcript_index % len(self.mock_transcripts)]
            self.transcript_index += 1
            
            yield Transcript(
                text=text,
                timestamp=time.time(),
                is_final=True,
                is_speech_start=True,
                confidence=0.95,
                latency=150.0  # Mock 150ms latency
            )
            
    def stop(self) -> None:
        """Stop mock STT provider."""
        self.is_running = False
        
    def get_status(self) -> dict:
        """Get mock STT provider status."""
        return {
            "provider": "mock_stt",
            "is_running": self.is_running,
            "transcripts_generated": self.transcript_index
        }


class MockAIProvider(AIProvider):
    """Mock AI provider that generates fake responses."""
    
    def __init__(self, system_prompt: str, streaming: bool = True):
        super().__init__(system_prompt, streaming)
        self.is_streaming = False
        self.mock_responses = [
            "I'm doing great, thank you for asking! How can I help you today?",
            "The weather is looking nice! It's a perfect day for a conversation.",
            "I'd be happy to help you with your task. What would you like to work on?",
            "Here's a joke for you: Why don't scientists trust atoms? Because they make up everything!",
            "The current time is " + time.strftime("%I:%M %p")
        ]
        self.response_index = 0
        
    def initialize(self) -> None:
        """Initialize mock AI provider."""
        pass
        
    def stream_response(self, user_input: str) -> Iterator[AIResponse]:
        """Generate mock streaming AI response."""
        self.is_streaming = True
        self.add_to_history("user", user_input)
        
        # Get mock response
        response = self.mock_responses[self.response_index % len(self.mock_responses)]
        self.response_index += 1
        
        # Simulate streaming by yielding chunks
        words = response.split()
        full_response = ""
        
        for i, word in enumerate(words):
            if not self.is_streaming:
                break
                
            # Add word to response
            if i > 0:
                full_response += " "
            full_response += word
            
            yield AIResponse(
                text=word + (" " if i < len(words) - 1 else ""),
                is_first=(i == 0),
                is_final=False,
                full_text=full_response
            )
            
            # Simulate AI processing delay
            time.sleep(0.1)
            
        if self.is_streaming:
            # Send final response
            self.add_to_history("assistant", full_response)
            yield AIResponse(
                text="",
                is_first=False,
                is_final=True,
                full_text=full_response
            )
            
        self.is_streaming = False
        
    def stop_streaming(self) -> None:
        """Stop mock streaming."""
        self.is_streaming = False
        
    def stop(self) -> None:
        """Stop mock AI provider."""
        self.stop_streaming()
        
    def get_status(self) -> dict:
        """Get mock AI provider status."""
        return {
            "provider": "mock_ai",
            "is_streaming": self.is_streaming,
            "responses_generated": self.response_index,
            "history_length": len(self.conversation_history)
        }


class MockTTSProvider(TTSProvider):
    """Mock TTS provider that simulates audio playback."""
    
    def __init__(self):
        self.is_playing = False
        
    def initialize(self) -> None:
        """Initialize mock TTS provider."""
        pass
        
    def stream_audio(self, text: str) -> Iterator[AudioChunk]:
        """Generate mock audio chunks."""
        # Set playing flag
        self.is_playing = True
        
        # Simulate TTS processing time
        words = text.split()
        
        for i, word in enumerate(words):
            if not self.is_playing:
                break
                
            yield AudioChunk(
                data=b"mock_audio_data",  # Fake audio data
                is_first=(i == 0),
                is_final=(i == len(words) - 1),
                duration_ms=len(word) * 100  # Rough estimate: 100ms per character
            )
            
            # Simulate audio generation delay
            time.sleep(0.1)  # Reduced delay for testing
            
    def play_chunk(self, audio_chunk: AudioChunk) -> None:
        """Mock audio playback - just sleep to simulate timing."""
        time.sleep(audio_chunk.duration_ms / 1000.0)
        
    def stop_playback(self) -> None:
        """Stop mock audio playback."""
        self.is_playing = False
        
    def stop(self) -> None:
        """Stop mock TTS provider."""
        self.stop_playback()
        
    def get_status(self) -> dict:
        """Get mock TTS provider status."""
        return {
            "provider": "mock_tts",
            "is_playing": self.is_playing
        }