"""Gemini AI provider implementation."""

import os
import time
from typing import Iterator, Optional
import google.generativeai as genai
import structlog

from .base import AIProvider, AIResponse


logger = structlog.get_logger()


class GeminiProvider(AIProvider):
    """
    Gemini AI provider using direct API calls.
    """

    def __init__(
        self,
        system_prompt: str,
        streaming: bool = True,
        model_name: str = "gemini-pro",
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        super().__init__(system_prompt, streaming)
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries
        self.model: Optional[genai.GenerativeModel] = None
        self.chat_session = None
        self.is_streaming = False

    def initialize(self) -> None:
        """Initialize Gemini API client."""
        logger.info("Initializing Gemini provider", model=self.model_name)

        # Configure API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")

        try:
            # Configure Gemini API
            genai.configure(api_key=api_key)

            # Create model with system instruction
            self.model = genai.GenerativeModel(
                model_name=self.model_name, system_instruction=self.system_prompt
            )

            # Start chat session
            self.chat_session = self.model.start_chat(history=[])

            logger.info("Gemini client initialized")

        except Exception as e:
            logger.error("Failed to initialize Gemini", error=str(e))
            raise

    def stream_response(self, user_input: str) -> Iterator[AIResponse]:
        """Stream response from Gemini."""
        if not self.model or not self.chat_session:
            raise RuntimeError("Gemini not initialized")

        self.is_streaming = True

        # Add to history
        self.add_to_history("user", user_input)

        for attempt in range(self.max_retries):
            try:
                is_first = True
                full_response = ""
                start_time = time.time()

                generation_config = genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2048,
                )

                if self.streaming:
                    # Stream response
                    response = self.chat_session.send_message(
                        user_input, stream=True, generation_config=generation_config
                    )

                    for chunk in response:
                        if not self.is_streaming:
                            break

                        # Check timeout
                        if time.time() - start_time > self.timeout:
                            logger.error(
                                "Gemini response timeout", timeout=self.timeout
                            )
                            self.is_streaming = False
                            raise TimeoutError(
                                f"Gemini response timeout after {self.timeout}s"
                            )

                        text = chunk.text if hasattr(chunk, "text") else ""
                        if text:
                            full_response += text

                            # Extract metadata
                            metadata = {}
                            if hasattr(chunk, "finish_reason"):
                                metadata["finish_reason"] = chunk.finish_reason
                            if hasattr(chunk, "safety_ratings"):
                                metadata["safety_ratings"] = [
                                    {
                                        "category": rating.category.name,
                                        "probability": rating.probability.name,
                                    }
                                    for rating in chunk.safety_ratings
                                ]

                            yield AIResponse(
                                text=text,
                                is_first=is_first,
                                is_final=False,
                                metadata=metadata,
                            )

                            is_first = False

                else:
                    # Non-streaming response
                    response = self.chat_session.send_message(
                        user_input, generation_config=generation_config
                    )
                    full_response = response.text

                    yield AIResponse(
                        text=full_response,
                        is_first=True,
                        is_final=True,
                        full_text=full_response,
                    )

                # Add complete response to history
                if full_response:
                    self.add_to_history("assistant", full_response)

                # Send final response if streaming
                if self.streaming:
                    yield AIResponse(
                        text="", is_first=False, is_final=True, full_text=full_response
                    )

                self.is_streaming = False
                break  # Success, exit retry loop

            except (TimeoutError, Exception) as e:
                logger.warning(f"Gemini attempt {attempt + 1} failed", error=str(e))
                self.is_streaming = False

                if attempt == self.max_retries - 1:
                    # Last attempt failed
                    logger.error("All Gemini retry attempts failed", error=str(e))
                    raise

                # Exponential backoff
                wait_time = 2**attempt
                logger.info(f"Retrying Gemini in {wait_time}s", attempt=attempt + 1)
                time.sleep(wait_time)

    def stop_streaming(self) -> None:
        """Stop current streaming response."""
        logger.debug("Stopping Gemini streaming")
        self.is_streaming = False

        # Note: Gemini API doesn't have a direct way to stop streaming
        # We rely on the is_streaming flag check in stream_response

    def stop(self) -> None:
        """Stop Gemini provider."""
        logger.info("Stopping Gemini provider")

        self.stop_streaming()
        self.model = None
        self.chat_session = None

    def get_status(self) -> dict:
        """Get Gemini provider status."""
        return {
            "provider": "gemini",
            "model": self.model_name,
            "is_streaming": self.is_streaming,
            "initialized": self.model is not None,
            "history_length": len(self.conversation_history),
        }
