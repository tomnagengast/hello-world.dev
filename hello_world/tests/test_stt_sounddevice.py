"""Tests for sounddevice-based WhisperKit STT provider."""

import unittest
import time
import numpy as np
from unittest.mock import Mock, patch

from hello_world.providers.stt.whisperkit import WhisperKitProvider, RingBuffer
from hello_world.utils.interruption_handler import InterruptionHandler


class TestRingBuffer(unittest.TestCase):
    """Test the ring buffer implementation."""

    def setUp(self):
        self.buffer = RingBuffer(1000)

    def test_write_read_basic(self):
        """Test basic write and read operations."""
        data = np.array([1, 2, 3, 4, 5], dtype=np.float32)
        written = self.buffer.write(data)
        self.assertEqual(written, 5)

        read_data = self.buffer.read(5)
        np.testing.assert_array_equal(read_data, data)

    def test_available_read(self):
        """Test available read count."""
        self.assertEqual(self.buffer.available_read(), 0)

        data = np.array([1, 2, 3], dtype=np.float32)
        self.buffer.write(data)
        self.assertEqual(self.buffer.available_read(), 3)

        self.buffer.read(2)
        self.assertEqual(self.buffer.available_read(), 1)

    def test_wraparound(self):
        """Test buffer wraparound functionality."""
        # Fill buffer almost completely
        large_data = np.ones(990, dtype=np.float32)
        self.buffer.write(large_data)

        # Read some data to create space at beginning
        self.buffer.read(100)

        # Write more data that should wrap around
        wrap_data = np.array([2, 3, 4, 5, 6], dtype=np.float32)
        written = self.buffer.write(wrap_data)
        self.assertEqual(written, 5)

        # Read remaining original data
        remaining = self.buffer.read(890)
        self.assertEqual(len(remaining), 890)

        # Read wrapped data
        wrapped = self.buffer.read(5)
        np.testing.assert_array_equal(wrapped, wrap_data)


class TestInterruptionHandler(unittest.TestCase):
    """Test the advanced VAD interruption handler."""

    def setUp(self):
        self.handler = InterruptionHandler(
            sample_rate=16000, frame_duration_ms=30, vad_aggressiveness=3
        )

    def test_initialization(self):
        """Test proper initialization."""
        self.assertEqual(self.handler.sample_rate, 16000)
        self.assertEqual(self.handler.frame_duration_ms, 30)
        self.assertEqual(self.handler.frame_size, 480)  # 16000 * 30 / 1000
        self.assertIsNotNone(self.handler.vad)

    def test_silence_detection(self):
        """Test silence detection."""
        self.assertTrue(self.handler.is_silence())

        # Simulate voice activity
        self.handler.last_voice_time = time.time()
        self.assertFalse(self.handler.is_silence())

        # Wait for silence timeout (simulate)
        self.handler.last_voice_time = time.time() - 1.0  # 1 second ago
        self.assertTrue(self.handler.is_silence())

    @patch("webrtcvad.Vad")
    def test_audio_frame_processing(self, mock_vad_class):
        """Test audio frame processing."""
        mock_vad = Mock()
        mock_vad.is_speech.return_value = True
        mock_vad_class.return_value = mock_vad

        handler = InterruptionHandler()

        # Create test audio frame
        audio_frame = np.random.random(480).astype(np.float32) * 0.1

        # Process frame
        handler.process_audio_frame(audio_frame)

        # Should call VAD
        mock_vad.is_speech.assert_called()

    def test_voice_activity_stats(self):
        """Test voice activity statistics."""
        stats = self.handler.get_voice_activity_stats()

        expected_keys = [
            "is_voice_active",
            "last_voice_time",
            "silence_duration_ms",
            "is_silence",
            "noise_floor",
            "dynamic_threshold",
            "recent_voice_ratio",
        ]

        for key in expected_keys:
            self.assertIn(key, stats)


