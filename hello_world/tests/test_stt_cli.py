"""Tests for STT CLI utility."""

import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch
from click.testing import CliRunner

from hello_world.cli.test_stt import stt
from hello_world.providers.stt.base import Transcript


class TestSTTCLI(unittest.TestCase):
    """Test the STT CLI utility."""

    def setUp(self):
        self.runner = CliRunner()

    def test_list_providers(self):
        """Test --list-providers option."""
        result = self.runner.invoke(stt, ["--list-providers"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Available STT providers:", result.output)
        self.assertIn("whisperkit", result.output)

    def test_no_input_error(self):
        """Test error when no input is provided."""
        with patch("sys.stdin.isatty", return_value=True):
            result = self.runner.invoke(stt, [])

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("No input specified", result.output)

    def test_nonexistent_file_error(self):
        """Test error when input file doesn't exist."""
        result = self.runner.invoke(stt, ["--input", "/path/that/does/not/exist.wav"])

        self.assertNotEqual(result.exit_code, 0)

    def test_unsupported_format_error(self):
        """Test error for unsupported audio format."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"not audio")

        try:
            result = self.runner.invoke(stt, ["--input", str(temp_path)])

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("Unsupported audio format", result.output)

        finally:
            temp_path.unlink(missing_ok=True)

    @patch("hello_world.cli.test_stt.WhisperKitFileProvider")
    def test_successful_processing(self, mock_provider_class):
        """Test successful audio file processing."""
        # Create a temporary audio file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            # Mock provider
            mock_provider = Mock()
            mock_provider.model = "large-v3_turbo"
            mock_provider.process_file.return_value = [
                Transcript(
                    text="Hello world",
                    timestamp=1234567890.0,
                    is_final=True,
                    is_speech_start=True,
                    confidence=0.95,
                    latency=150.0,
                )
            ]
            mock_provider.get_status.return_value = {"provider": "whisperkit_file"}
            mock_provider_class.return_value = mock_provider

            result = self.runner.invoke(stt, ["--input", str(temp_path)])

            self.assertEqual(result.exit_code, 0)
            self.assertIn("Hello world", result.output)

            # Verify provider was initialized and used correctly
            mock_provider.initialize.assert_called_once()
            mock_provider.process_file.assert_called_once_with(temp_path)
            mock_provider.stop.assert_called_once()

        finally:
            temp_path.unlink(missing_ok=True)

    @patch("hello_world.cli.test_stt.WhisperKitFileProvider")
    def test_json_output(self, mock_provider_class):
        """Test JSON output format."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            # Mock provider
            mock_provider = Mock()
            mock_provider.model = "large-v3_turbo"
            mock_provider.process_file.return_value = [
                Transcript(
                    text="Hello world",
                    timestamp=1234567890.0,
                    is_final=True,
                    is_speech_start=True,
                    confidence=0.95,
                    latency=150.0,
                )
            ]
            mock_provider_class.return_value = mock_provider

            result = self.runner.invoke(stt, ["--input", str(temp_path), "--json"])

            self.assertEqual(result.exit_code, 0)

            # Parse and verify JSON output
            output_data = json.loads(result.output)
            self.assertEqual(output_data["text"], "Hello world")
            self.assertEqual(output_data["provider"], "whisperkit")
            self.assertEqual(output_data["model"], "large-v3_turbo")
            self.assertIn("metadata", output_data)
            self.assertEqual(output_data["metadata"]["confidence"], 0.95)
            self.assertEqual(output_data["metadata"]["latency_ms"], 150.0)

        finally:
            temp_path.unlink(missing_ok=True)

    @patch("hello_world.cli.test_stt.WhisperKitFileProvider")
    def test_metrics_output(self, mock_provider_class):
        """Test metrics output."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            # Mock provider
            mock_provider = Mock()
            mock_provider.model = "large-v3_turbo"
            mock_provider.process_file.return_value = [
                Transcript(
                    text="Hello world",
                    timestamp=1234567890.0,
                    is_final=True,
                    is_speech_start=True,
                    confidence=0.95,
                    latency=150.0,
                )
            ]
            mock_provider.get_status.return_value = {"provider": "whisperkit_file"}
            mock_provider_class.return_value = mock_provider

            result = self.runner.invoke(stt, ["--input", str(temp_path), "--metrics"])

            self.assertEqual(result.exit_code, 0)
            self.assertIn("Hello world", result.output)
            self.assertIn("--- Metrics ---", result.output)
            self.assertIn("Processing time:", result.output)
            self.assertIn("Characters:", result.output)
            self.assertIn("Words:", result.output)

        finally:
            temp_path.unlink(missing_ok=True)

    @patch("hello_world.cli.test_stt.WhisperKitFileProvider")
    def test_custom_model(self, mock_provider_class):
        """Test using custom model."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            # Mock provider
            mock_provider = Mock()
            mock_provider.process_file.return_value = [
                Transcript(
                    text="Test", timestamp=0, is_final=True, is_speech_start=True
                )
            ]
            mock_provider_class.return_value = mock_provider

            result = self.runner.invoke(
                stt, ["--input", str(temp_path), "--model", "custom-model"]
            )

            self.assertEqual(result.exit_code, 0)

            # Verify custom model was passed to provider
            mock_provider_class.assert_called_once()
            call_kwargs = mock_provider_class.call_args[1]
            self.assertEqual(call_kwargs["model"], "custom-model")

        finally:
            temp_path.unlink(missing_ok=True)

    @patch("hello_world.cli.test_stt.WhisperKitFileProvider")
    def test_no_speech_detected(self, mock_provider_class):
        """Test handling when no speech is detected."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            # Mock provider returning empty transcript
            mock_provider = Mock()
            mock_provider.process_file.return_value = [
                Transcript(text="", timestamp=0, is_final=True, is_speech_start=False)
            ]
            mock_provider_class.return_value = mock_provider

            result = self.runner.invoke(stt, ["--input", str(temp_path)])

            self.assertEqual(result.exit_code, 0)
            self.assertIn("(no speech detected)", result.output)

        finally:
            temp_path.unlink(missing_ok=True)

    @patch("hello_world.cli.test_stt.WhisperKitFileProvider")
    def test_provider_error_handling(self, mock_provider_class):
        """Test error handling when provider fails."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            # Mock provider that raises an error
            mock_provider = Mock()
            mock_provider.initialize.side_effect = RuntimeError("Provider failed")
            mock_provider_class.return_value = mock_provider

            result = self.runner.invoke(stt, ["--input", str(temp_path)])

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("Error: Provider failed", result.output)

        finally:
            temp_path.unlink(missing_ok=True)

    @patch("hello_world.cli.test_stt.WhisperKitFileProvider")
    def test_json_error_output(self, mock_provider_class):
        """Test JSON error output format."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            # Mock provider that raises an error
            mock_provider = Mock()
            mock_provider.initialize.side_effect = RuntimeError("Provider failed")
            mock_provider_class.return_value = mock_provider

            result = self.runner.invoke(stt, ["--input", str(temp_path), "--json"])

            self.assertNotEqual(result.exit_code, 0)

            # Parse error JSON
            error_data = json.loads(result.output)
            self.assertEqual(error_data["error"], "Provider failed")
            self.assertEqual(error_data["provider"], "whisperkit")
            self.assertIn("input_file", error_data)

        finally:
            temp_path.unlink(missing_ok=True)

    @patch("hello_world.cli.test_stt.read_audio_from_stdin")
    @patch("hello_world.cli.test_stt.WhisperKitFileProvider")
    @patch("sys.stdin.isatty")
    def test_stdin_input(self, mock_isatty, mock_provider_class, mock_read_stdin):
        """Test reading audio from stdin."""
        # Mock stdin is available
        mock_isatty.return_value = False

        # Mock stdin reading
        temp_path = Path("/tmp/temp_audio.wav")
        mock_read_stdin.return_value = temp_path

        # Mock provider
        mock_provider = Mock()
        mock_provider.process_file.return_value = [
            Transcript(
                text="From stdin", timestamp=0, is_final=True, is_speech_start=True
            )
        ]
        mock_provider_class.return_value = mock_provider

        with patch("hello_world.cli.test_stt.cleanup_temp_file") as mock_cleanup:
            result = self.runner.invoke(stt, ["--input", "-"])

            self.assertEqual(result.exit_code, 0)
            self.assertIn("From stdin", result.output)

            # Verify stdin was read and temp file cleaned up
            mock_read_stdin.assert_called_once()
            mock_cleanup.assert_called_once_with(temp_path)


if __name__ == "__main__":
    unittest.main()
