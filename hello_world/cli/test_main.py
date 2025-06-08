"""Main CLI entry point for conversation-test utilities."""

import click
from .test_stt import stt


@click.group()
@click.version_option(version="1.0.0", prog_name="conversation-test")
def cli():
    """
    Developer testing utilities for the conversation system.
    
    Test individual components (STT, AI, TTS) in isolation for debugging,
    development, and performance analysis.
    """
    pass


# Add subcommands
cli.add_command(stt)


if __name__ == "__main__":
    cli()