"""STT test utility for the conversation system."""

import click
import json
import sys
import time
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import structlog


logger = structlog.get_logger()


def validate_audio_file(file_path: Path) -> None:
    """Validate that the audio file exists and has supported format."""
    if not file_path.exists():
        raise click.FileError(f"Audio file not found: {file_path}")

    # Import locally to avoid early logging
    from ..providers.stt.whisperkit_file import WhisperKitFileProvider

    supported_formats = WhisperKitFileProvider.supported_formats()
    if file_path.suffix.lower() not in supported_formats:
        raise click.BadParameter(
            f"Unsupported audio format '{file_path.suffix}'. "
            f"Supported formats: {', '.join(supported_formats)}"
        )


def read_audio_from_stdin() -> Path:
    """Read audio data from stdin and save to temporary file."""
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_path = Path(temp_file.name)

            # Read binary data from stdin
            audio_data = sys.stdin.buffer.read()

            if not audio_data:
                raise click.ClickException("No audio data received from stdin")

            temp_file.write(audio_data)

        logger.info(
            "Audio data read from stdin", temp_file=str(temp_path), size=len(audio_data)
        )
        return temp_path

    except Exception as e:
        logger.error("Failed to read audio from stdin", error=str(e))
        raise click.ClickException(f"Failed to read audio from stdin: {str(e)}")


def cleanup_temp_file(file_path: Path) -> None:
    """Clean up temporary file safely."""
    try:
        if file_path.exists():
            file_path.unlink()
            logger.debug("Cleaned up temporary file", file_path=str(file_path))
    except Exception as e:
        logger.warning(
            "Failed to cleanup temporary file", file_path=str(file_path), error=str(e)
        )


@click.command()
@click.option(
    "--input",
    "-i",
    "input_file",
    type=click.Path(exists=True, path_type=Path),
    help="Input audio file (mp3, wav, m4a, etc.). Use '-' to read from stdin.",
)
@click.option(
    "--provider", default="whisperkit", help="STT provider to use (default: whisperkit)"
)
@click.option("--model", help="Model to use (provider-specific)")
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output results in JSON format with metadata",
)
@click.option("--metrics", is_flag=True, help="Include performance metrics in output")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file",
)
@click.option(
    "--list-providers", is_flag=True, help="List available STT providers and exit"
)
def stt(
    input_file: Optional[Path],
    provider: str,
    model: Optional[str],
    json_output: bool,
    metrics: bool,
    debug: bool,
    config: Optional[Path],
    list_providers: bool,
):
    """
    Test STT (Speech-to-Text) providers with audio files.

    Examples:

        # Process audio file
        conversation-test stt --input audio.mp3

        # Use specific provider and model
        conversation-test stt --input audio.wav --provider whisperkit --model large-v3_turbo

        # JSON output with metadata
        conversation-test stt --input audio.m4a --json

        # Read from stdin (for piping)
        cat audio.wav | conversation-test stt --input -

        # Include performance metrics
        conversation-test stt --input audio.mp3 --metrics
    """

    # Setup logging only after arguments are parsed
    from ..utils.logging import setup_logging

    setup_logging(debug=debug)

    # List providers if requested
    if list_providers:
        click.echo("Available STT providers:")
        providers = [
            "whisperkit"
        ]  # For now, we only support whisperkit file processing
        for p in providers:
            click.echo(f"  - {p}")
        return

    # Validate input
    if not input_file:
        if not sys.stdin.isatty():
            # Reading from stdin
            input_file = Path("-")
        else:
            raise click.ClickException(
                "No input specified. Use --input flag or pipe audio data to stdin."
            )

    temp_file_path: Optional[Path] = None
    stt_provider = None

    try:
        # Handle stdin input
        if str(input_file) == "-":
            input_file = read_audio_from_stdin()
            temp_file_path = input_file
        else:
            # Validate file input
            validate_audio_file(input_file)

        # Load configuration if provided
        if config:
            from ..config.settings import settings

            settings.config_file = config
            settings.load_from_file()

        # Initialize provider
        logger.info("Initializing STT provider", provider=provider, model=model)

        if provider == "whisperkit":
            # Import provider locally to avoid early logging
            from ..providers.stt.whisperkit_file import WhisperKitFileProvider

            # Use file-based WhisperKit provider
            provider_kwargs: Dict[str, Any] = {"verbose": debug}
            if model:
                provider_kwargs["model"] = model

            stt_provider = WhisperKitFileProvider(**provider_kwargs)
        else:
            raise click.BadParameter(
                f"Unsupported provider '{provider}'. Available providers: whisperkit"
            )

        # Initialize the provider
        stt_provider.initialize()

        # Process the audio file
        start_time = time.time()

        transcripts = list(stt_provider.process_file(input_file))

        end_time = time.time()
        processing_time = end_time - start_time

        # Extract results
        if not transcripts:
            result_text = ""
            confidence = None
            latency = None
        else:
            # For file processing, we typically get one final transcript
            final_transcript = transcripts[-1]
            result_text = final_transcript.text
            confidence = final_transcript.confidence
            latency = final_transcript.latency

        # Prepare output
        if json_output:
            output_data = {
                "text": result_text,
                "provider": provider,
                "model": model or stt_provider.model,
                "input_file": str(input_file) if str(input_file) != "-" else "stdin",
                "metadata": {
                    "confidence": confidence,
                    "latency_ms": latency,
                    "processing_time_ms": processing_time * 1000,
                    "character_count": len(result_text),
                    "word_count": len(result_text.split()) if result_text else 0,
                },
            }

            if metrics:
                status = stt_provider.get_status()
                output_data["metrics"] = {
                    "provider_status": status,
                    "total_processing_time_ms": processing_time * 1000,
                }

            click.echo(json.dumps(output_data, indent=2))
        else:
            # Plain text output
            if result_text:
                click.echo(result_text)
            else:
                click.echo("(no speech detected)", err=True)

            # Show metrics if requested
            if metrics:
                click.echo("\n--- Metrics ---", err=True)
                click.echo(f"Processing time: {processing_time * 1000:.1f}ms", err=True)
                click.echo(f"Characters: {len(result_text)}", err=True)
                click.echo(
                    f"Words: {len(result_text.split()) if result_text else 0}", err=True
                )
                if latency:
                    click.echo(f"Provider latency: {latency:.1f}ms", err=True)

        # Log success
        logger.info(
            "STT processing completed",
            text_length=len(result_text),
            processing_time_ms=processing_time * 1000,
        )

    except Exception as e:
        logger.error("STT processing failed", error=str(e))

        if json_output:
            error_data = {
                "error": str(e),
                "provider": provider,
                "input_file": str(input_file) if input_file else "unknown",
            }
            click.echo(json.dumps(error_data))
        else:
            click.echo(f"Error: {str(e)}", err=True)

        sys.exit(1)

    finally:
        # Cleanup
        if temp_file_path:
            cleanup_temp_file(temp_file_path)

        try:
            if stt_provider is not None:
                stt_provider.stop()
        except Exception:
            pass


if __name__ == "__main__":
    stt()
