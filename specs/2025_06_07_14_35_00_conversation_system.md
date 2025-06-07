# Conversation System PRD

## Project Overview
Build a pluggable conversation system that enables natural voice interactions with AI models, starting with a Python CLI implementation and evolving to an iOS SwiftUI app.

## Version 1.0 - Audio to Text File Streaming

### Objective
When the app starts, capture audio from the microphone and stream it to WhisperKit CLI for real-time transcription to a text file.

### Technical Requirements
- **Audio Capture**: System microphone input
- **Speech-to-Text**: WhisperKit CLI for local transcription
- **Output**: Streaming text file with transcribed content
- **Platform**: Python CLI application (macOS)

### Implementation Details
1. Audio capture using PyAudio or similar library
2. Stream audio chunks to WhisperKit CLI
3. Write transcribed text to a file in real-time
4. Handle continuous audio streaming without gaps

## End State Vision - Full Conversation System

### Architecture Overview
A modular, pluggable conversation system with three core components:

1. **Speech-to-Text (STT) Module**
   - Input: User's voice via microphone
   - Processing: Real-time audio streaming and transcription
   - Output: Text stream
   - Options: WhisperKit (local), Google Speech-to-Text, OpenAI Whisper API

2. **AI Text Processing Module**
   - Input: Transcribed user text
   - Processing: LLM inference with streaming response
   - Output: AI-generated text response
   - Options: Anthropic Claude, Google Gemini, OpenAI GPT models

3. **Text-to-Speech (TTS) Module**
   - Input: AI text response
   - Processing: Convert text to natural speech
   - Output: Audio stream to speakers
   - Options: On-device (if fast enough), ElevenLabs, Google TTS, OpenAI TTS

### Key Features
1. **Real-time Streaming**: All components should support streaming for low-latency conversation
2. **Pluggable Architecture**: Easy to swap providers for each module
3. **Natural Conversation Flow**: Similar to Google Gemini Live, Grok voice mode, OpenAI Advanced Voice Mode
4. **Error Handling**: Graceful fallbacks and recovery
5. **Privacy**: Option for fully on-device processing where possible

### User Experience Goals
- **Latency**: < 300ms between user speech end and AI response start
- **Natural Flow**: Support interruptions and continuous conversation
- **Voice Quality**: High-quality, natural-sounding TTS output
- **Reliability**: Robust handling of network issues and API failures

### Development Phases

#### Phase 1: Full CLI Conversation System (Current)
- Python-based implementation
- Complete conversation loop:
  - Audio capture from microphone
  - Speech-to-text via WhisperKit CLI (streaming to text file)
  - AI model integration (Claude, Gemini, or GPT)
  - Text-to-speech output (ElevenLabs or alternatives)
- Pluggable architecture for easy provider swapping
- Real-time streaming throughout the pipeline
- Test all integration patterns

#### Phase 2: Advanced CLI Features
- Multiple provider support with configuration
- Conversation history and session management
- Voice customization options
- Performance optimizations
- Error handling and fallback mechanisms

#### Future: iOS App Development (Unplanned)
- SwiftUI interface
- Migrate to Swift-based audio handling
- Native iOS integration
- Mobile-optimized UI/UX

## Implementation Specifications

### Audio Configuration
- **Sample Rate**: 16 kHz (required by Whisper)
- **Format**: Mono audio
- **Chunking**: 30-second chunks (optimal for Whisper)
- **VAD**: Use WhisperKit's built-in `--chunking-strategy vad`
- **Model**: Large v3 Turbo with Neural Engine acceleration

### WhisperKit Integration
- **Command**: `whisperkit-cli transcribe --stream --model "large-v3_turbo" --chunking-strategy vad`
- **Compute Units**: `--audio-encoder-compute-units cpuAndNeuralEngine --text-decoder-compute-units cpuAndNeuralEngine`
- **Approach**: Use WhisperKit's built-in streaming mode for simplicity
- **Model**: Uses auto-download `large-v3_turbo` model for optimal performance

### AI Providers

#### Claude Integration (Primary)
- **Method**: Claude Code SDK as subprocess
- **Command**: `claude --output-format stream-json --system-prompt "You are a breezy but focused senior developer who gets straight to the point without getting stuck in the weeds. Be conversational but efficient."`
- **Authentication**: N/A; User will be pre-authenticated
- **Advantages**: Built-in conversation management, MCP support, streaming JSON output

