"""Claude AI provider implementation using Claude Code SDK."""

import subprocess
import json
import signal
import time
from typing import Iterator, Optional
import structlog

from .base import AIProvider, AIResponse


logger = structlog.get_logger()


class ClaudeProvider(AIProvider):
    """
    Claude AI provider using Claude Code SDK subprocess.
    """

    def __init__(
        self,
        system_prompt: str,
        streaming: bool = True,
        claude_path: str = "claude",
        timeout: float = 30.0,
    ):
        super().__init__(system_prompt, streaming)
        self.claude_path = claude_path
        self.timeout = timeout

        self.process: Optional[subprocess.Popen] = None
        self.is_streaming = False
        self.current_response = []

    def initialize(self) -> None:
        """Initialize Claude Code SDK subprocess."""
        logger.info("Initializing Claude provider")

        # Build command
        cmd = [
            self.claude_path,
            "--output-format",
            "stream-json" if self.streaming else "json",
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
            )

            # Send initial system prompt message
            initial_message = {"type": "system", "content": self.system_prompt}
            if self.process.stdin:
                self.process.stdin.write(json.dumps(initial_message) + "\n")
                self.process.stdin.flush()

            logger.info("Claude subprocess started")

        except Exception as e:
            logger.error("Failed to start Claude", error=str(e))
            raise

    def stream_response(self, user_input: str) -> Iterator[AIResponse]:
        """Stream response from Claude."""
        if not self.process:
            raise RuntimeError("Claude not initialized")

        self.is_streaming = True
        self.current_response = []

        # Add to history
        self.add_to_history("user", user_input)

        try:
            # Send user input as JSON message
            user_message = {"type": "user", "content": user_input}
            if self.process.stdin:
                self.process.stdin.write(json.dumps(user_message) + "\n")
                self.process.stdin.flush()

            is_first = True
            full_response = ""
            start_time = time.time()

            # Read streaming response with timeout
            while self.is_streaming:
                # Check timeout
                if time.time() - start_time > self.timeout:
                    logger.error("Claude response timeout", timeout=self.timeout)
                    self.is_streaming = False
                    raise TimeoutError(f"Claude response timeout after {self.timeout}s")

                if not self.process.stdout:
                    break
                line = self.process.stdout.readline()
                if not line:
                    break

                try:
                    # Parse JSON response
                    data = json.loads(line.strip())

                    # Handle different response types
                    if data.get("type") == "content_block_delta":
                        # Streaming text chunk
                        text = data.get("delta", {}).get("text", "")
                        if text:
                            full_response += text

                            yield AIResponse(
                                text=text,
                                is_first=is_first,
                                is_final=False,
                                metadata=data.get("metadata"),
                            )

                            is_first = False

                    elif data.get("type") == "message_stop":
                        # Response complete
                        self.is_streaming = False
                        break

                    elif data.get("type") == "error":
                        # Handle error from Claude
                        logger.error("Claude error", error=data.get("error"))
                        self.is_streaming = False
                        raise RuntimeError(f"Claude error: {data.get('error')}")

                except json.JSONDecodeError as e:
                    logger.warning("Invalid JSON from Claude", line=line, error=str(e))
                    continue

            # Add complete response to history
            if full_response:
                self.add_to_history("assistant", full_response)

            # Send final response
            yield AIResponse(
                text="", is_first=False, is_final=True, full_text=full_response
            )

        except Exception as e:
            logger.error("Error streaming Claude response", error=str(e))
            self.is_streaming = False
            raise

    def stop_streaming(self) -> None:
        """Stop current streaming response."""
        logger.debug("Stopping Claude streaming")
        self.is_streaming = False

        # Send interrupt signal to Claude subprocess
        if self.process and self.process.poll() is None:
            try:
                # Send SIGINT to interrupt current generation
                self.process.send_signal(signal.SIGINT)
            except Exception as e:
                logger.warning("Failed to interrupt Claude process", error=str(e))

    def stop(self) -> None:
        """Stop Claude subprocess."""
        logger.info("Stopping Claude provider")

        self.stop_streaming()

        if self.process:
            try:
                # Gracefully terminate subprocess
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Claude didn't terminate gracefully, killing process")
                self.process.kill()
                self.process.wait()
            except Exception as e:
                logger.error("Error stopping Claude process", error=str(e))

            self.process = None

    def get_status(self) -> dict:
        """Get Claude provider status."""
        return {
            "provider": "claude",
            "is_streaming": self.is_streaming,
            "process_alive": self.process is not None and self.process.poll() is None,
            "history_length": len(self.conversation_history),
        }
