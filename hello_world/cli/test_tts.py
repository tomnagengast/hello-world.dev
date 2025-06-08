"""TTS test command for conversation-test CLI."""

import click
import sys
import time
from typing import Optional

from .tts_utility import TTSTestUtility


@click.command()
@click.option(
    "--input", "-i",
    help="Text to convert to speech (if not provided, reads from stdin)"
)
@click.option(
    "--voice", "-v",
    help="Voice to use for TTS"
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Output file path (default: play through speakers)"
)
@click.option(
    "--provider", "-p",
    default="elevenlabs",
    help="TTS provider to use (default: elevenlabs)"
)
@click.option(
    "--speed",
    type=float,
    default=1.0,
    help="Speech speed multiplier (default: 1.0)"
)
@click.option(
    "--metrics", "-m",
    is_flag=True,
    help="Show performance metrics"
)
@click.option(
    "--format",
    type=click.Choice(["mp3", "wav"]),
    default="mp3",
    help="Output audio format (default: mp3)"
)
@click.pass_context
def tts(ctx, input: Optional[str], voice: Optional[str], output: Optional[str], 
        provider: str, speed: float, metrics: bool, format: str):
    """Test text-to-speech functionality."""
    debug = ctx.obj.get("debug", False) if ctx.obj else False
    
    # Get text input
    if input:
        text = input
    else:
        # Read from stdin
        try:
            text = sys.stdin.read().strip()
            if not text:
                click.echo("Error: No input text provided", err=True)
                sys.exit(1)
        except KeyboardInterrupt:
            click.echo("\nCancelled", err=True)
            sys.exit(1)
    
    if not text:
        click.echo("Error: Empty input text", err=True)
        sys.exit(1)
    
    try:
        # Initialize TTS utility
        utility = TTSTestUtility(
            provider=provider,
            voice=voice,
            speed=speed,
            debug=debug
        )
        
        # Run TTS test
        start_time = time.time()
        success = utility.run_tts_test(
            text=text,
            output_file=output,
            output_format=format
        )
        end_time = time.time()
        
        if success:
            if metrics:
                duration = end_time - start_time
                click.echo("\n📊 Metrics:")
                click.echo(f"  Total time: {duration:.2f}s")
                click.echo(f"  Text length: {len(text)} characters")
                click.echo(f"  Provider: {provider}")
                if voice:
                    click.echo(f"  Voice: {voice}")
                click.echo(f"  Speed: {speed}x")
                
                # Get additional metrics from utility
                util_metrics = utility.get_metrics()
                for key, value in util_metrics.items():
                    if isinstance(value, float):
                        click.echo(f"  {key}: {value:.2f}")
                    else:
                        click.echo(f"  {key}: {value}")
        else:
            sys.exit(1)
            
    except Exception as e:
        if debug:
            import structlog
            logger = structlog.get_logger()
            logger.error("TTS test failed", error=str(e), exc_info=True)
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)