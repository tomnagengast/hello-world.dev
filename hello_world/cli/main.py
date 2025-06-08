"""CLI entry point for the conversation system."""

import click
import json
import signal
import sys
from pathlib import Path
import structlog
from typing import Optional

from ..core.conversation_manager import ConversationManager, ConversationConfig
from .ai import ai
from ..config.settings import settings
from ..metrics.collector import MetricsCollector
from ..utils.logging import setup_logging
from ..providers import registry


logger = structlog.get_logger()


# Global conversation manager for signal handling
conversation_manager: Optional[ConversationManager] = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal")
    if conversation_manager:
        conversation_manager.stop()
    sys.exit(0)


def validate_provider(ctx, param, value):
    """Validate provider selection."""
    if param.name == "stt_provider":
        valid_providers = registry.list_stt_providers()
        provider_type = "STT"
    elif param.name == "ai_provider":
        valid_providers = registry.list_ai_providers()
        provider_type = "AI"
    elif param.name == "tts_provider":
        valid_providers = registry.list_tts_providers()
        provider_type = "TTS"
    else:
        return value

    if value not in valid_providers:
        raise click.BadParameter(
            f"Invalid {provider_type} provider '{value}'. "
            f"Available options: {', '.join(valid_providers)}"
        )
    return value


@click.command()
@click.option(
    "--project",
    "-p",
    type=click.Path(),
    help="Project path to associate with conversation",
)
@click.option(
    "--stt-provider",
    callback=validate_provider,
    default="whisperkit",
    help="STT provider to use",
)
@click.option(
    "--ai-provider",
    callback=validate_provider,
    default="claude",
    help="AI provider to use",
)
@click.option(
    "--tts-provider",
    callback=validate_provider,
    default="elevenlabs",
    help="TTS provider to use",
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--mock", is_flag=True, help="Run in mock mode (no API calls)")
@click.option("--dry-run", is_flag=True, help="Test pipeline without API calls")
@click.option(
    "--config", type=click.Path(exists=True), help="Path to configuration file"
)
@click.option("--no-interruptions", is_flag=True, help="Disable interruption handling")
@click.option("--no-metrics", is_flag=True, help="Disable metrics collection")
def main(
    project: Optional[str],
    stt_provider: str,
    ai_provider: str,
    tts_provider: str,
    debug: bool,
    mock: bool,
    dry_run: bool,
    config: Optional[str],
    no_interruptions: bool,
    no_metrics: bool,
):
    """
    Start the conversation system.

    This will enable natural voice interactions with AI models using:
    - WhisperKit for speech-to-text
    - Claude or Gemini for AI responses
    - ElevenLabs for text-to-speech
    """
    global conversation_manager

    # Setup logging
    setup_logging(debug=debug)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Load configuration
    if config:
        settings.config_file = Path(config)
        settings.load_from_file()

    # Override with command line options
    settings.stt_provider = stt_provider
    settings.ai_provider = ai_provider
    settings.tts_provider = tts_provider

    # Create conversation config
    conversation_config = ConversationConfig(
        stt_provider=stt_provider,
        ai_provider=ai_provider,
        tts_provider=tts_provider,
        enable_interruptions=not no_interruptions,
        enable_metrics=not no_metrics,
        debug_mode=debug,
        mock_mode=mock or dry_run,
    )

    # Initialize conversation manager
    conversation_manager = ConversationManager(conversation_config)

    # Display startup information
    click.echo(click.style("🎙️  Conversation System Starting...", fg="green", bold=True))
    click.echo(f"STT Provider: {stt_provider}")
    click.echo(f"AI Provider: {ai_provider}")
    click.echo(f"TTS Provider: {tts_provider}")
    click.echo(f"Project: {project or 'None'}")

    if mock:
        click.echo(
            click.style(
                "⚠️  Running in MOCK mode - no API calls will be made", fg="yellow"
            )
        )
    elif dry_run:
        click.echo(
            click.style(
                "⚠️  Running in DRY RUN mode - testing pipeline only", fg="yellow"
            )
        )

    click.echo("\nPress Ctrl+C to stop the conversation.\n")

    try:
        # Start the conversation system
        conversation_manager.start(project_path=project)

        # Keep the main thread alive and display status
        import time

        last_status_time = 0
        status_interval = 10  # Show status every 10 seconds

        while conversation_manager.is_running:
            time.sleep(1)

            # Display periodic status in debug mode
            if debug and time.time() - last_status_time > status_interval:
                status = conversation_manager.get_status()
                click.echo(
                    f"Status: Running | Transcript Queue: {status['transcript_queue_size']} | "
                    f"Response Queue: {status['response_queue_size']} | TTS: {'Playing' if status['tts_playing'] else 'Idle'}"
                )
                last_status_time = time.time()

    except KeyboardInterrupt:
        click.echo("\n\nShutting down...")
    except Exception as e:
        logger.error("Fatal error", error=str(e), exc_info=True)
        click.echo(click.style(f"\n❌ Error: {str(e)}", fg="red"))
    finally:
        if conversation_manager:
            # Save metrics if enabled
            if (
                conversation_config.enable_metrics
                and conversation_manager.metrics_collector
            ):
                summary = conversation_manager.metrics_collector.get_summary()
                conversation_manager.metrics_collector.save_metrics()

                # Display session summary
                click.echo("\n📊 Session Summary:")
                click.echo(f"Duration: {summary['session_duration_seconds']:.1f}s")
                click.echo(f"Interactions: {summary['total_interactions']}")

                if summary["total_interactions"] > 0:
                    click.echo(
                        f"Avg E2E Latency: {summary['e2e_latency_ms']['avg']:.0f}ms"
                    )

            conversation_manager.stop()

        click.echo("\n👋 Goodbye!")


@click.command()
@click.option("--days", "-d", default=7, help="Number of days to include in report")
@click.option(
    "--format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
def metrics(days: int, format: str):
    """View performance metrics."""
    collector = MetricsCollector()
    report = collector.generate_report(days=days)

    if format == "json":
        click.echo(json.dumps(report, indent=2))
    else:
        click.echo("📊 Performance Metrics Report")
        click.echo(f"Last {days} days")
        click.echo("-" * 50)

        if "error" in report:
            click.echo(click.style(f"❌ {report['error']}", fg="red"))
            return

        if report["total_sessions"] == 0:
            click.echo("No data available for the specified period.")
            return

        # Display summary statistics
        click.echo(f"Total Sessions: {report['total_sessions']}")
        click.echo(f"Total Interactions: {report['total_interactions']}")
        click.echo(f"Error Rate: {report['error_rate']:.2%}")
        click.echo(f"Interruption Rate: {report['interruption_rate']:.2%}")
        click.echo()

        # Display latency metrics
        def display_latency(name, metrics):
            if metrics["samples"] > 0:
                click.echo(f"{name} Latency:")
                click.echo(f"  Average: {metrics['avg']:.1f}ms")
                click.echo(f"  P95: {metrics['p95']:.1f}ms")
                click.echo(f"  P99: {metrics['p99']:.1f}ms")
                click.echo(f"  Samples: {metrics['samples']}")
            else:
                click.echo(f"{name} Latency: No data")
            click.echo()

        display_latency("STT", report["stt_latency_ms"])
        display_latency("AI", report["ai_latency_ms"])
        display_latency("TTS", report["tts_latency_ms"])
        display_latency("End-to-End", report["e2e_latency_ms"])


@click.command()
@click.argument("project_path", type=click.Path(exists=True))
def conversations(project_path: str):
    """List conversations for a project."""
    from ..state.session_manager import SessionManager

    try:
        manager = SessionManager()
        conversations_list = manager.list_conversations(project_path)

        if not conversations_list:
            click.echo("No conversations found for this project.")
            return

        click.echo(f"📝 Conversations for {project_path}:")
        click.echo("-" * 60)

        for conv in conversations_list:
            click.echo(f"ID: {conv.get('id', 'Unknown')}")
            click.echo(f"Created: {conv.get('created_at', 'Unknown')}")
            click.echo(f"Last Active: {conv.get('last_accessed', 'Unknown')}")
            click.echo(f"Sessions: {conv.get('session_count', 0)}")

            if "summary" in conv:
                click.echo(
                    f"Summary: {conv['summary'][:100]}{'...' if len(conv['summary']) > 100 else ''}"
                )

            click.echo("-" * 60)

    except Exception as e:
        click.echo(
            click.style(f"❌ Error retrieving conversations: {str(e)}", fg="red")
        )


@click.command()
def providers():
    """List available providers."""
    click.echo("🔌 Available Providers")
    click.echo("-" * 50)

    # STT Providers
    stt_providers = registry.list_stt_providers()
    click.echo(f"\n🎙️  STT Providers ({len(stt_providers)})")
    for provider in stt_providers:
        click.echo(f"  - {provider}")

    # AI Providers
    ai_providers = registry.list_ai_providers()
    click.echo(f"\n🤖 AI Providers ({len(ai_providers)})")
    for provider in ai_providers:
        click.echo(f"  - {provider}")

    # TTS Providers
    tts_providers = registry.list_tts_providers()
    click.echo(f"\n🔊 TTS Providers ({len(tts_providers)})")
    for provider in tts_providers:
        click.echo(f"  - {provider}")

    click.echo("\nUse --<type>-provider flag to select a specific provider.")
    click.echo("Example: conversation start --ai-provider gemini")


# AI command already imported at top of file


# Create CLI group
cli = click.Group()
cli.add_command(main, name="start")
cli.add_command(metrics)
cli.add_command(conversations)
cli.add_command(providers)
cli.add_command(ai)


if __name__ == "__main__":
    cli()
