"""Tests for TTS providers."""

import os
import time
import pytest
from unittest.mock import Mock, patch

from hello_world.providers.tts.elevenlabs import ElevenLabsProvider
from hello_world.providers.tts.base import AudioChunk
from hello_world.config.settings import Settings


class TestElevenLabsProvider:
    """Test cases for ElevenLabs TTS provider."""

    def setup_method(self):
        """Set up test fixtures."""
        self.provider = ElevenLabsProvider()

    def teardown_method(self):
        """Clean up after tests."""
        if hasattr(self.provider, "client") and self.provider.client:
            self.provider.stop()

    def test_initialization_requires_api_key(self):
        """Test that initialization requires ELEVENLABS_API_KEY."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="ELEVENLABS_API_KEY"):
                self.provider.initialize()

    @patch("hello_world.providers.tts.elevenlabs.ElevenLabs")
    @patch("hello_world.providers.tts.elevenlabs.pygame.mixer")
    def test_successful_initialization(self, mock_mixer, mock_elevenlabs):
        """Test successful provider initialization."""
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}):
            mock_mixer.get_init.return_value = (22050, -16, 2)

            self.provider.initialize()

            assert self.provider.client is not None
            mock_elevenlabs.assert_called_once_with(api_key="test-key")
            mock_mixer.pre_init.assert_called_once()
            mock_mixer.init.assert_called_once()

    @patch("hello_world.providers.tts.elevenlabs.ElevenLabs")
    def test_stream_audio_requires_initialization(self, mock_elevenlabs):
        """Test that stream_audio requires initialization."""
        with pytest.raises(RuntimeError, match="not initialized"):
            list(self.provider.stream_audio("Hello world"))

    @patch("hello_world.providers.tts.elevenlabs.ElevenLabs")
    @patch("hello_world.providers.tts.elevenlabs.pygame.mixer")
    def test_stream_audio_generates_chunks(self, mock_mixer, mock_elevenlabs):
        """Test audio streaming generates proper chunks."""
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}):
            # Setup mocks
            mock_response = [b"chunk1", b"chunk2", b"chunk3"]
            mock_client = Mock()
            mock_client.text_to_speech.convert.return_value = mock_response
            mock_elevenlabs.return_value = mock_client
            mock_mixer.get_init.return_value = (22050, -16, 2)

            # Initialize and test
            self.provider.initialize()
            chunks = list(self.provider.stream_audio("Hello world"))

            # Verify chunks
            assert len(chunks) == 4  # 3 data chunks + 1 final chunk

            # First chunk should be marked as first
            assert chunks[0].is_first is True
            assert chunks[0].is_final is False
            assert chunks[0].data == b"chunk1"

            # Middle chunks
            assert chunks[1].is_first is False
            assert chunks[1].is_final is False
            assert chunks[1].data == b"chunk2"

            # Final chunk should be marked as final
            assert chunks[-1].is_final is True
            assert chunks[-1].data == b""

    @patch("hello_world.providers.tts.elevenlabs.ElevenLabs")
    @patch("hello_world.providers.tts.elevenlabs.pygame.mixer")
    def test_interruption_stops_streaming(self, mock_mixer, mock_elevenlabs):
        """Test that setting should_stop interrupts streaming."""
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}):
            # Setup mocks with long response
            mock_response = [b"chunk1", b"chunk2", b"chunk3", b"chunk4", b"chunk5"]
            mock_client = Mock()
            mock_client.text_to_speech.convert.return_value = mock_response
            mock_elevenlabs.return_value = mock_client
            mock_mixer.get_init.return_value = (22050, -16, 2)

            # Initialize
            self.provider.initialize()

            # Start streaming and interrupt after first chunk
            chunks = []
            stream = self.provider.stream_audio("Hello world")

            # Get first chunk
            chunk = next(stream)
            chunks.append(chunk)

            # Interrupt
            self.provider.should_stop = True

            # Try to get more chunks - should stop
            try:
                while True:
                    chunk = next(stream)
                    chunks.append(chunk)
            except StopIteration:
                pass

            # Should have stopped early
            assert len(chunks) < len(mock_response) + 1

    def test_play_chunk_handles_empty_data(self):
        """Test that play_chunk handles chunks with no data."""
        chunk = AudioChunk(data=b"", is_first=False, is_final=False)

        # Should not raise exception
        self.provider.play_chunk(chunk)

    @patch("hello_world.providers.tts.elevenlabs.pygame.mixer")
    def test_stop_playback_clears_queue(self, mock_mixer):
        """Test that stop_playback clears the audio queue."""
        # Add some items to queue
        chunk1 = AudioChunk(data=b"test1", is_first=True)
        chunk2 = AudioChunk(data=b"test2", is_first=False)

        self.provider.audio_queue.put(chunk1)
        self.provider.audio_queue.put(chunk2)
        self.provider.is_playing = True

        # Stop playback
        self.provider.stop_playback()

        # Queue should be empty
        assert self.provider.audio_queue.empty()
        assert not self.provider.is_playing
        mock_mixer.music.stop.assert_called_once()

    def test_get_status_returns_proper_info(self):
        """Test that get_status returns comprehensive status."""
        status = self.provider.get_status()

        expected_keys = [
            "provider",
            "voice_id",
            "model_id",
            "is_playing",
            "should_stop",
            "queue_size",
            "playback_thread_alive",
            "initialized",
            "mixer_initialized",
        ]

        for key in expected_keys:
            assert key in status

        assert status["provider"] == "elevenlabs"
        assert status["voice_id"] == "pNInz6obpgDQGcFmaJgB"
        assert status["model_id"] == "eleven_flash_v2_5"


class TestTTSIntegration:
    """Integration tests for TTS functionality."""

    @pytest.mark.integration
    @patch("hello_world.providers.tts.elevenlabs.pygame.mixer")
    def test_full_tts_pipeline_short_text(self, mock_mixer):
        """Test complete TTS pipeline with short text."""
        if not os.getenv("ELEVENLABS_API_KEY"):
            pytest.skip("ELEVENLABS_API_KEY not set")

        mock_mixer.get_init.return_value = (22050, -16, 2)

        provider = ElevenLabsProvider()

        try:
            provider.initialize()

            # Test short text
            text = "Hello, this is a test."
            chunks = list(provider.stream_audio(text))

            assert len(chunks) > 0
            assert any(chunk.is_first for chunk in chunks)
            assert any(chunk.is_final for chunk in chunks)

            # Test playback
            for chunk in chunks:
                provider.play_chunk(chunk)

            # Wait a bit for processing
            time.sleep(0.1)

        finally:
            provider.stop()

    @pytest.mark.integration
    @patch("hello_world.providers.tts.elevenlabs.pygame.mixer")
    def test_full_tts_pipeline_long_text(self, mock_mixer):
        """Test complete TTS pipeline with longer text."""
        if not os.getenv("ELEVENLABS_API_KEY"):
            pytest.skip("ELEVENLABS_API_KEY not set")

        mock_mixer.get_init.return_value = (22050, -16, 2)

        provider = ElevenLabsProvider()

        try:
            provider.initialize()

            # Test longer text
            text = """
            This is a much longer text that should be converted to speech.
            It contains multiple sentences and should test the streaming
            capabilities of the TTS provider. The system should handle
            this text efficiently and provide smooth audio output without
            any interruptions or artifacts.
            """

            chunks = list(provider.stream_audio(text))

            assert len(chunks) > 1  # Should have multiple chunks
            assert any(chunk.is_first for chunk in chunks)
            assert any(chunk.is_final for chunk in chunks)

            # Test playback
            for chunk in chunks:
                provider.play_chunk(chunk)

            # Wait a bit for processing
            time.sleep(0.5)

        finally:
            provider.stop()

    @pytest.mark.integration
    @patch("hello_world.providers.tts.elevenlabs.pygame.mixer")
    def test_interruption_handling(self, mock_mixer):
        """Test that interruption works during TTS generation."""
        if not os.getenv("ELEVENLABS_API_KEY"):
            pytest.skip("ELEVENLABS_API_KEY not set")

        mock_mixer.get_init.return_value = (22050, -16, 2)

        provider = ElevenLabsProvider()

        try:
            provider.initialize()

            # Start TTS with long text
            text = "This is a very long text " * 50  # Repeat to make it long
            stream = provider.stream_audio(text)

            # Get first chunk
            chunk = next(stream)
            assert chunk.is_first

            # Interrupt
            provider.should_stop = True

            # Continue streaming - should stop early
            remaining_chunks = list(stream)

            # Should have stopped before completing all text
            total_chunks = 1 + len(remaining_chunks)
            assert total_chunks < 100  # Arbitrary large number

        finally:
            provider.stop()


class TestSettings:
    """Test TTS-related settings."""

    def test_elevenlabs_config_includes_voice_settings(self):
        """Test that ElevenLabs config includes voice settings."""
        settings = Settings()
        config = settings.get_provider_config("elevenlabs")

        expected_keys = [
            "voice_id",
            "model_id",
            "output_format",
            "stability",
            "similarity_boost",
            "style",
            "speed",
            "use_speaker_boost",
        ]

        for key in expected_keys:
            assert key in config

    def test_voice_settings_from_config(self):
        """Test creating provider with settings from config."""
        settings = Settings()
        config = settings.get_provider_config("elevenlabs")

        provider = ElevenLabsProvider(
            voice_id=config["voice_id"],
            model_id=config["model_id"],
            output_format=config["output_format"],
            stability=config["stability"],
            similarity_boost=config["similarity_boost"],
            style=config["style"],
            speed=config["speed"],
            use_speaker_boost=config["use_speaker_boost"],
        )

        assert provider.voice_id == config["voice_id"]
        assert provider.voice_settings.stability == config["stability"]
        assert provider.voice_settings.similarity_boost == config["similarity_boost"]
