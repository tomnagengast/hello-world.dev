"""Tests for WhisperKit file-based STT provider."""

import unittest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from hello_world.providers.stt.whisperkit_file import WhisperKitFileProvider
from hello_world.providers.stt.base import Transcript


class TestWhisperKitFileProvider(unittest.TestCase):
    """Test the file-based WhisperKit provider."""
    
    def setUp(self):
        self.provider = WhisperKitFileProvider(
            model="large-v3_turbo",
            whisperkit_path="/usr/bin/whisperkit-cli",  # Mock path for testing
            verbose=False
        )
    
    def test_initialization(self):
        """Test provider initialization parameters."""
        self.assertEqual(self.provider.model, "large-v3_turbo")
        self.assertEqual(self.provider.whisperkit_path, "/usr/bin/whisperkit-cli")
        self.assertFalse(self.provider.verbose)
        self.assertFalse(self.provider.is_initialized)
        self.assertIsNone(self.provider.current_file)
    
    @patch('subprocess.run')
    def test_initialize_success(self, mock_run):
        """Test successful initialization."""
        # Mock successful whisperkit-cli check
        mock_run.return_value = Mock(returncode=0)
        
        self.provider.initialize()
        
        self.assertTrue(self.provider.is_initialized)
        mock_run.assert_called_once_with(
            ["/usr/bin/whisperkit-cli", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
    
    @patch('subprocess.run')
    def test_initialize_cli_not_found(self, mock_run):
        """Test initialization failure when WhisperKit CLI not found."""
        mock_run.side_effect = FileNotFoundError("Command not found")
        
        with self.assertRaises(RuntimeError) as context:
            self.provider.initialize()
        
        self.assertIn("WhisperKit CLI not found", str(context.exception))
        self.assertFalse(self.provider.is_initialized)
    
    @patch('subprocess.run')
    def test_initialize_cli_not_working(self, mock_run):
        """Test initialization failure when WhisperKit CLI returns error."""
        mock_run.return_value = Mock(returncode=1, stderr="Error message")
        
        with self.assertRaises(RuntimeError) as context:
            self.provider.initialize()
        
        self.assertIn("WhisperKit CLI not working", str(context.exception))
        self.assertFalse(self.provider.is_initialized)
    
    def test_process_file_not_initialized(self):
        """Test that processing file fails when not initialized."""
        with tempfile.NamedTemporaryFile(suffix=".wav") as temp_file:
            temp_path = Path(temp_file.name)
            
            with self.assertRaises(RuntimeError) as context:
                list(self.provider.process_file(temp_path))
            
            self.assertIn("Provider not initialized", str(context.exception))
    
    def test_process_file_not_found(self):
        """Test processing non-existent file."""
        self.provider.is_initialized = True
        non_existent_file = Path("/path/that/does/not/exist.wav")
        
        with self.assertRaises(FileNotFoundError) as context:
            list(self.provider.process_file(non_existent_file))
        
        self.assertIn("Audio file not found", str(context.exception))
    
    @patch('subprocess.Popen')
    def test_process_file_success(self, mock_popen):
        """Test successful file processing."""
        self.provider.is_initialized = True
        
        # Create a temporary audio file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")
        
        try:
            # Mock subprocess
            mock_process = Mock()
            mock_process.stdout.readline.side_effect = [
                "Hello world\n",
                ""  # End of output
            ]
            mock_process.poll.return_value = 0  # Process completed
            mock_process.wait.return_value = 0  # Success
            mock_process.stderr.read.return_value = ""
            mock_popen.return_value = mock_process
            
            # Process file
            transcripts = list(self.provider.process_file(temp_path))
            
            # Verify results
            self.assertEqual(len(transcripts), 1)
            transcript = transcripts[0]
            self.assertIsInstance(transcript, Transcript)
            self.assertEqual(transcript.text, "Hello world")
            self.assertTrue(transcript.is_final)
            self.assertTrue(transcript.is_speech_start)
            self.assertIsNotNone(transcript.latency)
            
            # Verify subprocess was called correctly
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args[0][0]
            self.assertIn("/usr/bin/whisperkit-cli", call_args)
            self.assertIn("transcribe", call_args)
            self.assertIn("--model", call_args)
            self.assertIn("large-v3_turbo", call_args)
            self.assertIn(str(temp_path), call_args)
            
        finally:
            # Cleanup
            temp_path.unlink(missing_ok=True)
    
    @patch('subprocess.Popen')
    def test_process_file_whisperkit_failure(self, mock_popen):
        """Test handling of WhisperKit process failure."""
        self.provider.is_initialized = True
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Mock failing subprocess
            mock_process = Mock()
            mock_process.stdout.readline.return_value = ""
            mock_process.poll.return_value = 1  # Process failed
            mock_process.wait.return_value = 1
            mock_process.stderr.read.return_value = "WhisperKit error"
            mock_popen.return_value = mock_process
            
            with self.assertRaises(RuntimeError) as context:
                list(self.provider.process_file(temp_path))
            
            self.assertIn("WhisperKit failed with code 1", str(context.exception))
            
        finally:
            temp_path.unlink(missing_ok=True)
    
    def test_stream_transcripts_not_implemented(self):
        """Test that stream_transcripts raises NotImplementedError."""
        with self.assertRaises(NotImplementedError) as context:
            list(self.provider.stream_transcripts())
        
        self.assertIn("file processing only", str(context.exception))
    
    @patch('subprocess.Popen')
    def test_stop_cleanup(self, mock_popen):
        """Test proper cleanup on stop."""
        # Setup mock process
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process running
        self.provider.process = mock_process
        
        # Stop provider
        self.provider.stop()
        
        # Verify cleanup
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)
        self.assertIsNone(self.provider.process)
        self.assertIsNone(self.provider.current_file)
    
    def test_get_status(self):
        """Test status reporting."""
        status = self.provider.get_status()
        
        expected_keys = [
            'provider', 'model', 'is_initialized', 'current_file',
            'process_running', 'compute_units', 'whisperkit_path',
            'last_processing_time_ms'
        ]
        
        for key in expected_keys:
            self.assertIn(key, status)
        
        self.assertEqual(status['provider'], 'whisperkit_file')
        self.assertEqual(status['model'], 'large-v3_turbo')
        self.assertFalse(status['is_initialized'])
        self.assertIsNone(status['current_file'])
    
    def test_supported_formats(self):
        """Test supported formats listing."""
        formats = WhisperKitFileProvider.supported_formats()
        
        expected_formats = [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"]
        self.assertEqual(set(formats), set(expected_formats))
    
    def test_is_format_supported(self):
        """Test format support checking."""
        # Supported formats
        self.assertTrue(self.provider.is_format_supported(Path("test.mp3")))
        self.assertTrue(self.provider.is_format_supported(Path("test.wav")))
        self.assertTrue(self.provider.is_format_supported(Path("test.m4a")))
        self.assertTrue(self.provider.is_format_supported(Path("TEST.MP3")))  # Case insensitive
        
        # Unsupported formats
        self.assertFalse(self.provider.is_format_supported(Path("test.txt")))
        self.assertFalse(self.provider.is_format_supported(Path("test.mp4")))
        self.assertFalse(self.provider.is_format_supported(Path("test")))  # No extension
    
    @patch('subprocess.Popen')
    def test_verbose_mode(self, mock_popen):
        """Test verbose mode adds --verbose flag."""
        verbose_provider = WhisperKitFileProvider(verbose=True)
        verbose_provider.is_initialized = True
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Mock subprocess
            mock_process = Mock()
            mock_process.stdout.readline.side_effect = ["", ""]
            mock_process.poll.return_value = 0
            mock_process.wait.return_value = 0
            mock_process.stderr.read.return_value = ""
            mock_popen.return_value = mock_process
            
            list(verbose_provider.process_file(temp_path))
            
            # Verify --verbose flag is included
            call_args = mock_popen.call_args[0][0]
            self.assertIn("--verbose", call_args)
            
        finally:
            temp_path.unlink(missing_ok=True)


if __name__ == '__main__':
    unittest.main()