"""Tests for state management and metrics collection."""

import pytest
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import patch

from hello_world.state.session_manager import SessionManager
from hello_world.metrics.collector import MetricsCollector
from hello_world.config.settings import Settings
from hello_world.utils.logging import setup_logging, JsonFormatter


class TestSessionManager:
    """Test session management functionality."""

    def test_session_creation(self):
        """Test basic session creation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = SessionManager(tmp_dir)
            session = manager.create_session("/test/project")

            assert session.id.startswith("session_")
            assert session.conversation_id.startswith("conv_")
            assert session.project_path == "/test/project"
            assert len(session.messages) == 0

    def test_session_without_project(self):
        """Test session creation without project path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = SessionManager(tmp_dir)
            session = manager.create_session()

            assert session.project_path is None
            assert session.id.startswith("session_")

    def test_session_save_load(self):
        """Test saving and loading sessions."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = SessionManager(tmp_dir)

            # Create and modify session
            session = manager.create_session("/test/project")
            session.add_user_message("Hello")
            session.add_ai_message("Hi there!")

            # Save session
            manager.save_session(session)

            # Load session
            loaded_session = manager.load_session(session.id, "/test/project")

            assert loaded_session is not None
            assert loaded_session.id == session.id
            assert loaded_session.conversation_id == session.conversation_id
            assert len(loaded_session.messages) == 2
            assert loaded_session.messages[0]["content"] == "Hello"
            assert loaded_session.messages[1]["content"] == "Hi there!"

    def test_session_save_without_project(self):
        """Test that sessions without project path are not saved."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = SessionManager(tmp_dir)
            session = manager.create_session()  # No project path

            # Should not raise but should log warning
            manager.save_session(session)

    def test_list_conversations(self):
        """Test listing conversations for a project."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = SessionManager(tmp_dir)

            # Create multiple sessions
            session1 = manager.create_session("/test/project")
            session2 = manager.create_session("/test/project")

            # Save sessions
            manager.save_session(session1)
            manager.save_session(session2)

            # List conversations
            conversations = manager.list_conversations("/test/project")

            assert len(conversations) >= 1  # At least one conversation
            for conv in conversations:
                assert "id" in conv
                assert "created_at" in conv
                assert "session_count" in conv

    def test_project_hash_consistency(self):
        """Test that project hash is consistent."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = SessionManager(tmp_dir)

            hash1 = manager._get_project_hash("/test/project")
            hash2 = manager._get_project_hash("/test/project")

            assert hash1 == hash2
            assert len(hash1) == 16  # Should be 16 chars as specified


class TestMetricsCollector:
    """Test metrics collection functionality."""

    def test_latency_metric_recording(self):
        """Test recording latency metrics."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            collector = MetricsCollector(tmp_dir)

            # Start a session
            collector.start_session("test_session")

            # Record STT latency
            collector.record_stt_latency(500.0)

            # Get summary
            summary = collector.get_summary()

            assert summary["stt_latency_ms"]["samples"] == 1
            assert summary["stt_latency_ms"]["avg"] == 500.0

    def test_ai_latency_recording(self):
        """Test recording AI response latency."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            collector = MetricsCollector(tmp_dir)

            # Start a session
            collector.start_session("test_session")

            # Simulate AI response timing
            start_time = time.time()
            time.sleep(0.01)  # Sleep for 10ms
            duration_ms = (time.time() - start_time) * 1000

            # Record AI latency
            collector.record_ai_latency(duration_ms)

            # Get summary
            summary = collector.get_summary()

            assert summary["ai_latency_ms"]["samples"] == 1
            assert summary["ai_latency_ms"]["avg"] >= 10  # Should be at least 10ms

    def test_interaction_recording(self):
        """Test recording interactions."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            collector = MetricsCollector(tmp_dir)

            # Start a session
            collector.start_session("test_session")

            # Record multiple interactions
            for _ in range(10):
                collector.record_interaction()

            # Get summary
            summary = collector.get_summary()

            assert summary["total_interactions"] == 10

    def test_error_recording(self):
        """Test recording errors."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            collector = MetricsCollector(tmp_dir)

            # Start a session
            collector.start_session("test_session")

            # Record an error
            collector.record_error(
                component="elevenlabs",
                error="Failed to connect",
                metadata={"error_type": "ConnectionError"},
            )

            # Get summary
            summary = collector.get_summary()

            assert summary["total_errors"] == 1

    def test_metrics_summary(self):
        """Test metrics summary generation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            collector = MetricsCollector(tmp_dir)

            # Start a session
            collector.start_session("test_session")

            # Record some test metrics
            for i in range(5):
                collector.record_stt_latency(100.0 + i * 10)  # 100, 110, 120, 130, 140
                collector.record_interaction()

            # Get summary
            summary = collector.get_summary()

            assert summary["total_interactions"] == 5
            assert summary["stt_latency_ms"]["samples"] == 5
            assert summary["stt_latency_ms"]["min"] == 100.0
            assert summary["stt_latency_ms"]["max"] == 140.0
            assert summary["stt_latency_ms"]["avg"] == 120.0  # (100+110+120+130+140)/5

    def test_save_and_load_metrics(self):
        """Test saving and loading session metrics."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            collector = MetricsCollector(tmp_dir)

            # Start a session and record metrics
            session_id = "test_session_save"
            collector.start_session(session_id)

            collector.record_stt_latency(100.0)
            collector.record_ai_latency(200.0)
            collector.record_tts_latency(150.0)
            collector.record_interaction()

            # End session and save
            collector.end_session()
            collector.save_metrics()

            # Load the session metrics
            loaded_metrics = collector.load_session_metrics(session_id)

            assert loaded_metrics is not None
            assert loaded_metrics.session_id == session_id
            assert loaded_metrics.total_interactions == 1
            assert len(loaded_metrics.stt_latencies) == 1
            assert loaded_metrics.stt_latencies[0] == 100.0


