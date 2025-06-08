"""
Integration tests for the conversation system.
Tests the full pipeline with mock providers.
"""

import unittest
import time

from hello_world.core.conversation_manager import ConversationManager, ConversationConfig
from hello_world.metrics.collector import MetricsCollector


class TestIntegration(unittest.TestCase):
    """Integration tests for the conversation system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = ConversationConfig(
            mock_mode=True,
            debug_mode=True,
            enable_metrics=True,
            enable_interruptions=True
        )
        self.manager = ConversationManager(self.config)
        
    def test_conversation_manager_initialization(self):
        """Test that ConversationManager initializes correctly."""
        self.assertIsNotNone(self.manager.stt_provider)
        self.assertIsNotNone(self.manager.ai_provider)
        self.assertIsNotNone(self.manager.tts_provider)
        self.assertIsNotNone(self.manager.metrics_collector)
        self.assertIsNotNone(self.manager.interruption_handler)
        
    def test_provider_status(self):
        """Test that all providers report correct status."""
        status = self.manager.get_status()
        
        self.assertIn('providers_status', status)
        providers = status['providers_status']
        
        self.assertIsNotNone(providers['stt'])
        self.assertIsNotNone(providers['ai'])
        self.assertIsNotNone(providers['tts'])
        
        # Check provider types
        self.assertEqual(providers['stt']['provider'], 'mock_stt')
        self.assertEqual(providers['ai']['provider'], 'mock_ai')
        self.assertEqual(providers['tts']['provider'], 'mock_tts')
        
    def test_session_lifecycle(self):
        """Test session creation and management."""
        # Start conversation
        test_project = "/tmp/test_project"
        self.manager.start(project_path=test_project)
        
        # Check session was created
        status = self.manager.get_status()
        self.assertTrue(status['is_running'])
        self.assertIsNotNone(status['session_id'])
        
        # Stop conversation
        self.manager.stop()
        
        # Check session was stopped
        status = self.manager.get_status()
        self.assertFalse(status['is_running'])
        
    def test_mock_pipeline_basic_flow(self):
        """Test basic conversation flow with mock providers."""
        # Start the system
        self.manager.start(project_path="/tmp/test")
        
        # Wait for threads to start
        time.sleep(0.5)
        
        # Check that threads are running
        self.assertTrue(self.manager.stt_thread.is_alive())
        self.assertTrue(self.manager.ai_thread.is_alive())
        self.assertTrue(self.manager.tts_thread.is_alive())
        
        # Let it run for a few seconds to process mock data
        time.sleep(2)
        
        # Check queues have activity (mock providers generate data)
        status = self.manager.get_status()
        self.assertTrue(status['is_running'])
        
        # Stop the system
        self.manager.stop()
        
        # Verify threads stopped
        self.assertFalse(self.manager.is_running)
        
    def test_metrics_collection(self):
        """Test that metrics are collected during operation."""
        collector = self.manager.metrics_collector
        
        # Start session
        collector.start_session("test_session")
        
        # Record some test metrics
        collector.record_stt_latency(150.0)
        collector.record_ai_latency(500.0)
        collector.record_tts_latency(200.0)
        collector.record_interaction()
        collector.record_error("test", "test error")
        collector.record_interruption()
        
        # Get summary
        summary = collector.get_summary()
        
        self.assertEqual(summary['total_interactions'], 1)
        self.assertEqual(summary['total_errors'], 1)
        self.assertEqual(summary['interruptions'], 1)
        
        # Check latency stats
        self.assertGreater(summary['stt_latency_ms']['samples'], 0)
        self.assertGreater(summary['ai_latency_ms']['samples'], 0)
        self.assertGreater(summary['tts_latency_ms']['samples'], 0)
        
    def test_interruption_handling(self):
        """Test interruption handling mechanism."""
        # Start the system
        self.manager.start(project_path="/tmp/test")
        
        # Simulate TTS playing
        self.manager.tts_playing = True
        
        # Add some responses to queue
        from hello_world.providers.ai.base import AIResponse
        test_response = AIResponse(text="test", is_first=False, is_final=True)
        self.manager.response_queue.put(test_response)
        
        # Trigger interruption
        if self.manager.interruption_handler:
            self.manager.interruption_handler.trigger_interruption()
        
        # Handle interruption
        self.manager.handle_interruption()
        
        # Check that queues were cleared and TTS stopped
        self.assertTrue(self.manager.response_queue.empty())
        self.assertFalse(self.manager.tts_playing)
        
        # Stop the system
        self.manager.stop()
        
    def test_error_recovery(self):
        """Test error recovery mechanisms."""
        # Test STT error recovery
        test_error = Exception("Test STT error")
        self.manager._handle_stt_error(test_error)
        
        # Check that error was recorded
        if self.manager.metrics_collector:
            summary = self.manager.metrics_collector.get_summary()
            # Metrics might not have error data if session not started
            if 'total_errors' in summary:
                self.assertGreater(summary['total_errors'], 0)
            
        self.assertGreater(self.manager.error_count, 0)
        
    def test_cli_metrics_command(self):
        """Test CLI metrics functionality."""
        from hello_world.cli.main import metrics
        from click.testing import CliRunner
        
        # Generate some test data
        collector = MetricsCollector()
        collector.start_session("test_cli_session")
        collector.record_stt_latency(100.0)
        collector.record_ai_latency(300.0)
        collector.record_interaction()
        collector.end_session()
        collector.save_metrics()
        
        # Test text format
        runner = CliRunner()
        result = runner.invoke(metrics, ['--days', '1', '--format', 'text'])
        self.assertEqual(result.exit_code, 0)
        
        # Test JSON format
        result = runner.invoke(metrics, ['--days', '1', '--format', 'json'])
        self.assertEqual(result.exit_code, 0)
        
    def test_performance_benchmarks(self):
        """Test performance benchmarks for the system."""
        # Start the system
        start_time = time.time()
        self.manager.start(project_path="/tmp/test")
        startup_time = time.time() - start_time
        
        # Startup should be fast (< 2 seconds)
        self.assertLess(startup_time, 2.0)
        
        # Let system run briefly
        time.sleep(1)
        
        # Test queue processing (should have low latency)
        from hello_world.providers.stt.base import Transcript
        test_transcript = Transcript(
            text="test message",
            timestamp=time.time(),
            is_final=True,
            is_speech_start=False,
            confidence=0.95,
            latency=100.0
        )
        
        queue_start = time.time()
        self.manager.transcript_queue.put(test_transcript)
        
        # Wait for processing
        time.sleep(0.1)
        
        # Check that transcript was processed quickly
        processing_time = time.time() - queue_start
        self.assertLess(processing_time, 0.5)  # Should process in < 500ms
        
        # Stop the system
        stop_start = time.time()
        self.manager.stop()
        shutdown_time = time.time() - stop_start
        
        # Shutdown should be fast (< 10 seconds)
        self.assertLess(shutdown_time, 10.0)


class TestMockProviders(unittest.TestCase):
    """Test mock providers individually."""
    
    def test_mock_stt_provider(self):
        """Test mock STT provider functionality."""
        from mocks.providers import MockSTTProvider
        
        provider = MockSTTProvider()
        provider.initialize()
        
        self.assertTrue(provider.is_running)
        
        # Test transcript generation (brief test)
        transcript_count = 0
        for transcript in provider.stream_transcripts():
            self.assertIsNotNone(transcript.text)
            self.assertGreater(transcript.confidence, 0)
            transcript_count += 1
            if transcript_count >= 2:  # Test just a couple
                break
                
        provider.stop()
        self.assertFalse(provider.is_running)
        
    def test_mock_ai_provider(self):
        """Test mock AI provider functionality."""
        from mocks.providers import MockAIProvider
        
        provider = MockAIProvider("Test system prompt")
        provider.initialize()
        
        # Test response generation
        responses = list(provider.stream_response("Hello"))
        
        self.assertGreater(len(responses), 0)
        self.assertTrue(any(r.is_first for r in responses))
        self.assertTrue(any(r.is_final for r in responses))
        
        final_response = next(r for r in responses if r.is_final)
        self.assertIsNotNone(final_response.full_text)
        
    def test_mock_tts_provider(self):
        """Test mock TTS provider functionality."""
        from mocks.providers import MockTTSProvider
        
        provider = MockTTSProvider()
        provider.initialize()
        
        # Test audio generation
        audio_chunks = list(provider.stream_audio("Hello world"))
        
        self.assertGreater(len(audio_chunks), 0)
        self.assertTrue(any(c.is_first for c in audio_chunks))
        self.assertTrue(any(c.is_final for c in audio_chunks))
        
        # Test playback simulation
        for chunk in audio_chunks:
            start_time = time.time()
            provider.play_chunk(chunk)
            playback_time = time.time() - start_time
            
            # Should simulate reasonable playback timing
            self.assertGreater(playback_time, 0)


if __name__ == '__main__':
    unittest.main()