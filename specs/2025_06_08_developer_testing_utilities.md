# Developer Testing Utilities PRD

## Problem Space

Developers working on the conversation system need to test and debug individual components (STT, AI, TTS) in isolation. Currently, the only way to test these components is through the full conversation flow, which makes it difficult to:
- Debug specific component failures
- Test edge cases for individual components
- Benchmark performance of individual stages
- Develop and iterate on single components without running the entire pipeline

## Solution Overview

Create standalone CLI utilities for each core component that allow developers to:
1. **STT Utility**: Test speech-to-text with audio files, outputting transcribed text
2. **AI Utility**: Test AI providers with text input, outputting generated responses
3. **TTS Utility**: Test text-to-speech with text input, playing audio through system speakers

## Technical Implementation

### Architecture: Dedicated Test CLI

We will create a new `conversation-test` CLI with subcommands for each testing utility. This approach provides:
- Clean separation of concerns between production and testing utilities
- Extensibility for future test utilities and debugging tools
- Consistent interface across all test commands
- Dedicated space for test-specific features without cluttering the main CLI

### Component Specifications

#### STT Test Utility
```bash
# Usage
conversation-test stt --input audio.mp3 [--model whisperkit] [--device cuda]

# Features
- Accept audio files (mp3, wav, m4a)
- Support streaming from stdin for piping
- Output transcribed text to stdout
- Optional JSON output with metadata (confidence, timing)
- Support all configured STT providers
```

#### AI Test Utility
```bash
# Usage
conversation-test ai --input "Hello, how are you?" [--provider claude] [--model opus]

# Features
- Accept text from command line or stdin
- Support conversation context via --context flag
- Output AI response to stdout
- Optional JSON output with metadata (tokens, latency)
- Support all configured AI providers
- System prompt configuration via --system flag
```

#### TTS Test Utility
```bash
# Usage
conversation-test tts --input "Hello world" [--voice rachel] [--output audio.mp3]

# Features
- Accept text from command line or stdin
- Play audio through system speakers by default
- Optional output to file
- Support all configured TTS providers
- Voice selection and configuration
- Speed/pitch adjustments where supported
```

### Common Features

All utilities should support:
- `--debug` flag for verbose logging
- `--config` flag for custom configuration file
- `--list-providers` to show available providers
- `--help` with detailed usage examples
- Performance metrics output with `--metrics`
- Error handling with clear messages

## Workstreams

### Workstream 1: CLI Infrastructure (Can start immediately)
- Create new `conversation-test` CLI entry point
- Set up command structure and argument parsing
- Implement common utilities (config loading, error handling)
- Add provider listing functionality

### Workstream 2: STT Test Utility (Can start immediately)
- Implement audio file loading
- Integrate with existing STT providers
- Add stdout output formatting
- Implement JSON output mode
- Add performance metrics

### Workstream 3: AI Test Utility (Can start immediately)
- Implement text input handling
- Integrate with existing AI providers
- Add conversation context support
- Implement JSON output mode
- Add performance metrics

### Workstream 4: TTS Test Utility (Can start immediately)
- Implement text input handling
- Integrate with existing TTS providers
- Add audio playback functionality
- Implement file output option
- Add performance metrics

### Workstream 5: Documentation & Examples (After workstreams 1-4)
- Create comprehensive documentation
- Add example scripts and use cases
- Update main README with testing utilities
- Create troubleshooting guide

## Success Criteria

1. Developers can test each component in isolation
2. All utilities support piping for Unix-style workflows
3. Performance metrics help identify bottlenecks
4. Clear error messages aid in debugging
5. Documentation enables quick adoption

## Decisions

1. **Batch processing**: Not supported initially - focus on single input operations
2. **GUI interface**: Not for initial release - CLI-only approach
3. **Recording/capturing for STT**: Not included - use existing audio files
4. **Provider-specific configuration**: To be determined based on provider requirements during implementation

## Future Enhancements

- Integration with pytest for automated testing
- Performance regression testing
- Mock providers for unit testing
- WebSocket/HTTP API versions for remote testing
- Visual waveform display for audio utilities