class TestSettings:
    """Test configuration management."""

    def test_default_settings(self):
        """Test default settings initialization."""
        settings = Settings()

        assert settings.ai_provider == "claude"
        assert settings.tts_provider == "elevenlabs"
        assert settings.audio.sample_rate == 16000
        assert settings.providers.whisperkit_model == "large-v3_turbo"
        assert settings.timeouts.ai_response_timeout == 30

    def test_environment_variable_override(self):
        """Test environment variable overrides."""
        with patch.dict(
            "os.environ",
            {
                "AI_PROVIDER": "gemini",
                "AUDIO_SAMPLE_RATE": "44100",
                "AI_RESPONSE_TIMEOUT": "60",
            },
        ):
            settings = Settings()

            assert settings.ai_provider == "gemini"
            assert settings.audio.sample_rate == 44100
            assert settings.timeouts.ai_response_timeout == 60

    def test_config_file_loading(self):
        """Test loading settings from config file."""
        config_data = {
            "audio": {"sample_rate": 48000, "channels": 2},
            "providers": {"whisperkit_model": "base"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name

        try:
            settings = Settings(config_file=config_file)

            assert settings.audio.sample_rate == 48000
            assert settings.audio.channels == 2
            assert settings.providers.whisperkit_model == "base"
        finally:
            Path(config_file).unlink()

    def test_save_config_file(self):
        """Test saving settings to config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_file = f.name

        try:
            settings = Settings()
            settings.audio.sample_rate = 48000
            settings.save_to_file(config_file)

            # Load saved config
            with open(config_file, "r") as f:
                saved_config = json.load(f)

            assert saved_config["audio"]["sample_rate"] == 48000
        finally:
            Path(config_file).unlink()

    def test_provider_config(self):
        """Test provider-specific configuration."""
        settings = Settings()

        whisperkit_config = settings.get_provider_config("whisperkit")
        assert "model" in whisperkit_config
        assert "compute_units" in whisperkit_config

        claude_config = settings.get_provider_config("claude")
        assert "output_format" in claude_config
        assert "system_prompt" in claude_config

        with pytest.raises(ValueError):
            settings.get_provider_config("unknown_provider")

    def test_settings_validation(self):
        """Test settings validation."""
        settings = Settings()

        # Valid settings should pass
        issues = settings.validate()
        assert len(issues) == 0

        # Invalid settings should be caught
        settings.audio.sample_rate = 12345  # Invalid
        settings.timeouts.ai_response_timeout = -1  # Invalid

        issues = settings.validate()
        assert len(issues) >= 2


class TestLogging:
    """Test logging configuration."""

    def test_json_formatter(self):
        """Test JSON log formatter."""
        import logging

        formatter = JsonFormatter()

        # Create a test log record
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test_logger"
        assert log_data["message"] == "Test message"
        assert "timestamp" in log_data

    def test_setup_logging_debug(self):
        """Test debug logging setup."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            setup_logging(debug=True, log_file=True, log_dir=tmp_dir)

            # Check that log files are created
            log_dir = Path(tmp_dir)
            log_files = list(log_dir.glob("*.log"))
            assert len(log_files) >= 1

    def test_setup_logging_session_specific(self):
        """Test session-specific logging setup."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            session_id = "test_session_123"

            setup_logging(session_id=session_id, log_dir=tmp_dir)

            # Check that session-specific log file is created
            log_dir = Path(tmp_dir)
            session_logs = list(log_dir.glob(f"session_{session_id}_*.log"))
            assert len(session_logs) >= 1


class TestIntegration:
    """Integration tests for state and metrics systems."""

    def test_session_with_metrics(self):
        """Test session management with metrics collection."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Setup
            session_manager = SessionManager(str(Path(tmp_dir) / "sessions"))
            metrics_collector = MetricsCollector(str(Path(tmp_dir) / "metrics"))

            # Create session
            session = session_manager.create_session("/test/project")

            # Record metrics during session
            # Start metrics collection
            metrics_collector.start_session(session.id)

            # Simulate end-to-end timing
            start_time = time.time()
            session.add_user_message("Hello")
            time.sleep(0.01)  # Simulate processing
            session.add_ai_message("Hi there!")
            duration_ms = (time.time() - start_time) * 1000

            # Record the latency
            metrics_collector.record_e2e_latency(duration_ms)
            metrics_collector.record_interaction()

            # Save session
            session_manager.save_session(session)

            # Verify session was saved
            loaded_session = session_manager.load_session(session.id, "/test/project")
            assert loaded_session is not None
            assert len(loaded_session.messages) == 2

            # Verify metrics were recorded
            summary = metrics_collector.get_summary()
            assert summary["total_interactions"] == 1
            assert summary["e2e_latency_ms"]["samples"] == 1
            assert summary["e2e_latency_ms"]["avg"] >= 10  # Should be at least 10ms

    def test_settings_with_all_components(self):
        """Test that settings work with all components."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create custom settings
            settings = Settings()
            settings.metrics.enabled = True
            settings.logging.file_enabled = True

            # Test that components can use settings
            assert settings.get_provider_config("whisperkit") is not None
            assert settings.validate() == []

            # Save and reload
            config_file = Path(tmp_dir) / "config.json"
            settings.save_to_file(config_file)

            new_settings = Settings(config_file=config_file)
            assert new_settings.metrics.enabled is True
            assert new_settings.logging.file_enabled is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