#### Gemini Integration (Secondary)
- **Method**: Direct API calls to Gemini API
- **Endpoint**: `https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:streamGenerateContent`
- **Authentication**: `GOOGLE_API_KEY` environment variable
- **System Prompt**: Same as Claude, set in initial message

**Implementation Note**: Claude uses the Claude Code SDK subprocess for richer features, while Gemini uses direct API calls for simplicity.

### Configuration Management
- **Method**: `.env` file for API keys and provider selection
- **Example**:
  ```
  ANTHROPIC_API_KEY=sk-ant-...
  GOOGLE_API_KEY=...
  ELEVENLABS_API_KEY=...
  AI_PROVIDER=claude  # or gemini
  TTS_PROVIDER=elevenlabs
  ```

### Error Handling
- **WhisperKit Crash**: Notify user and auto-restart (max 3 retries)
- **API Timeouts**:
  - AI responses: 30 seconds
  - TTS generation: 10 seconds
- **Audio Buffer**: Maintain 30-second rolling buffer for recovery
- **Network Failures**: Exponential backoff with max 3 retries

### Conversation Flow
- **Interruption**: Immediately stop TTS playback when user speaks
- **Input Detection**: Continuous listening with VAD
- **Turn Management**: Clear audio cues when switching between listening/speaking

### Logging Strategy
- **Location**: `./logs/conversation_YYYY-MM-DD_HH-MM-SS.log`
- **Console**: Show logs in debug/verbose mode only
- **Format**: JSON structured logging for easy parsing
- **Rotation**: Daily rotation, keep last 7 days

### Development Features
- **Mock Mode**: `--mock` flag for testing without API calls
- **Mock Responses**: Pre-recorded responses in `./mocks/` directory
- **Debug Mode**: `--debug` flag for verbose logging
- **Dry Run**: `--dry-run` to test pipeline without API calls

## Technical Architecture

### Stream-Based with Process Pipes

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Python Process                       │
│  ┌─────────────┐    ┌─────────┐    ┌─────────┐            │
│  │ WhisperKit  │───▶│   AI    │───▶│   TTS   │            │
│  │  Process    │pipe│ Thread  │pipe│ Thread  │            │
│  │  (--stream) │    │         │    │         │            │
│  └─────────────┘    └─────────┘    └─────────┘            │
└─────────────────────────────────────────────────────────────┘
       │                   │              │
       ▼                   ▼              ▼
  Microphone →        Response Stream  Audio Out
  Text Stream

```

**Key Components:**
- **WhisperKit Process**: Subprocess using `--stream` flag for direct microphone access
- **AI Thread**: Async HTTP streaming with AI provider (Claude/Gemini)
- **TTS Thread**: Streams response text to TTS API (ElevenLabs)
- **Interruption Handler**: Monitors WhisperKit output to stop TTS on new speech

**Implementation Details:**
```python
# Simplified structure leveraging WhisperKit's streaming
class ConversationSystem:
    def __init__(self):
        self.transcript_queue = Queue()
        self.response_queue = Queue()
        self.tts_playing = False
        self.ai_provider = os.getenv('AI_PROVIDER', 'claude')

    def whisperkit_process(self):
        # Start WhisperKit with --stream flag
        # Parse stdout for transcripts → transcript_queue

    def ai_thread(self):
        # transcript_queue → AI provider → response_queue
        if self.ai_provider == 'claude':
            # Use Claude Code SDK subprocess
            # claude --output-format stream-json
        else:  # gemini
            # Direct API call to Gemini streaming endpoint
        # Handle interruptions by clearing queues

    def tts_thread(self):
        # response_queue → TTS API → Audio output
        # Check self.tts_playing for interruption
