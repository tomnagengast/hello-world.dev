# Conversation System

A pluggable conversation system that enables natural voice interactions with AI models using WhisperKit for speech-to-text, Claude/Gemini for AI responses, and ElevenLabs for text-to-speech.

## Features

- 🎙️ **Real-time Speech Recognition**: WhisperKit with Large v3 Turbo model
- 🤖 **AI Integration**: Claude (via Code SDK) and Gemini support
- 🔊 **Natural TTS**: ElevenLabs streaming text-to-speech
- 🔄 **Interruption Handling**: Natural conversation flow with interruptions
- 📊 **Performance Metrics**: Track latencies and system performance
- 💾 **Session Management**: Hierarchical conversation state persistence
- 🔌 **Pluggable Architecture**: Easy provider swapping

## Quick Start

```bash
# Install dependencies
uv sync

# Basic usage (after uv sync, the 'conversation' command is available)
conversation start

# Or run directly with Python
python -m conversation_system.cli.main start

# With project association
conversation start --project /path/to/project

# Debug mode
conversation start --debug

# View metrics
conversation metrics --days 7

# List conversations for a project
conversation conversations /path/to/project
```

## Architecture

See [conversation_system/README.md](conversation_system/README.md) for detailed architecture documentation.

## Requirements

- macOS 14.0+ (Apple Silicon)
- Python 3.11+
- WhisperKit CLI
- Node.js (for Claude Code SDK)

## Documentation

- [PRD](specs/2025_06_07_14_35_00_conversation_system.md) - Product Requirements Document
- [Architecture](conversation_system/README.md) - Technical architecture guide

## Resources
- [WhisperKit Large v3 Turbo Docs](https://huggingface.co/openai/whisper-large-v3-turbo)
- [Claude Code SDK Docs](https://docs.anthropic.com/en/docs/claude-code/sdk)
- [Gemini API Docs](https://ai.google.dev/gemini-api/docs)
- [ElevenLabs Docs](https://elevenlabs.io/docs)
