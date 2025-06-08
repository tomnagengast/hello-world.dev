# Plugin Configuration System PRD

## Problem Space

The conversation system currently has rigid provider configuration:
- **Fixed Providers**: Users cannot easily switch between STT/AI/TTS providers
- **High Costs**: Third-party services require subscriptions and API fees
- **Privacy Concerns**: All audio/text data goes through external services
- **Platform Underutilization**: macOS native capabilities are not leveraged

Users need flexibility to choose providers based on their priorities: cost, privacy, quality, or latency.

## Proposed Architecture & Solution

### CLI Provider Selection
Enable provider selection via command-line flags:
```bash
# Native Apple providers (free, private, low-latency)
conversation start --stt apple --tts apple

# Mix and match providers
conversation start --stt whisperkit --model gemini --tts apple

# List available providers
conversation providers
```

### Provider Architecture
Extend the existing provider base classes to support new implementations:

```python
# hello_world/providers/stt/apple.py
class AppleSTTProvider(STTProvider):
    """Native macOS Speech Recognition via SFSpeechRecognizer"""
    
# hello_world/providers/tts/apple.py  
class AppleTTSProvider(TTSProvider):
    """Native macOS TTS via AVSpeechSynthesizer"""
```

### Registry Integration
Update the provider registry to:
- Auto-discover available providers
- Check platform compatibility
- Validate dependencies
- Handle graceful fallbacks

## Workstreams

### Workstream 1: CLI Infrastructure
**Goal**: Add provider selection flags to the CLI
- Update `hello_world/cli/main.py` with `--stt`, `--model`, `--tts` options
- Modify provider initialization to use CLI arguments
- Add `conversation providers` command for discovery
- Update help documentation

### Workstream 2: Apple STT Provider
**Goal**: Implement native macOS speech-to-text
- Create `hello_world/providers/stt/apple.py`
- Implement `AppleSTTProvider` using SFSpeechRecognizer
- Handle microphone permissions
- Support streaming transcription
- Add to provider registry

### Workstream 3: Apple TTS Provider  
**Goal**: Implement native macOS text-to-speech
- Create `hello_world/providers/tts/apple.py`
- Implement `AppleTTSProvider` using AVSpeechSynthesizer
- Support voice selection and configuration
- Handle audio output and interruptions
- Add to provider registry

### Workstream 4: Provider Registry Enhancement
**Goal**: Improve provider management and discovery
- Add platform compatibility checking
- Implement dependency validation
- Create provider capability queries
- Add fallback logic for unavailable providers

### Workstream 5: Testing & Documentation
**Goal**: Ensure quality and usability
- Unit tests for new providers
- Integration tests for provider combinations
- Update README with provider information
- Create migration guide

## Implementation References

### Apple Framework Documentation
- [SFSpeechRecognizer](https://developer.apple.com/documentation/speech/sfspeechrecognizer) - Apple STT framework
- [AVSpeechSynthesizer](https://developer.apple.com/documentation/avfaudio/avspeechsynthesizer) - Apple TTS framework
- [PyObjC](https://pyobjc.readthedocs.io/) - Python-Objective-C bridge

### Existing Codebase References
- `hello_world/providers/` - Provider implementations
- `hello_world/providers/registry.py` - Provider registration system
- `hello_world/cli/main.py` - CLI entry point
- `hello_world/config/settings.py` - Configuration management

### Design Patterns
- [Strategy Pattern](https://refactoring.guru/design-patterns/strategy) - Provider abstraction
- [Registry Pattern](https://martinfowler.com/eaaCatalog/registry.html) - Provider discovery

## Dependencies

```toml
[project.optional-dependencies]
apple-providers = [
    "pyobjc-core>=9.0",
    "pyobjc-framework-AVFoundation>=9.0", 
    "pyobjc-framework-Speech>=9.0",
]
```