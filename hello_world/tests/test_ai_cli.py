"""Tests for the AI CLI subcommand."""

import json
import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner

from ..cli.ai import ai
from ..providers.ai.base import AIResponse


class TestAICLI:
    """Test cases for AI CLI subcommand."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        
    @pytest.fixture
    def mock_claude_provider(self):
        """Mock Claude provider."""
        provider = Mock()
        provider.conversation_history = []
        provider.initialize.return_value = None
        provider.stop.return_value = None
        return provider
    
    @pytest.fixture
    def mock_gemini_provider(self):
        """Mock Gemini provider."""
        provider = Mock()
        provider.conversation_history = []
        provider.initialize.return_value = None
        provider.stop.return_value = None
        return provider
    
    def test_basic_text_input(self, mock_claude_provider):
        """Test basic text input with Claude provider."""
        # Mock streaming response
        mock_claude_provider.stream_response.return_value = [
            AIResponse(text="Hello", is_first=True, is_final=False),
            AIResponse(text=" there!", is_first=False, is_final=False),
            AIResponse(text="", is_first=False, is_final=True, full_text="Hello there!")
        ]
        
        with patch('hello_world.cli.ai.ClaudeProvider', return_value=mock_claude_provider):
            result = self.runner.invoke(ai, ['--input', 'Hello'])
            
        assert result.exit_code == 0
        assert "Hello there!" in result.output
        mock_claude_provider.initialize.assert_called_once()
        mock_claude_provider.stream_response.assert_called_once_with('Hello')
        mock_claude_provider.stop.assert_called_once()
    
    def test_gemini_provider(self, mock_gemini_provider):
        """Test using Gemini provider."""
        mock_gemini_provider.stream_response.return_value = [
            AIResponse(text="Gemini response", is_first=True, is_final=True, full_text="Gemini response")
        ]
        
        with patch('hello_world.cli.ai.GeminiProvider', return_value=mock_gemini_provider):
            result = self.runner.invoke(ai, ['--input', 'Test', '--provider', 'gemini'])
            
        assert result.exit_code == 0
        assert "Gemini response" in result.output
        mock_gemini_provider.initialize.assert_called_once()
        mock_gemini_provider.stream_response.assert_called_once_with('Test')
    
    def test_stdin_input(self, mock_claude_provider):
        """Test reading input from stdin."""
        mock_claude_provider.stream_response.return_value = [
            AIResponse(text="Response from stdin", is_first=True, is_final=True, full_text="Response from stdin")
        ]
        
        with patch('hello_world.cli.ai.ClaudeProvider', return_value=mock_claude_provider):
            result = self.runner.invoke(ai, input='Hello from stdin')
            
        assert result.exit_code == 0
        assert "Response from stdin" in result.output
        mock_claude_provider.stream_response.assert_called_once_with('Hello from stdin')
    
    def test_json_output(self, mock_claude_provider):
        """Test JSON output format."""
        mock_claude_provider.stream_response.return_value = [
            AIResponse(
                text="JSON test response", 
                is_first=True, 
                is_final=True, 
                full_text="JSON test response",
                metadata={"tokens": 4}
            )
        ]
        mock_claude_provider.conversation_history = [
            {"role": "user", "content": "test"},
            {"role": "assistant", "content": "JSON test response"}
        ]
        
        with patch('hello_world.cli.ai.ClaudeProvider', return_value=mock_claude_provider):
            result = self.runner.invoke(ai, ['--input', 'test', '--json'])
            
        assert result.exit_code == 0
        
        # Parse JSON output
        output_data = json.loads(result.output)
        assert output_data['response'] == "JSON test response"
        assert output_data['provider'] == "claude"
        assert output_data['input'] == "test"
        assert 'conversation_history' in output_data
    
    def test_metrics_output(self, mock_claude_provider):
        """Test metrics output."""
        mock_claude_provider.stream_response.return_value = [
            AIResponse(text="Metrics test", is_first=True, is_final=True, full_text="Metrics test")
        ]
        
        with patch('hello_world.cli.ai.ClaudeProvider', return_value=mock_claude_provider):
            result = self.runner.invoke(ai, ['--input', 'test', '--metrics'])
            
        assert result.exit_code == 0
        assert "--- Metrics ---" in result.output
        assert "Total latency:" in result.output
        assert "First token latency:" in result.output
    
    def test_conversation_context(self, mock_claude_provider, tmp_path):
        """Test loading conversation context from file."""
        # Create context file
        context_data = {
            "history": [
                {"role": "user", "content": "Previous question"},
                {"role": "assistant", "content": "Previous answer"}
            ]
        }
        context_file = tmp_path / "context.json"
        context_file.write_text(json.dumps(context_data))
        
        mock_claude_provider.stream_response.return_value = [
            AIResponse(text="Context response", is_first=True, is_final=True, full_text="Context response")
        ]
        
        with patch('hello_world.cli.ai.ClaudeProvider', return_value=mock_claude_provider):
            result = self.runner.invoke(ai, ['--input', 'Continue', '--context', str(context_file)])
            
        assert result.exit_code == 0
        # Verify context was loaded into provider
        assert mock_claude_provider.conversation_history == context_data["history"]
    
    def test_custom_system_prompt(self, mock_claude_provider):
        """Test custom system prompt."""
        mock_claude_provider.stream_response.return_value = [
            AIResponse(text="Custom system response", is_first=True, is_final=True, full_text="Custom system response")
        ]
        
        with patch('hello_world.cli.ai.ClaudeProvider') as mock_class:
            mock_class.return_value = mock_claude_provider
            result = self.runner.invoke(ai, [
                '--input', 'test', 
                '--system', 'You are a specialized assistant.'
            ])
            
        assert result.exit_code == 0
        # Verify system prompt was passed to provider
        mock_class.assert_called_once_with(
            system_prompt='You are a specialized assistant.',
            streaming=True
        )
    
    def test_no_streaming(self, mock_claude_provider):
        """Test non-streaming mode."""
        mock_claude_provider.stream_response.return_value = [
            AIResponse(text="Full response", is_first=True, is_final=True, full_text="Full response")
        ]
        
        with patch('hello_world.cli.ai.ClaudeProvider') as mock_class:
            mock_class.return_value = mock_claude_provider
            result = self.runner.invoke(ai, ['--input', 'test', '--no-streaming'])
            
        assert result.exit_code == 0
        # Verify streaming was disabled
        mock_class.assert_called_once_with(
            system_prompt='You are a helpful AI assistant.',
            streaming=False
        )
    
    def test_provider_initialization_error(self):
        """Test handling of provider initialization errors."""
        with patch('hello_world.cli.ai.ClaudeProvider') as mock_class:
            mock_provider = Mock()
            mock_provider.initialize.side_effect = Exception("Initialization failed")
            mock_class.return_value = mock_provider
            
            result = self.runner.invoke(ai, ['--input', 'test'])
            
        assert result.exit_code == 1
        assert "Error initializing claude" in result.output
    
    def test_streaming_error(self, mock_claude_provider):
        """Test handling of streaming errors."""
        mock_claude_provider.stream_response.side_effect = Exception("Streaming failed")
        
        with patch('hello_world.cli.ai.ClaudeProvider', return_value=mock_claude_provider):
            result = self.runner.invoke(ai, ['--input', 'test'])
            
        assert result.exit_code == 1
        assert "Error:" in result.output
        mock_claude_provider.stop.assert_called_once()
    
    def test_invalid_context_file(self):
        """Test handling of invalid context file."""
        result = self.runner.invoke(ai, ['--input', 'test', '--context', 'nonexistent.json'])
        
        assert result.exit_code == 2  # Click file not found error
    
    def test_empty_stdin(self):
        """Test handling of empty stdin input."""
        result = self.runner.invoke(ai, input='')
        
        assert result.exit_code == 1
        assert "No input provided" in result.output
    
    def test_model_parameter(self, mock_gemini_provider):
        """Test model parameter for Gemini provider."""
        mock_gemini_provider.stream_response.return_value = [
            AIResponse(text="Model test", is_first=True, is_final=True, full_text="Model test")
        ]
        
        with patch('hello_world.cli.ai.GeminiProvider') as mock_class:
            mock_class.return_value = mock_gemini_provider
            result = self.runner.invoke(ai, [
                '--input', 'test', 
                '--provider', 'gemini',
                '--model', 'gemini-pro-1.5'
            ])
            
        assert result.exit_code == 0
        # Verify model was passed to Gemini provider
        mock_class.assert_called_once_with(
            system_prompt='You are a helpful AI assistant.',
            streaming=True,
            model_name='gemini-pro-1.5'
        )