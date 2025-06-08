# Team 2: AI Provider Implementation

## Objective
Implement both Claude and Gemini AI providers with streaming support for the conversation system.

## Key Tasks

1. **Claude Provider** (`hello_world/providers/ai/claude.py`)
   - Replace pseudocode with subprocess implementation
   - Use command: `claude --output-format stream-json`
   - Add system prompt: "You are a breezy but focused senior developer who gets straight to the point without getting stuck in the weeds. Be conversational but efficient."
   - Parse streaming JSON output
   - Handle conversation context management
   - Implement proper subprocess lifecycle

2. **Gemini Provider** (`hello_world/providers/ai/gemini.py`)
   - Replace pseudocode with actual API calls
   - Use google-generativeai library
   - Implement streaming responses
   - Set system prompt in initial message
   - Handle API errors gracefully

3. **Common Features**
   - Streaming response handling with queues
   - Context management (last N messages)
   - Token counting and limits
   - Response timeout (30 seconds)
   - Retry logic with exponential backoff
   - Interruption support (clear queues)

4. **Testing & Mocking**
   - Create mock responses for testing
   - Test streaming functionality
   - Verify context management
   - Test error scenarios

## Technical Specifications
- Use asyncio for Gemini API calls
- Thread-safe queue for streaming tokens
- Implement timeout and cancellation
- Proper resource cleanup

## Configuration
Environment variables:
- `AI_PROVIDER`: claude or gemini
- `GOOGLE_API_KEY`: For Gemini
- Claude uses pre-authenticated SDK

## Success Criteria
- Both providers working with streaming
- Response latency < 500ms to first token
- Proper context management
- Graceful error handling
- Seamless provider switching

## Files to Modify
- `hello_world/providers/ai/claude.py` - Claude implementation
- `hello_world/providers/ai/gemini.py` - Gemini implementation
- `hello_world/providers/ai/base.py` - Update interface if needed
- Create tests in `hello_world/tests/test_ai_providers.py`

## Implementation Notes
- Claude: Focus on subprocess management and JSON parsing
- Gemini: Focus on async streaming and API integration
- Both: Ensure consistent interface for ConversationManager