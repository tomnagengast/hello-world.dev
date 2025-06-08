"""Tests for TTS utility functionality."""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch

from hello_world.cli.tts_utility import TTSTestUtility
from hello_world.providers.tts.base import AudioChunk


class TestTTSTestUtility:
    """Test cases for TTSTestUtility class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_text = "Hello, this is a test"
        self.mock_provider = Mock()
        self.mock_provider.get_status.return_value = {
            "is_playing": False,
            "provider": "test",
        }

    @patch("hello_world.cli.tts_utility.registry")
    def test_initialization(self, mock_registry):
        """Test utility initialization."""
        mock_registry.get_tts_provider.return_value = self.mock_provider

        utility = TTSTestUtility(
            provider="test_provider", voice="test_voice", speed=1.5, debug=True
        )

        assert utility.provider_name == "test_provider"
        assert utility.voice == "test_voice"
        assert utility.speed == 1.5
        assert utility.debug is True
        assert utility.provider is None  # Not initialized yet

    @patch("hello_world.cli.tts_utility.registry")
    def test_provider_initialization(self, mock_registry):
        """Test provider initialization."""
        mock_registry.get_tts_provider.return_value = self.mock_provider

        utility = TTSTestUtility(provider="test_provider", voice="test_voice")
        utility._initialize_provider()

        # Check that provider was retrieved with correct parameters
        mock_registry.get_tts_provider.assert_called_once_with(
            "test_provider", voice_id="test_voice"
        )

        # Check that provider was initialized
        self.mock_provider.initialize.assert_called_once()
        assert utility.provider == self.mock_provider

    @patch("hello_world.cli.tts_utility.registry")
    def test_provider_initialization_with_speed(self, mock_registry):
        """Test provider initialization with custom speed."""
        mock_registry.get_tts_provider.return_value = self.mock_provider

        utility = TTSTestUtility(provider="test_provider", speed=1.5)
        utility._initialize_provider()

        # Check that provider was retrieved with speed parameter
        mock_registry.get_tts_provider.assert_called_once_with(
            "test_provider", speed=1.5
        )

    @patch("hello_world.cli.tts_utility.registry")
    def test_provider_initialization_failure(self, mock_registry):
        """Test provider initialization failure handling."""
        mock_registry.get_tts_provider.side_effect = ValueError("Provider not found")

        utility = TTSTestUtility(provider="invalid_provider")

        with pytest.raises(RuntimeError, match="Failed to initialize TTS provider"):
            utility._initialize_provider()

    @patch("hello_world.cli.tts_utility.registry")
    def test_file_output_test(self, mock_registry):
        """Test TTS with file output."""
        # Mock audio chunks
        chunks = [
            AudioChunk(data=b"chunk1", is_first=True),
            AudioChunk(data=b"chunk2"),
            AudioChunk(data=b"", is_final=True),
        ]
        self.mock_provider.stream_audio.return_value = iter(chunks)
        mock_registry.get_tts_provider.return_value = self.mock_provider

        utility = TTSTestUtility(provider="test_provider")

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            output_path = tmp_file.name

        try:
            # Run the test
            success = utility.run_tts_test(
                text=self.test_text, output_file=output_path, output_format="mp3"
            )

            assert success is True

            # Check that audio was generated
            self.mock_provider.stream_audio.assert_called_once_with(self.test_text)

            # Check that file was created with audio data
            assert os.path.exists(output_path)
            with open(output_path, "rb") as f:
                content = f.read()
                assert content == b"chunk1chunk2"

            # Check metrics
            metrics = utility.get_metrics()
            assert "generation_time" in metrics
            assert "total_chunks" in metrics
            assert "output_file_size" in metrics
            assert metrics["text_length"] == len(self.test_text)
            assert metrics["total_chunks"] == 2  # Only chunks with data

        finally:
            # Clean up
            if os.path.exists(output_path):
                os.unlink(output_path)

    @patch("hello_world.cli.tts_utility.registry")
    def test_playback_test(self, mock_registry):
        """Test TTS with speaker playback."""
        # Mock audio chunks
        chunks = [
            AudioChunk(data=b"chunk1", is_first=True),
            AudioChunk(data=b"chunk2"),
            AudioChunk(data=b"", is_final=True),
        ]
        self.mock_provider.stream_audio.return_value = iter(chunks)
        mock_registry.get_tts_provider.return_value = self.mock_provider

        utility = TTSTestUtility(provider="test_provider")

        # Mock the status to simulate playback completion
        # We need multiple calls: during playback loop + final metrics call
        self.mock_provider.get_status.side_effect = [
            {"is_playing": True},  # First check during playback
            {"is_playing": False},  # Second check - playback done
            {"is_playing": False, "provider": "test_provider"},  # Final metrics call
        ]

        success = utility.run_tts_test(text=self.test_text)

        assert success is True

        # Check that audio was generated
        self.mock_provider.stream_audio.assert_called_once_with(self.test_text)

        # Check that chunks were played
        assert self.mock_provider.play_chunk.call_count == 3

        # Check metrics
        metrics = utility.get_metrics()
        assert "generation_time" in metrics
        assert "total_chunks" in metrics
        assert metrics["text_length"] == len(self.test_text)

    @patch("hello_world.cli.tts_utility.registry")
    def test_empty_audio_handling(self, mock_registry):
        """Test handling of empty audio data."""
        # Mock empty audio generation
        chunks = [AudioChunk(data=b"", is_final=True)]
        self.mock_provider.stream_audio.return_value = iter(chunks)
        mock_registry.get_tts_provider.return_value = self.mock_provider

        utility = TTSTestUtility(provider="test_provider")

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            output_path = tmp_file.name

        try:
            # This should fail due to no audio data
            success = utility.run_tts_test(text=self.test_text, output_file=output_path)

            assert success is False

        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    @patch("hello_world.cli.tts_utility.registry")
    def test_provider_cleanup(self, mock_registry):
        """Test that provider is properly cleaned up."""
        mock_registry.get_tts_provider.return_value = self.mock_provider

        # Mock audio chunks
        chunks = [AudioChunk(data=b"test", is_final=True)]
        self.mock_provider.stream_audio.return_value = iter(chunks)

        utility = TTSTestUtility(provider="test_provider")
        utility.run_tts_test(text=self.test_text)

        # Check that provider was stopped
        self.mock_provider.stop.assert_called_once()

    @patch("hello_world.cli.tts_utility.registry")
    def test_metrics_collection(self, mock_registry):
        """Test metrics collection functionality."""
        mock_registry.get_tts_provider.return_value = self.mock_provider

        chunks = [AudioChunk(data=b"test", is_final=True)]
        self.mock_provider.stream_audio.return_value = iter(chunks)

        provider_status = {
            "provider": "test_provider",
            "is_playing": False,
            "queue_size": 0,
        }
        self.mock_provider.get_status.return_value = provider_status

        utility = TTSTestUtility(
            provider="test_provider", voice="test_voice", speed=1.5
        )
        utility.run_tts_test(text=self.test_text)

        metrics = utility.get_metrics()

        # Check basic metrics
        assert metrics["text_length"] == len(self.test_text)
        assert metrics["provider_name"] == "test_provider"
        assert metrics["voice_used"] == "test_voice"
        assert metrics["speed_used"] == 1.5
        assert "initialization_time" in metrics
        assert "generation_time" in metrics

        # Check provider status is included
        assert metrics["provider_status"] == provider_status

    def test_get_metrics_without_provider(self):
        """Test getting metrics when no provider is initialized."""
        utility = TTSTestUtility(provider="test_provider")

        metrics = utility.get_metrics()

        # Should still return basic info
        assert metrics["provider_name"] == "test_provider"
        assert metrics["voice_used"] is None
        assert metrics["speed_used"] == 1.0
        assert "provider_status" not in metrics
