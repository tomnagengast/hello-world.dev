"""AI test subcommand for conversation-test CLI."""

import click
import json
import sys
import time
from typing import Optional
import structlog

from ..providers.ai.claude import ClaudeProvider
from ..providers.ai.gemini import GeminiProvider
from ..utils.logging import setup_logging

logger = structlog.get_logger()


@click.command()
@click.option(
    "--input", "-i", help="Text input for the AI (if not provided, reads from stdin)"
)
@click.option(
    "--provider",
    "-p",
    default="claude",
    type=click.Choice(["claude", "gemini"]),
    help="AI provider to use",
)
@click.option("--model", "-m", help="Model to use (provider-specific)")
@click.option(
    "--system",
    "-s",
    default="You are a helpful AI assistant.",
    help="System prompt to use",
)
@click.option(
    "--context",
    "-c",
    type=click.Path(exists=True),
    help="Path to conversation context JSON file",
)
@click.option(
    "--json", "json_output", is_flag=True, help="Output response as JSON with metadata"
)
@click.option("--metrics", is_flag=True, help="Include performance metrics in output")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option(
    "--streaming/--no-streaming", default=True, help="Enable/disable streaming output"
)
def ai(
    input: Optional[str],
    provider: str,
    model: Optional[str],
    system: str,
    context: Optional[str],
    json_output: bool,
    metrics: bool,
    debug: bool,
    streaming: bool,
):
    """
    Test AI providers with text input.

    Examples:
    \b
        conversation-test ai --input "Hello, how are you?"
        echo "Tell me a joke" | conversation-test ai --provider gemini
        conversation-test ai --input "Continue" --context previous.json
    """
    # Setup logging (suppress in JSON mode unless debug is explicitly enabled)
    if json_output and not debug:
        # Completely suppress logging for clean JSON output
        import logging
        import structlog

        logging.getLogger().setLevel(logging.CRITICAL)
        structlog.configure(
            processors=[],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        setup_logging(debug=debug)

    # Get input text
    if input:
        user_input = input
    else:
        # Read from stdin
        try:
            user_input = sys.stdin.read().strip()
            if not user_input:
                click.echo("Error: No input provided", err=True)
                sys.exit(1)
        except KeyboardInterrupt:
            click.echo("\nInterrupted", err=True)
            sys.exit(1)

    # Load conversation context if provided
    conversation_history = []
    if context:
        try:
            with open(context, "r") as f:
                context_data = json.load(f)
                conversation_history = context_data.get("history", [])
                logger.info(
                    "Loaded conversation context", messages=len(conversation_history)
                )
        except Exception as e:
            click.echo(f"Error loading context file: {e}", err=True)
            sys.exit(1)

    # Initialize AI provider
    try:
        if provider == "claude":
            ai_provider = ClaudeProvider(system_prompt=system, streaming=streaming)
        elif provider == "gemini":
            kwargs = {"system_prompt": system, "streaming": streaming}
            if model:
                kwargs["model_name"] = model
            ai_provider = GeminiProvider(**kwargs)
        else:
            click.echo(f"Error: Unknown provider '{provider}'", err=True)
            sys.exit(1)

        # Set conversation history
        ai_provider.conversation_history = conversation_history

        # Initialize provider
        ai_provider.initialize()

    except Exception as e:
        logger.error("Failed to initialize AI provider", error=str(e))
        click.echo(f"Error initializing {provider}: {e}", err=True)
        sys.exit(1)

    # Measure performance
    start_time = time.time()
    first_token_time = None
    full_response = ""
    response_metadata = {}

    try:
        # Stream response
        for response_chunk in ai_provider.stream_response(user_input):
            if response_chunk.is_first and first_token_time is None:
                first_token_time = time.time()

            if response_chunk.text and not json_output:
                # Stream output to stdout if not JSON mode
                click.echo(response_chunk.text, nl=False)
                sys.stdout.flush()

            if response_chunk.is_final:
                full_response = response_chunk.full_text or full_response
                response_metadata = response_chunk.metadata or {}
                break
            else:
                full_response += response_chunk.text

        end_time = time.time()

        # Calculate metrics
        total_latency_ms = (end_time - start_time) * 1000
        first_token_latency_ms = (
            (first_token_time - start_time) * 1000
            if first_token_time
            else total_latency_ms
        )

        # Output results
        if json_output:
            output_data = {
                "response": full_response,
                "provider": provider,
                "model": model,
                "system_prompt": system,
                "input": user_input,
            }

            if metrics or response_metadata:
                output_data["metadata"] = {
                    "total_latency_ms": round(total_latency_ms, 2),
                    "first_token_latency_ms": round(first_token_latency_ms, 2),
                    "response_length": len(full_response),
                    "provider_metadata": response_metadata,
                }

            # Include updated conversation history
            updated_history = ai_provider.conversation_history.copy()
            output_data["conversation_history"] = updated_history

            click.echo(json.dumps(output_data, indent=2))
        else:
            if streaming:
                # Add newline after streaming output
                click.echo()
            else:
                # Output full response for non-streaming
                click.echo(full_response)

            # Show metrics if requested
            if metrics:
                click.echo("\n--- Metrics ---", err=True)
                click.echo(f"Provider: {provider}", err=True)
                if model:
                    click.echo(f"Model: {model}", err=True)
                click.echo(f"Total latency: {total_latency_ms:.2f}ms", err=True)
                click.echo(
                    f"First token latency: {first_token_latency_ms:.2f}ms", err=True
                )
                click.echo(f"Response length: {len(full_response)} chars", err=True)

    except KeyboardInterrupt:
        click.echo("\nInterrupted", err=True)
        ai_provider.stop_streaming()
        sys.exit(1)
    except Exception as e:
        logger.error("Error during AI interaction", error=str(e))
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        # Clean up
        try:
            ai_provider.stop()
        except Exception as e:
            logger.warning("Error stopping AI provider", error=str(e))


if __name__ == "__main__":
    ai()