class TestWhisperKitProvider(unittest.TestCase):
    """Test the sounddevice-based WhisperKit provider."""

    def setUp(self):
        self.provider = WhisperKitProvider(
            model="large-v3_turbo",
            sample_rate=16000,
            block_duration=0.1,
            buffer_duration=2.0,
        )

    def test_initialization_parameters(self):
        """Test proper initialization of parameters."""
        self.assertEqual(self.provider.model, "large-v3_turbo")
        self.assertEqual(self.provider.sample_rate, 16000)
        self.assertEqual(self.provider.block_duration, 0.1)
        self.assertEqual(self.provider.buffer_duration, 2.0)

        # Check calculated values
        self.assertEqual(self.provider.block_size, 1600)  # 16000 * 0.1
        self.assertEqual(self.provider.buffer_size, 32000)  # 16000 * 2.0

    def test_audio_callback(self):
        """Test audio callback processing."""
        # Create mock audio data
        frames = 1600
        indata = np.random.random((frames, 1)).astype(np.float32)

        # Mock the ring buffer
        self.provider.ring_buffer = Mock()
        self.provider.ring_buffer.write.return_value = frames

        # Mock interruption handler
        self.provider.interruption_handler = Mock()
        self.provider.interruption_handler.frame_size = 480
        self.provider.interruption_handler.process_audio_frame.return_value = False

        # Process callback
        self.provider.audio_callback(indata, frames, None, None)

        # Verify ring buffer was called
        self.provider.ring_buffer.write.assert_called_once()

        # Verify audio was queued
        self.assertGreater(self.provider.audio_queue.qsize(), 0)

    @patch("sounddevice.query_devices")
    @patch("sounddevice.InputStream")
    @patch("subprocess.Popen")
    def test_initialize_success(self, mock_popen, mock_stream, mock_query):
        """Test successful initialization."""
        # Mock audio device query
        mock_query.return_value = [{"name": "Test Device", "default_samplerate": 44100}]

        # Mock audio stream
        mock_stream_instance = Mock()
        mock_stream_instance.latency = 0.1
        mock_stream.return_value = mock_stream_instance

        # Mock subprocess
        mock_process = Mock()
        mock_popen.return_value = mock_process

        # Initialize
        self.provider.initialize()

        # Verify components were created
        mock_stream.assert_called_once()
        mock_popen.assert_called_once()
        self.assertTrue(self.provider.is_running)
        self.assertTrue(self.provider.is_recording)

    def test_get_status(self):
        """Test status reporting."""
        status = self.provider.get_status()

        expected_keys = [
            "provider",
            "model",
            "is_running",
            "is_recording",
            "process_alive",
            "audio_stream_active",
            "vad_enabled",
            "compute_units",
            "sample_rate",
            "block_duration",
            "buffer_duration",
            "audio_callback_count",
            "ring_buffer_available",
            "audio_queue_size",
            "vad_stats",
            "last_audio_time",
            "processing_latency_ms",
        ]

        for key in expected_keys:
            self.assertIn(key, status)

        self.assertEqual(status["provider"], "whisperkit")
        self.assertEqual(status["model"], "large-v3_turbo")

    @patch("subprocess.Popen")
    def test_stop_cleanup(self, mock_popen):
        """Test proper cleanup on stop."""
        # Setup mock process
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        # Setup mock audio stream
        self.provider.audio_stream = Mock()
        self.provider.process = mock_process
        self.provider.is_running = True
        self.provider.is_recording = True

        # Stop provider
        self.provider.stop()

        # Verify cleanup
        self.assertFalse(self.provider.is_running)
        self.assertFalse(self.provider.is_recording)
        if self.provider.audio_stream:
            self.provider.audio_stream.stop.assert_called_once()
            self.provider.audio_stream.close.assert_called_once()
        mock_process.terminate.assert_called_once()


class TestPerformanceCharacteristics(unittest.TestCase):
    """Test performance characteristics of the implementation."""

    def test_ring_buffer_performance(self):
        """Test ring buffer performance under load."""
        buffer = RingBuffer(10000)

        start_time = time.time()

        # Simulate high-frequency writes
        for _ in range(1000):
            data = np.random.random(100).astype(np.float32)
            buffer.write(data)
            buffer.read(50)  # Read half back

        end_time = time.time()
        duration = end_time - start_time

        # Should complete in reasonable time (< 100ms for 1000 operations)
        self.assertLess(duration, 0.1)

    def test_vad_processing_speed(self):
        """Test VAD processing speed."""
        handler = InterruptionHandler()

        # Generate test frames
        frames = []
        for _ in range(100):
            frame = np.random.random(480).astype(np.float32) * 0.1
            frames.append(frame)

        start_time = time.time()

        # Process frames
        for frame in frames:
            try:
                handler.process_audio_frame(frame)
            except Exception:
                # VAD might fail without proper audio, that's OK for performance test
                pass

        end_time = time.time()
        duration = end_time - start_time

        # Should process 100 frames quickly (< 50ms)
        self.assertLess(duration, 0.05)


if __name__ == "__main__":
    unittest.main()
