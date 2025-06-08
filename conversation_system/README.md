# Conversation System Architecture

This is the project architecture for the conversation system. The implementation uses pseudocode throughout, allowing the dev team to fill in the actual implementation details.

## Directory Structure

```
conversation_system/
├── core/
│   └── conversation_manager.py    # Main orchestrator
├── providers/
│   ├── stt/
│   │   ├── base.py               # STT interface
│   │   └── whisperkit.py         # WhisperKit implementation
│   ├── ai/
│   │   ├── base.py               # AI provider interface
│   │   ├── claude.py             # Claude Code SDK implementation
│   │   └── gemini.py             # Gemini API implementation
│   └── tts/
│       ├── base.py               # TTS interface
│       └── elevenlabs.py         # ElevenLabs implementation
├── state/
│   └── session_manager.py        # Session & conversation management
├── metrics/
│   └── collector.py              # Performance metrics collection
├── utils/
│   ├── interruption_handler.py   # Interruption coordination
│   └── logging.py                # Logging configuration
├── config/
│   └── settings.py               # Configuration management
└── cli/
    └── main.py                   # CLI entry point
```

## Key Components

### 1. ConversationManager (`core/conversation_manager.py`)
- Main orchestrator that manages the entire pipeline
- Coordinates STT → AI → TTS flow
- Handles threading and queue management
- Manages interruptions and error recovery

### 2. Provider System (`providers/`)
- **Base Classes**: Define interfaces for each provider type
- **Implementations**: Concrete implementations with pseudocode
  - WhisperKit: Subprocess-based STT
  - Claude: Claude Code SDK subprocess
  - Gemini: Direct API calls
  - ElevenLabs: Streaming TTS with pygame

### 3. State Management (`state/session_manager.py`)
- Hierarchical storage: Projects → Conversations → Sessions
- Persistence to `~/.conversation-system/projects/`
- Session history and metadata tracking

### 4. Metrics Collection (`metrics/collector.py`)
- Tracks STT, AI, TTS, and E2E latencies
- Daily JSON file storage
- Summary statistics and reporting

### 5. Configuration (`config/settings.py`)
- Centralized settings management
- Environment variable overrides
- Provider-specific configurations

### 6. CLI Interface (`cli/main.py`)
- Click-based command line interface
- Commands: `start`, `metrics`, `conversations`
- Debug, mock, and dry-run modes

## Implementation Guide

### For the Dev Team:

1. **Start with Core Components**:
   - Implement the actual subprocess management in WhisperKit provider
   - Get basic STT working with transcript queue

2. **Add AI Providers**:
   - Claude: Implement subprocess communication with Claude Code SDK
   - Gemini: Implement HTTP streaming with google-generativeai library

3. **Complete TTS Integration**:
   - Implement ElevenLabs streaming
   - Get pygame audio playback working

4. **Wire Everything Together**:
   - Complete the ConversationManager threading logic
   - Implement interruption handling
   - Add error recovery

5. **Polish**:
   - Complete metrics collection
   - Implement session persistence
   - Add comprehensive logging

## Key Design Decisions

1. **Threading Model**: Separate threads for STT, AI, and TTS with queue-based communication
2. **Interruption Handling**: Centralized through InterruptionHandler with callbacks
3. **Provider Abstraction**: Clean interfaces allow easy provider swapping
4. **State Persistence**: Hierarchical structure for multi-project/conversation support
5. **Configuration**: Layered approach (file → env vars → CLI args)

## Running the System

```bash
# Install dependencies
uv sync

# Basic usage (preferred - uses installed script)
conversation start

# Or use uv run for development
uv run python -m conversation_system.cli.main start

# With project association
conversation start --project /path/to/project

# Debug mode
conversation start --debug

# Mock mode (no API calls)
conversation start --mock

# Run tests with uv
uv run pytest tests/
```

## Next Steps

The pseudocode provides the structure and flow. The dev team should:
1. Replace pseudocode with actual implementations
2. Add error handling for edge cases
3. Optimize for latency
4. Add tests for each component
5. Fine-tune interruption detection