```

**Benefits:**
- Lower latency with true streaming
- Memory-efficient (no disk I/O)
- Better for real-time interactions
- Can handle interruptions effectively
- Balanced complexity vs performance

## Technical Considerations
1. **Audio Formats**: Support common formats (WAV, MP3, AAC)
2. **Streaming Protocols**: WebSocket or Server-Sent Events for real-time communication
3. **Buffer Management**: Optimize for low-latency audio processing
4. **API Rate Limits**: Handle provider limits gracefully
5. **Cost Optimization**: Monitor and optimize API usage

### Success Metrics
- Response latency < 500ms
- Transcription accuracy > 95%
- Natural conversation flow rating > 4.5/5
- System uptime > 99.9%

### References
- [Google Gemini Live](https://support.google.com/gemini/answer/15274899?hl=en&co=GENIE.Platform%3DAndroid)
- [Grok Voice Mode](https://www.reddit.com/r/grok/comments/1kch9m3/grok_has_the_best_voice_mode_by_far_and_its_not/)
- [OpenAI Voice Mode FAQ](https://help.openai.com/en/articles/8400625-voice-mode-faq)
- [Claude Mobile Voice Mode](https://support.anthropic.com/en/articles/11101966-using-voice-mode-on-claude-mobile-apps)

## Dependencies

### System Requirements
- **OS**: macOS 14.0+ (Apple Silicon required)
- **Python**: 3.11+
- **WhisperKit CLI**: Already installed (`/opt/homebrew/bin/whisperkit-cli`)

### Python Dependencies
```toml
[project.dependencies]
python-dotenv = ">=1.0.0"      # Environment management
google-generativeai = ">=0.3.0" # Gemini API
elevenlabs = ">=2.0.0"         # TTS
pygame = ">=2.5.0"             # Audio playback
structlog = ">=23.0.0"         # Structured logging
click = ">=8.0.0"              # CLI interface
```

### External Dependencies
- **Claude Code SDK**: Installed via `npm install -g @anthropic-ai/claude-code` (requires Node.js)
- **WhisperKit CLI**: Already installed at `/opt/homebrew/bin/whisperkit-cli`

## Implementation Plan

### Phase 1.1: Core Pipeline (Week 1)
1. Set up project structure and dependencies
2. Implement WhisperKit subprocess management
3. Create basic Claude integration with streaming
4. Add ElevenLabs TTS with pygame playback
5. Test end-to-end conversation flow

### Phase 1.2: Robustness (Week 2)
1. Add interruption handling
2. Implement error recovery and retries
3. Add structured logging
4. Create mock mode for testing
5. Add Gemini as secondary AI provider

### Phase 1.3: Polish (Week 3)
1. Optimize latency and performance
2. Add configuration management
3. Implement conversation history
4. Create comprehensive test suite
5. Documentation and deployment scripts

## Additional Implementation Details

### WhisperKit Output Format
- **Streaming Output**: Plain text transcripts output line-by-line to stdout
- **Format**: Direct text output without timestamps or metadata in streaming mode
- **Example**: `" Daya is an open weights text to to dialogue model. You get full control over scripts and Voices. Wow, amazing. Try it now on GitHub or Hugging Face."`

### Model Management
- **Model Selection**: `large-v3_turbo` using WhisperKit's auto-download
- **Local Resources**: Pre-downloaded models available in `resources/whisperkit/models/` (backup)
- **Sample Audio**: Test files available in `resources/whisperkit/samples/`
- **First Run**: Model will be downloaded and cached automatically

### Metrics Collection
- **Track Performance Metrics**:
  - STT latency (speech end to transcript)
  - AI response latency (transcript to first token)
  - TTS latency (text to audio start)
  - End-to-end conversation latency
- **Storage**: Metrics saved to `./metrics/YYYY-MM-DD.json`
- **Dashboard**: Simple CLI command to view performance trends

### Conversation State Management
- **Hierarchical Structure**:
  ```
  Projects/
  └── project_path_hash/
      ├── metadata.json (project name, path, created)
      └── conversations/
          ├── conv_<uuid-v7>/
          │   ├── metadata.json (created, last_accessed)
          │   └── sessions/
          │       ├── session_<uuid-v7>.json
          │       └── session_<uuid-v7>.json
          └── conv_<uuid-v7>/
  ```
- **Project Association**: Each project identified by hashed file path
- **Multiple Conversations**: Users can have multiple conversation threads per project
- **Session Continuity**: Each conversation can span multiple sessions
- **Storage Location**: `~/.conversation-system/projects/`
