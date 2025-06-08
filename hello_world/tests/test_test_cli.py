"""Tests for the test CLI infrastructure."""

import json
from click.testing import CliRunner
from unittest.mock import patch

from hello_world.cli.test_cli import (
    cli,
    get_provider_list,
    format_provider_output,
    TestCLIError,
)


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_cli_help(self):
        """Test that CLI shows help message."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Developer testing utilities" in result.output
        assert "conversation system" in result.output

    def test_cli_version(self):
        """Test that CLI shows version."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0

    def test_subcommands_exist(self):
        """Test that required subcommands exist."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "stt" in result.output
        assert "ai" in result.output
        assert "tts" in result.output
        assert "list-providers" in result.output


class TestListProviders:
    """Test provider listing functionality."""

    @patch("hello_world.cli.test_cli.registry")
    def test_list_providers_text_format(self, mock_registry):
        """Test listing providers in text format."""
        mock_registry.list_stt_providers.return_value = ["whisperkit"]
        mock_registry.list_ai_providers.return_value = ["claude", "gemini"]
        mock_registry.list_tts_providers.return_value = ["elevenlabs"]

        runner = CliRunner()
        result = runner.invoke(cli, ["list-providers"])

        assert result.exit_code == 0
        assert "Available Providers" in result.output
        assert "whisperkit" in result.output
        assert "claude" in result.output
        assert "gemini" in result.output
        assert "elevenlabs" in result.output

    @patch("hello_world.cli.test_cli.registry")
    def test_list_providers_json_format(self, mock_registry):
        """Test listing providers in JSON format."""
        mock_registry.list_stt_providers.return_value = ["whisperkit"]
        mock_registry.list_ai_providers.return_value = ["claude", "gemini"]
        mock_registry.list_tts_providers.return_value = ["elevenlabs"]

        runner = CliRunner()
        result = runner.invoke(cli, ["list-providers", "--output-format", "json"])

        assert result.exit_code == 0

        # Parse JSON output
        output_data = json.loads(result.output)
        assert "stt" in output_data
        assert "ai" in output_data
        assert "tts" in output_data
        assert output_data["stt"] == ["whisperkit"]
        assert output_data["ai"] == ["claude", "gemini"]
        assert output_data["tts"] == ["elevenlabs"]


class TestSubcommands:
    """Test subcommand structure."""

    def test_stt_subcommand_exists(self):
        """Test STT subcommand exists and shows help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["stt", "--help"])

        assert result.exit_code == 0
        assert "Speech-to-text testing utilities" in result.output

    def test_ai_subcommand_exists(self):
        """Test AI subcommand exists and shows help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["ai", "--help"])

        assert result.exit_code == 0
        assert "AI provider testing utilities" in result.output

    def test_tts_subcommand_exists(self):
        """Test TTS subcommand exists and shows help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["tts", "--help"])

        assert result.exit_code == 0
        assert "Text-to-speech testing utilities" in result.output

    def test_placeholder_commands(self):
        """Test that placeholder test commands exist."""
        runner = CliRunner()

        # Test STT placeholder
        result = runner.invoke(cli, ["stt", "test"])
        assert result.exit_code == 0
        assert "Team 2" in result.output

        # Test AI placeholder
        result = runner.invoke(cli, ["ai", "test"])
        assert result.exit_code == 0
        assert "Team 3" in result.output

        # Test TTS placeholder
        result = runner.invoke(cli, ["tts", "test"])
        assert result.exit_code == 0
        assert "Team 4" in result.output


class TestUtilityFunctions:
    """Test utility functions."""

    @patch("hello_world.cli.test_cli.registry")
    def test_get_provider_list(self, mock_registry):
        """Test get_provider_list function."""
        mock_registry.list_stt_providers.return_value = ["whisperkit"]
        mock_registry.list_ai_providers.return_value = ["claude", "gemini"]
        mock_registry.list_tts_providers.return_value = ["elevenlabs"]

        providers = get_provider_list()

        assert providers["stt"] == ["whisperkit"]
        assert providers["ai"] == ["claude", "gemini"]
        assert providers["tts"] == ["elevenlabs"]

    def test_format_provider_output_text(self):
        """Test formatting provider output as text."""
        providers = {
            "stt": ["whisperkit"],
            "ai": ["claude", "gemini"],
            "tts": ["elevenlabs"],
        }

        output = format_provider_output(providers, "text")

        assert "Available Providers" in output
        assert "whisperkit" in output
        assert "claude" in output
        assert "gemini" in output
        assert "elevenlabs" in output

    def test_format_provider_output_json(self):
        """Test formatting provider output as JSON."""
        providers = {
            "stt": ["whisperkit"],
            "ai": ["claude", "gemini"],
            "tts": ["elevenlabs"],
        }

        output = format_provider_output(providers, "json")
        parsed = json.loads(output)

        assert parsed == providers


class TestErrorHandling:
    """Test error handling functionality."""

    def test_test_cli_error_creation(self):
        """Test TestCLIError can be created."""
        error = TestCLIError("Test error message")
        assert str(error) == "Test error message"

    def test_config_file_not_found(self):
        """Test error when config file doesn't exist."""
        runner = CliRunner()
        result = runner.invoke(
            cli, ["list-providers", "--config", "/nonexistent/file.json"]
        )

        # Click returns exit code 2 for usage errors (like missing file)
        assert result.exit_code == 2
        assert "does not exist" in result.output or "Invalid value" in result.output


class TestCommonOptions:
    """Test common CLI options."""

    @patch("hello_world.cli.test_cli.setup_test_logging")
    @patch("hello_world.cli.test_cli.registry")
    def test_debug_option(self, mock_registry, mock_setup_logging):
        """Test debug option is passed through."""
        mock_registry.list_stt_providers.return_value = ["whisperkit"]
        mock_registry.list_ai_providers.return_value = ["claude"]
        mock_registry.list_tts_providers.return_value = ["elevenlabs"]

        runner = CliRunner()
        result = runner.invoke(cli, ["list-providers", "--debug"])

        assert result.exit_code == 0
        mock_setup_logging.assert_called_once_with(True)

    @patch("hello_world.cli.test_cli.setup_test_logging")
    @patch("hello_world.cli.test_cli.registry")
    def test_no_debug_option(self, mock_registry, mock_setup_logging):
        """Test default behavior without debug option."""
        mock_registry.list_stt_providers.return_value = ["whisperkit"]
        mock_registry.list_ai_providers.return_value = ["claude"]
        mock_registry.list_tts_providers.return_value = ["elevenlabs"]

        runner = CliRunner()
        result = runner.invoke(cli, ["list-providers"])

        assert result.exit_code == 0
        mock_setup_logging.assert_called_once_with(False)
