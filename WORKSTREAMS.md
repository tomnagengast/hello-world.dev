# Development Workstreams

The project has been divided into 5 parallel workstreams. Each has its own git worktree for concurrent development.

## Worktree Locations

All worktrees are in `../hello-world-worktrees/`:

```bash
hello-world-worktrees/
├── stt-whisperkit/     # Stream 1: Speech-to-Text
├── ai-providers/       # Stream 2: AI Providers
├── tts-elevenlabs/     # Stream 3: Text-to-Speech
├── state-metrics/      # Stream 4: State & Metrics
└── cli-interface/      # Stream 5: CLI & Integration
```

## Stream 1: STT WhisperKit Implementation
**Branch**: `feature/stt-whisperkit`  
**Worktree**: `../hello-world-worktrees/stt-whisperkit`  
**Owner**: Dev 1

### Tasks:
1. Implement WhisperKit subprocess management in `providers/stt/whisperkit.py`
2. Handle streaming output parsing from WhisperKit CLI
3. Implement VAD-based speech detection
4. Add error recovery for process crashes
5. Create unit tests for STT provider

### Files to modify:
- `conversation_system/providers/stt/whisperkit.py`
- `conversation_system/providers/stt/base.py` (if needed)

### Dependencies: None (can start immediately)

---

## Stream 2: AI Providers Implementation
**Branch**: `feature/ai-providers`  
**Worktree**: `../hello-world-worktrees/ai-providers`  
**Owner**: Dev 2 & Dev 3

### Tasks:
1. **Dev 2**: Implement Claude provider using subprocess
   - Handle Claude Code SDK subprocess communication
   - Parse streaming JSON responses
   - Implement conversation history management
   
2. **Dev 3**: Implement Gemini provider using API
   - Set up google-generativeai client
   - Handle streaming responses
   - Implement retry logic

### Files to modify:
- `conversation_system/providers/ai/claude.py`
- `conversation_system/providers/ai/gemini.py`
- `conversation_system/providers/ai/base.py` (if needed)

### Dependencies: None (can start immediately)

---

## Stream 3: TTS ElevenLabs Implementation
**Branch**: `feature/tts-elevenlabs`  
**Worktree**: `../hello-world-worktrees/tts-elevenlabs`  
**Owner**: Dev 4

### Tasks:
1. Implement ElevenLabs streaming TTS in `providers/tts/elevenlabs.py`
2. Set up pygame audio playback with buffering
3. Handle audio chunk streaming and queueing
4. Implement interruption support (stop playback)
5. Create unit tests for TTS provider

### Files to modify:
- `conversation_system/providers/tts/elevenlabs.py`
- `conversation_system/providers/tts/base.py` (if needed)

### Dependencies: None (can start immediately)

---

## Stream 4: State Management & Metrics
**Branch**: `feature/state-metrics`  
**Worktree**: `../hello-world-worktrees/state-metrics`  
**Owner**: Dev 5

### Tasks:
1. Implement session persistence in `state/session_manager.py`
2. Create directory structure for projects/conversations
3. Implement metrics collection in `metrics/collector.py`
4. Add JSON file I/O for sessions and metrics
5. Create reporting functionality

### Files to modify:
- `conversation_system/state/session_manager.py`
- `conversation_system/metrics/collector.py`

### Dependencies: None (can start immediately)

---

## Stream 5: CLI Interface & Core Integration
**Branch**: `feature/cli-interface`  
**Worktree**: `../hello-world-worktrees/cli-interface`  
**Owner**: Dev 6 (Integration Lead)

### Tasks:
1. Complete CLI command implementations in `cli/main.py`
2. Wire up conversation manager in `core/conversation_manager.py`
3. Implement threading and queue management
4. Add interruption handling logic
5. Create integration tests

### Files to modify:
- `conversation_system/cli/main.py`
- `conversation_system/core/conversation_manager.py`
- `conversation_system/utils/interruption_handler.py`
- `conversation_system/utils/logging.py`
- `conversation_system/config/settings.py`

### Dependencies: Will need basic implementations from other streams for integration testing

---

## Working with Worktrees

### For each developer:

```bash
# Navigate to your worktree
cd ../hello-world-worktrees/<your-stream>

# You're already on your feature branch
git status

# Make changes and commit
git add <files>
git commit -m "feat: implement <feature>"

# Push to your branch
git push origin feature/<your-branch>

# Create PR when ready
gh pr create --title "Feature: <description>" --body "Implements <details>"
```

### Syncing with main:

```bash
# In your worktree
git fetch origin
git merge origin/main
```

### Integration meetings:
- Daily standup to discuss progress
- Stream 5 (Integration Lead) coordinates testing
- Merge features to main after testing

---

## Timeline

### Week 1:
- Streams 1-4: Implement core functionality
- Stream 5: Set up integration framework

### Week 2:
- All streams: Complete implementation
- Stream 5: Begin integration testing
- Fix issues found during integration

### Week 3:
- Full system testing
- Performance optimization
- Documentation updates

---

## Notes

- Each worktree is independent - you can switch between them without stashing
- All worktrees share the same git repository and remotes
- Commits in one worktree are immediately visible in others after push/fetch
- Use draft PRs early for visibility