"""CLI entry point for the conversation system."""

import click
import asyncio
import signal
import sys
from pathlib import Path
import structlog
from typing import Optional

from ..core.conversation_manager import ConversationManager, ConversationConfig
from ..config.settings import settings
from ..metrics.collector import MetricsCollector
from ..utils.logging import setup_logging


logger = structlog.get_logger()


# Global conversation manager for signal handling
conversation_manager: Optional[ConversationManager] = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal")
    if conversation_manager:
        conversation_manager.stop()
    sys.exit(0)


@click.command()
@click.option('--project', '-p', type=click.Path(), 
              help='Project path to associate with conversation')
@click.option('--ai-provider', type=click.Choice(['claude', 'gemini']), 
              default='claude', help='AI provider to use')
@click.option('--tts-provider', type=click.Choice(['elevenlabs']), 
              default='elevenlabs', help='TTS provider to use')
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--mock', is_flag=True, help='Run in mock mode (no API calls)')
@click.option('--dry-run', is_flag=True, help='Test pipeline without API calls')
@click.option('--config', type=click.Path(exists=True), 
              help='Path to configuration file')
@click.option('--no-interruptions', is_flag=True, 
              help='Disable interruption handling')
@click.option('--no-metrics', is_flag=True, 
              help='Disable metrics collection')
def main(project: Optional[str], 
         ai_provider: str,
         tts_provider: str,
         debug: bool,
         mock: bool,
         dry_run: bool,
         config: Optional[str],
         no_interruptions: bool,
         no_metrics: bool):
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
    settings.ai_provider = ai_provider
    settings.tts_provider = tts_provider
    
    # Create conversation config
    conversation_config = ConversationConfig(
        ai_provider=ai_provider,
        tts_provider=tts_provider,
        enable_interruptions=not no_interruptions,
        enable_metrics=not no_metrics,
        debug_mode=debug,
        mock_mode=mock or dry_run
    )
    
    # Initialize conversation manager
    conversation_manager = ConversationManager(conversation_config)
    
    # Display startup information
    click.echo(click.style("🎙️  Conversation System Starting...", fg='green', bold=True))
    click.echo(f"AI Provider: {ai_provider}")
    click.echo(f"TTS Provider: {tts_provider}")
    click.echo(f"Project: {project or 'None'}")
    
    if mock:
        click.echo(click.style("⚠️  Running in MOCK mode - no API calls will be made", fg='yellow'))
    elif dry_run:
        click.echo(click.style("⚠️  Running in DRY RUN mode - testing pipeline only", fg='yellow'))
        
    click.echo("\nPress Ctrl+C to stop the conversation.\n")
    
    try:
        # Start the conversation system
        conversation_manager.start(project_path=project)
        
        # Keep the main thread alive
        while True:
            # PSEUDOCODE: Main loop
            # - Display status updates
            # - Handle user commands (if any)
            # - Sleep to prevent CPU spinning
            import time
            time.sleep(1)
            
    except KeyboardInterrupt:
        click.echo("\n\nShutting down...")
    except Exception as e:
        logger.error("Fatal error", error=str(e), exc_info=True)
        click.echo(click.style(f"\n❌ Error: {str(e)}", fg='red'))
    finally:
        if conversation_manager:
            # Save metrics if enabled
            if conversation_config.enable_metrics and conversation_manager.metrics_collector:
                summary = conversation_manager.metrics_collector.get_summary()
                conversation_manager.metrics_collector.save_metrics()
                
                # Display session summary
                click.echo("\n📊 Session Summary:")
                click.echo(f"Duration: {summary['session_duration_seconds']:.1f}s")
                click.echo(f"Interactions: {summary['total_interactions']}")
                
                if summary['total_interactions'] > 0:
                    click.echo(f"Avg E2E Latency: {summary['e2e_latency_ms']['avg']:.0f}ms")
                    
            conversation_manager.stop()
            
        click.echo("\n👋 Goodbye!")


@click.command()
@click.option('--days', '-d', default=7, help='Number of days to include in report')
@click.option('--format', type=click.Choice(['text', 'json']), 
              default='text', help='Output format')
def metrics(days: int, format: str):
    """View performance metrics."""
    collector = MetricsCollector()
    
    if format == 'json':
        # PSEUDOCODE: Output JSON report
        # report = collector.generate_report(days=days)
        # click.echo(json.dumps(report, indent=2))
        pass
    else:
        # PSEUDOCODE: Output text report
        # report = collector.generate_report(days=days)
        # click.echo("📊 Performance Metrics Report")
        # click.echo(f"Last {days} days")
        # click.echo("-" * 40)
        # # Format and display report...
        pass


@click.command()
@click.argument('project_path', type=click.Path(exists=True))
def conversations(project_path: str):
    """List conversations for a project."""
    from ..state.session_manager import SessionManager
    
    manager = SessionManager()
    conversations = manager.list_conversations(project_path)
    
    if not conversations:
        click.echo("No conversations found for this project.")
        return
        
    click.echo(f"📝 Conversations for {project_path}:")
    click.echo("-" * 60)
    
    # PSEUDOCODE: Display conversations
    # for conv in conversations:
    #     click.echo(f"ID: {conv['id']}")
    #     click.echo(f"Created: {conv['created_at']}")
    #     click.echo(f"Last Active: {conv['last_accessed']}")
    #     click.echo(f"Sessions: {conv['session_count']}")
    #     click.echo("-" * 60)


# Create CLI group
cli = click.Group()
cli.add_command(main, name='start')
cli.add_command(metrics)
cli.add_command(conversations)


if __name__ == '__main__':
    cli()