"""CLI entry point for developer testing utilities."""

import click
import sys
import json
from pathlib import Path
from typing import Optional, Dict
import structlog

from ..config.settings import settings
from ..utils.logging import setup_logging
from ..providers import registry
from ..metrics.collector import MetricsCollector
from .test_stt import stt as stt_command
from .ai import ai as ai_command
from .test_tts import tts as tts_command


logger = structlog.get_logger()


class TestCLIError(Exception):
    """Base exception for test CLI errors."""

    pass


def setup_test_logging(debug: bool = False) -> None:
    """Setup logging for test utilities with appropriate configuration."""
    setup_logging(
        debug=debug,
        log_file=False,  # Disable file logging for testing utilities
        log_format="dev" if debug else "json",
    )


def load_test_config(config_file: Optional[str] = None) -> None:
    """Load configuration for testing utilities."""
    if config_file:
        config_path = Path(config_file)
        if not config_path.exists():
            raise TestCLIError(f"Configuration file not found: {config_file}")
        settings.config_file = config_path
        settings.load_from_file()

    # Validate settings
    issues = settings.validate()
    if issues:
        raise TestCLIError(f"Configuration issues found: {'; '.join(issues)}")


def get_provider_list() -> Dict[str, list]:
    """Get list of all available providers by type."""
    return {
        "stt": registry.list_stt_providers(),
        "ai": registry.list_ai_providers(),
        "tts": registry.list_tts_providers(),
    }


def format_provider_output(
    providers: Dict[str, list], output_format: str = "text"
) -> str:
    """Format provider list for output."""
    if output_format == "json":
        return json.dumps(providers, indent=2)

    output = []
    output.append("🔌 Available Providers")
    output.append("-" * 50)

    for provider_type, provider_list in providers.items():
        emoji = {"stt": "🎙️", "ai": "🤖", "tts": "🔊"}[provider_type]
        output.append(
            f"\n{emoji} {provider_type.upper()} Providers ({len(provider_list)})"
        )
        for provider in provider_list:
            output.append(f"  - {provider}")

    return "\n".join(output)


def handle_cli_error(error: Exception, debug: bool = False) -> None:
    """Handle CLI errors with appropriate formatting."""
    if debug:
        logger.exception("CLI error occurred", error=str(error))
        click.echo(click.style(f"❌ Error: {str(error)}", fg="red"))
        raise click.Abort()
    else:
        click.echo(click.style(f"❌ {str(error)}", fg="red"))
        sys.exit(1)


def collect_performance_metrics(
    enable_metrics: bool = True,
) -> Optional[MetricsCollector]:
    """Initialize metrics collection if enabled."""
    if enable_metrics:
        try:
            return MetricsCollector()
        except Exception as e:
            logger.warning("Failed to initialize metrics collector", error=str(e))
    return None


# Common CLI options that can be reused across subcommands
common_options = [
    click.option("--debug", is_flag=True, help="Enable debug logging"),
    click.option(
        "--config", type=click.Path(exists=True), help="Path to configuration file"
    ),
    click.option("--no-metrics", is_flag=True, help="Disable metrics collection"),
    click.option(
        "--output-format",
        type=click.Choice(["text", "json"]),
        default="text",
        help="Output format",
    ),
]


def add_common_options(func):
    """Decorator to add common options to a command."""
    for option in reversed(common_options):
        func = option(func)
    return func


@click.group()
@click.version_option(version="1.0.0", package_name="conversation-system")
@click.pass_context
def cli(ctx):
    """
    Developer testing utilities for the conversation system.

    This CLI provides testing tools for STT, AI, and TTS providers
    to help validate functionality during development.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)


@cli.command()
@add_common_options
def list_providers(debug, config, no_metrics, output_format):
    """List all available providers."""
    try:
        setup_test_logging(debug)
        load_test_config(config)

        providers = get_provider_list()
        output = format_provider_output(providers, output_format)
        click.echo(output)

    except Exception as e:
        handle_cli_error(e, debug)


# Register STT command from Team 2
cli.add_command(stt_command, name="stt")

# Register AI command from Team 3
cli.add_command(ai_command, name="ai")

# Register TTS command from Team 4
cli.add_command(tts_command, name="tts")


# All teams have completed their implementations


if __name__ == "__main__":
    cli()
