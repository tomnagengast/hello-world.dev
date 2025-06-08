"""Setup script for the conversation system."""

from setuptools import setup, find_packages

setup(
    name="conversation-system",
    version="1.0.0",
    description="Natural voice interactions with AI models",
    author="Your Name",
    packages=find_packages(include=['hello_world', 'hello_world.*']),
    python_requires=">=3.11",
    install_requires=[
        "python-dotenv>=1.0.0",
        "google-generativeai>=0.3.0",
        "elevenlabs>=2.0.0",
        "pygame>=2.5.0",
        "structlog>=23.0.0",
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "conversation=hello_world.cli.main:cli",
            "conversation-test=hello_world.cli.test_main:cli",
        ],
    },
)