"""Tests for AI providers."""

import pytest
import os
import subprocess
from unittest.mock import Mock, patch
from hello_world.providers.ai.claude import ClaudeProvider
from hello_world.providers.ai.gemini import GeminiProvider


class TestClaudeProvider:
    """Tests for Claude AI provider."""

    def setup_method(self):
        """Set up test fixtures."""
        self.system_prompt = "You are a helpful assistant."
        self.provider = ClaudeProvider(
            system_prompt=self.system_prompt, streaming=True, timeout=5.0
        )

    @patch("subprocess.Popen")
    def test_initialize_success(self, mock_popen):
        """Test successful Claude initialization."""
        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_popen.return_value = mock_process

        self.provider.initialize()

        # Verify subprocess was called with correct arguments
        mock_popen.assert_called_once_with(
            ["claude", "--output-format", "stream-json"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        # Verify system prompt was sent
        mock_process.stdin.write.assert_called_once()
        mock_process.stdin.flush.assert_called_once()

        assert self.provider.process is not None

    @patch("subprocess.Popen")
    def test_initialize_failure(self, mock_popen):
        """Test Claude initialization failure."""
        mock_popen.side_effect = Exception("Failed to start subprocess")

        with pytest.raises(Exception, match="Failed to start subprocess"):
            self.provider.initialize()

    @patch("subprocess.Popen")
    def test_stream_response_success(self, mock_popen):
        """Test successful Claude streaming response."""
        # Mock subprocess
        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.stdout = Mock()
        mock_popen.return_value = mock_process

        # Mock streaming response
        response_chunks = [
            '{"type": "content_block_delta", "delta": {"text": "Hello"}}',
            '{"type": "content_block_delta", "delta": {"text": " there!"}}',
            '{"type": "message_stop"}',
        ]
        mock_process.stdout.readline.side_effect = response_chunks + [""]

        self.provider.initialize()

        # Stream response
        responses = list(self.provider.stream_response("Hello"))

        # Verify responses
        assert len(responses) == 3  # 2 chunks + final
        assert responses[0].text == "Hello"
        assert responses[0].is_first is True
        assert responses[0].is_final is False
        assert responses[1].text == " there!"
        assert responses[1].is_first is False
        assert responses[1].is_final is False
        assert responses[2].text == ""
        assert responses[2].is_final is True
        assert responses[2].full_text == "Hello there!"

    @patch("subprocess.Popen")
    @patch("time.time")
    def test_stream_response_timeout(self, mock_time, mock_popen):
        """Test Claude response timeout."""
        # Mock subprocess that hangs
        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.stdout = Mock()
        mock_process.stdout.readline.return_value = (
            '{"type": "content_block_delta", "delta": {"text": "test"}}'
        )
        mock_popen.return_value = mock_process

        # Mock time to simulate timeout
        mock_time.side_effect = [0, 10, 20]  # Start, check, timeout

        self.provider.initialize()

        with pytest.raises(TimeoutError, match="Claude response timeout"):
            list(self.provider.stream_response("Hello"))

    @patch("subprocess.Popen")
    def test_stop_streaming(self, mock_popen):
        """Test stopping Claude streaming."""
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_popen.return_value = mock_process

        self.provider.initialize()
        self.provider.is_streaming = True

        self.provider.stop_streaming()

        assert self.provider.is_streaming is False
        mock_process.send_signal.assert_called_once()

    @patch("subprocess.Popen")
    def test_stop(self, mock_popen):
        """Test stopping Claude provider."""
        mock_process = Mock()
        mock_popen.return_value = mock_process

        self.provider.initialize()
        self.provider.stop()

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()
        assert self.provider.process is None

    def test_get_status(self):
        """Test getting Claude status."""
        status = self.provider.get_status()

        assert status["provider"] == "claude"
        assert "is_streaming" in status
        assert "process_alive" in status
        assert "history_length" in status


class TestGeminiProvider:
    """Tests for Gemini AI provider."""

    def setup_method(self):
        """Set up test fixtures."""
        self.system_prompt = "You are a helpful assistant."
        self.provider = GeminiProvider(
            system_prompt=self.system_prompt, streaming=True, timeout=5.0, max_retries=2
        )

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"})
    @patch("google.generativeai.configure")
    @patch("google.generativeai.GenerativeModel")
    def test_initialize_success(self, mock_model_class, mock_configure):
        """Test successful Gemini initialization."""
        mock_model = Mock()
        mock_chat_session = Mock()
        mock_model.start_chat.return_value = mock_chat_session
        mock_model_class.return_value = mock_model

        self.provider.initialize()

        mock_configure.assert_called_once_with(api_key="test-key")
        mock_model_class.assert_called_once_with(
            model_name="gemini-pro", system_instruction=self.system_prompt
        )
        assert self.provider.model is not None
        assert self.provider.chat_session is not None

    def test_initialize_no_api_key(self):
        """Test Gemini initialization without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
                self.provider.initialize()

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"})
    @patch("google.generativeai.configure")
    @patch("google.generativeai.GenerativeModel")
    def test_stream_response_success(self, mock_model_class, mock_configure):
        """Test successful Gemini streaming response."""
        # Set up mocks
        mock_model = Mock()
        mock_chat_session = Mock()
        mock_model.start_chat.return_value = mock_chat_session
        mock_model_class.return_value = mock_model

        # Mock streaming response
        mock_chunk1 = Mock()
        mock_chunk1.text = "Hello"
        mock_chunk1.finish_reason = None
        mock_chunk1.safety_ratings = []

        mock_chunk2 = Mock()
        mock_chunk2.text = " there!"
        mock_chunk2.finish_reason = None
        mock_chunk2.safety_ratings = []

        mock_chat_session.send_message.return_value = [mock_chunk1, mock_chunk2]

        self.provider.initialize()

        # Stream response
        responses = list(self.provider.stream_response("Hello"))

        # Verify responses
        assert len(responses) == 3  # 2 chunks + final
        assert responses[0].text == "Hello"
        assert responses[0].is_first is True
        assert responses[0].is_final is False
        assert responses[1].text == " there!"
        assert responses[1].is_first is False
        assert responses[1].is_final is False
        assert responses[2].text == ""
        assert responses[2].is_final is True
        assert responses[2].full_text == "Hello there!"

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"})
    @patch("google.generativeai.configure")
    @patch("google.generativeai.GenerativeModel")
    @patch("time.sleep")  # Mock sleep to speed up test
    def test_stream_response_retry(self, mock_sleep, mock_model_class, mock_configure):
        """Test Gemini retry logic."""
        mock_model = Mock()
        mock_chat_session = Mock()
        mock_model.start_chat.return_value = mock_chat_session
        mock_model_class.return_value = mock_model

        # First call fails, second succeeds
        mock_chunk = Mock()
        mock_chunk.text = "Success"
        mock_chunk.finish_reason = None
        mock_chunk.safety_ratings = []

        # Ensure hasattr works correctly
        mock_chunk.configure_mock(
            **{"text": "Success", "finish_reason": None, "safety_ratings": []}
        )

        mock_chat_session.send_message.side_effect = [
            Exception("API Error"),
            [mock_chunk],
        ]

        self.provider.initialize()

        # Should succeed after retry (may raise if all retries fail)
        responses = list(self.provider.stream_response("Hello"))

        # The important thing is that retry mechanism worked
        # and we didn't get an exception from the final attempt
        assert len(responses) >= 1

        # Verify retry happened
        mock_sleep.assert_called_once_with(1)  # First retry delay

        # Verify send_message was called twice (first failed, second succeeded)
        assert mock_chat_session.send_message.call_count == 2

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"})
    @patch("google.generativeai.configure")
    @patch("google.generativeai.GenerativeModel")
    @patch("time.sleep")
    def test_stream_response_all_retries_fail(
        self, mock_sleep, mock_model_class, mock_configure
    ):
        """Test Gemini when all retries fail."""
        mock_model = Mock()
        mock_chat_session = Mock()
        mock_model.start_chat.return_value = mock_chat_session
        mock_model_class.return_value = mock_model

        # All calls fail
        mock_chat_session.send_message.side_effect = Exception("Persistent API Error")

        self.provider.initialize()

        with pytest.raises(Exception, match="Persistent API Error"):
            list(self.provider.stream_response("Hello"))

        # Should have retried the configured number of times
        assert mock_chat_session.send_message.call_count == 2

    def test_stop_streaming(self):
        """Test stopping Gemini streaming."""
        self.provider.is_streaming = True
        self.provider.stop_streaming()
        assert self.provider.is_streaming is False

    def test_stop(self):
        """Test stopping Gemini provider."""
        self.provider.model = Mock()
        self.provider.chat_session = Mock()

        self.provider.stop()

        assert self.provider.model is None
        assert self.provider.chat_session is None

    def test_get_status(self):
        """Test getting Gemini status."""
        status = self.provider.get_status()

        assert status["provider"] == "gemini"
        assert status["model"] == "gemini-pro"
        assert "is_streaming" in status
        assert "initialized" in status
        assert "history_length" in status


class TestMockProviders:
    """Test mock functionality for both providers."""

    def test_claude_mock_mode(self):
        """Test Claude with mock responses."""
        provider = ClaudeProvider("Test prompt", streaming=True)

        # Mock the subprocess to return test data
        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.stdin = Mock()
            mock_process.stdout = Mock()
            mock_process.stdout.readline.side_effect = [
                '{"type": "content_block_delta", "delta": {"text": "Mock response"}}',
                '{"type": "message_stop"}',
                "",
            ]
            mock_popen.return_value = mock_process

            provider.initialize()
            responses = list(provider.stream_response("Test input"))

            assert len(responses) == 2
            assert responses[0].text == "Mock response"
            assert responses[1].is_final is True

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"})
    def test_gemini_mock_mode(self):
        """Test Gemini with mock responses."""
        provider = GeminiProvider("Test prompt", streaming=True)

        with (
            patch("google.generativeai.configure"),
            patch("google.generativeai.GenerativeModel") as mock_model_class,
        ):
            mock_model = Mock()
            mock_chat_session = Mock()
            mock_model.start_chat.return_value = mock_chat_session
            mock_model_class.return_value = mock_model

            mock_chunk = Mock()
            mock_chunk.text = "Mock response"
            mock_chunk.finish_reason = None
            mock_chunk.safety_ratings = []

            mock_chat_session.send_message.return_value = [mock_chunk]

            provider.initialize()
            responses = list(provider.stream_response("Test input"))

            assert len(responses) == 2
            assert responses[0].text == "Mock response"
            assert responses[1].is_final is True


if __name__ == "__main__":
    pytest.main([__file__])
