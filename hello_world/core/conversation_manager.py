"""
Core conversation management system that orchestrates the entire pipeline.
"""

import threading
import time
from queue import Queue, Empty
from typing import Optional, Dict, Any
from dataclasses import dataclass
import structlog

from ..providers.stt.base import STTProvider
from ..providers.ai.base import AIProvider
from ..providers.tts.base import TTSProvider
from ..providers.registry import registry
from ..state.session_manager import SessionManager
from ..metrics.collector import MetricsCollector
from ..utils.interruption_handler import InterruptionHandler
from ..config.settings import settings


logger = structlog.get_logger()


@dataclass
class ConversationConfig:
    """Configuration for the conversation system."""

    ai_provider: str = "claude"  # claude or gemini
    tts_provider: str = "elevenlabs"
    stt_provider: str = "whisperkit"
    enable_interruptions: bool = True
    enable_metrics: bool = True
    debug_mode: bool = False
    mock_mode: bool = False


class ConversationManager:
    """
    Main orchestrator for the conversation system.
    Manages the flow between STT -> AI -> TTS with interruption handling.
    """

    def __init__(self, config: ConversationConfig):
        self.config = config

        # Initialize queues for inter-thread communication
        self.transcript_queue = Queue()
        self.response_queue = Queue()
        self.audio_output_queue = Queue()

        # State management
        self.is_running = False
        self.tts_playing = False
        self.session_manager = SessionManager()
        self.current_session = None

        # Initialize providers based on config
        self.stt_provider = self._initialize_stt_provider()
        self.ai_provider = self._initialize_ai_provider()
        self.tts_provider = self._initialize_tts_provider()

        # Initialize supporting components
        self.metrics_collector = MetricsCollector() if config.enable_metrics else None
        self.interruption_handler = (
            InterruptionHandler() if config.enable_interruptions else None
        )

        # Thread references and coordination
        self.stt_thread = None
        self.ai_thread = None
        self.tts_thread = None
        self.shutdown_event = threading.Event()
        self.error_count = 0
        self.max_retries = 3

    def _initialize_stt_provider(self) -> STTProvider:
        """Initialize the STT provider based on configuration."""
        if self.config.mock_mode:
            from mocks.providers import MockSTTProvider

            return MockSTTProvider()
        else:
            return registry.get_stt_provider(self.config.stt_provider)

    def _initialize_ai_provider(self) -> AIProvider:
        """Initialize the AI provider based on configuration."""
        if self.config.mock_mode:
            from mocks.providers import MockAIProvider

            return MockAIProvider(
                system_prompt=settings.system_prompts.default, streaming=True
            )
        else:
            # System prompt comes from settings
            return registry.get_ai_provider(self.config.ai_provider, streaming=True)

    def _initialize_tts_provider(self) -> TTSProvider:
        """Initialize the TTS provider based on configuration."""
        if self.config.mock_mode:
            from mocks.providers import MockTTSProvider

            return MockTTSProvider()
        else:
            return registry.get_tts_provider(self.config.tts_provider, streaming=True)

    def start(self, project_path: Optional[str] = None):
        """Start the conversation system."""
        logger.info(
            "Starting conversation system",
            ai_provider=self.config.ai_provider,
            tts_provider=self.config.tts_provider,
        )

        # Initialize session
        self.current_session = self.session_manager.create_session(project_path)

        # Set running flag
        self.is_running = True
        self.shutdown_event.clear()

        # Initialize providers
        try:
            self.stt_provider.initialize()
            self.ai_provider.initialize()
            self.tts_provider.initialize()
        except Exception as e:
            logger.error("Failed to initialize providers", error=str(e))
            raise

        # Start metrics collection
        if self.metrics_collector:
            self.metrics_collector.start_session(self.current_session.id)

        # Start provider threads
        self.stt_thread = threading.Thread(
            target=self._stt_worker, daemon=True, name="STT-Worker"
        )
        self.ai_thread = threading.Thread(
            target=self._ai_worker, daemon=True, name="AI-Worker"
        )
        self.tts_thread = threading.Thread(
            target=self._tts_worker, daemon=True, name="TTS-Worker"
        )

        self.stt_thread.start()
        self.ai_thread.start()
        self.tts_thread.start()

        logger.info("Conversation system started successfully")

    def stop(self):
        """Stop the conversation system gracefully."""
        logger.info("Stopping conversation system")

        # Set stop flags
        self.is_running = False
        self.shutdown_event.set()

        # Stop providers
        try:
            if self.stt_provider:
                self.stt_provider.stop()
            if self.ai_provider:
                self.ai_provider.stop()
            if self.tts_provider:
                self.tts_provider.stop()
        except Exception as e:
            logger.warning("Error stopping providers", error=str(e))

        # Wait for threads to finish
        threads = [self.stt_thread, self.ai_thread, self.tts_thread]
        for thread in threads:
            if thread and thread.is_alive():
                thread.join(timeout=5)
                if thread.is_alive():
                    logger.warning(f"Thread {thread.name} did not terminate gracefully")

        # End metrics collection
        if self.metrics_collector:
            self.metrics_collector.end_session()

        # Save session
        if self.current_session:
            self.session_manager.save_session(self.current_session)

        logger.info("Conversation system stopped")

    def _stt_worker(self):
        """STT worker thread - processes audio and produces transcripts."""
        logger.debug("STT worker started")

        retry_count = 0
        while self.is_running and not self.shutdown_event.is_set():
            try:
                # Stream transcripts from STT provider
                for transcript in self.stt_provider.stream_transcripts():
                    if not self.is_running or self.shutdown_event.is_set():
                        break

                    # Check for interruption
                    if (
                        self.interruption_handler
                        and transcript.is_speech_start
                        and self.tts_playing
                    ):
                        logger.debug(
                            "Speech detected during TTS playback - handling interruption"
                        )
                        self.handle_interruption()

                    # Skip empty transcripts
                    if not transcript.text.strip():
                        continue

                    # Add to transcript queue
                    self.transcript_queue.put(transcript)
                    logger.debug("Transcript added to queue", text=transcript.text[:50])

                    # Record metrics
                    if self.metrics_collector and transcript.latency:
                        self.metrics_collector.record_stt_latency(transcript.latency)

                    # Add to session history
                    if self.current_session:
                        # Note: session history handled in session_manager
                        pass

                # Reset retry count on successful operation
                retry_count = 0

            except Exception as e:
                logger.error("STT worker error", error=str(e), retry_count=retry_count)
                self._handle_stt_error(e)
                retry_count += 1

                if retry_count >= self.max_retries:
                    logger.error("STT worker exceeded max retries, stopping")
                    self.is_running = False
                    break

                # Wait before retry
                time.sleep(min(2**retry_count, 10))  # Exponential backoff

        logger.debug("STT worker stopped")

    def _ai_worker(self):
        """AI worker thread - processes transcripts and generates responses."""
        logger.debug("AI worker started")

        while self.is_running and not self.shutdown_event.is_set():
            try:
                # Get transcript from queue with timeout
                try:
                    transcript = self.transcript_queue.get(timeout=0.5)
                except Empty:
                    continue

                logger.debug("Processing transcript", text=transcript.text[:50])
                start_time = time.time()

                # Stream AI response
                full_response = ""
                first_token_recorded = False

                for response_chunk in self.ai_provider.stream_response(transcript.text):
                    if not self.is_running or self.shutdown_event.is_set():
                        break

                    # Check for interruption
                    if (
                        self.interruption_handler
                        and self.interruption_handler.is_interrupted_atomic()
                    ):
                        logger.debug("AI response interrupted")
                        self.ai_provider.stop_streaming()
                        break

                    # Record first token latency
                    if (
                        self.metrics_collector
                        and response_chunk.is_first
                        and not first_token_recorded
                    ):
                        latency_ms = (time.time() - start_time) * 1000
                        self.metrics_collector.record_ai_latency(latency_ms)
                        first_token_recorded = True

                    # Accumulate full response and send to TTS when complete
                    if response_chunk.is_final:
                        full_response = response_chunk.full_text
                        if full_response:
                            # Send complete response to TTS queue
                            self.response_queue.put(response_chunk)

                # Record completed interaction
                if self.metrics_collector and full_response:
                    self.metrics_collector.record_interaction()

                # Add complete response to session
                if self.current_session and full_response:
                    # Note: session history handled in session_manager
                    pass

            except Exception as e:
                logger.error("AI worker error", error=str(e))
                if self.metrics_collector:
                    self.metrics_collector.record_error("ai", str(e))

                # Continue processing other transcripts
                time.sleep(0.1)

        logger.debug("AI worker stopped")

    def _tts_worker(self):
        """TTS worker thread - converts text to speech and plays audio."""
        logger.debug("TTS worker started")

        while self.is_running and not self.shutdown_event.is_set():
            try:
                # Get response from queue with timeout
                try:
                    response = self.response_queue.get(timeout=0.5)
                except Empty:
                    continue

                # Get the text content (final responses use full_text)
                text_to_speak = (
                    response.full_text if response.is_final else response.text
                )
                logger.debug("Processing TTS response", text=text_to_speak[:50])
                self.tts_playing = True
                start_time = time.time()
                first_audio_recorded = False

                try:
                    # Stream TTS audio
                    for audio_chunk in self.tts_provider.stream_audio(text_to_speak):
                        if not self.is_running or self.shutdown_event.is_set():
                            break

                        # Check for interruption
                        if (
                            self.interruption_handler
                            and self.interruption_handler.is_interrupted_atomic()
                        ):
                            logger.debug("TTS playback interrupted")
                            self.tts_provider.stop_playback()
                            break

                        # Play audio chunk
                        self.tts_provider.play_chunk(audio_chunk)

                        # Record first audio latency
                        if (
                            self.metrics_collector
                            and audio_chunk.is_first
                            and not first_audio_recorded
                        ):
                            latency_ms = (time.time() - start_time) * 1000
                            self.metrics_collector.record_tts_latency(latency_ms)
                            first_audio_recorded = True

                except Exception as e:
                    logger.error("TTS streaming error", error=str(e))
                    if self.metrics_collector:
                        self.metrics_collector.record_error("tts", str(e))

                finally:
                    self.tts_playing = False

            except Exception as e:
                logger.error("TTS worker error", error=str(e))
                if self.metrics_collector:
                    self.metrics_collector.record_error("tts", str(e))

                # Continue processing other responses
                time.sleep(0.1)

        logger.debug("TTS worker stopped")

    def handle_interruption(self):
        """Handle user interruption during AI/TTS output."""
        logger.info("Handling user interruption")

        # Record interruption in metrics
        if self.metrics_collector:
            self.metrics_collector.record_interruption()

        # Clear response queue to stop pending TTS
        cleared_responses = 0
        while not self.response_queue.empty():
            try:
                self.response_queue.get_nowait()
                cleared_responses += 1
            except Empty:
                break

        logger.debug("Cleared response queue", cleared_responses=cleared_responses)

        # Stop TTS playback
        if self.tts_playing:
            try:
                self.tts_provider.stop_playback()
            except Exception as e:
                logger.warning("Error stopping TTS playback", error=str(e))
            self.tts_playing = False

        # Notify AI provider to stop streaming
        try:
            self.ai_provider.stop_streaming()
        except Exception as e:
            logger.warning("Error stopping AI streaming", error=str(e))

        # Reset interruption flag
        if self.interruption_handler:
            self.interruption_handler.reset()

    def get_status(self) -> Dict[str, Any]:
        """Get current system status."""
        return {
            "is_running": self.is_running,
            "tts_playing": self.tts_playing,
            "ai_provider": self.config.ai_provider,
            "tts_provider": self.config.tts_provider,
            "session_id": self.current_session.id if self.current_session else None,
            "transcript_queue_size": self.transcript_queue.qsize(),
            "response_queue_size": self.response_queue.qsize(),
            "error_count": self.error_count,
            "providers_status": {
                "stt": self.stt_provider.get_status() if self.stt_provider else None,
                "ai": self.ai_provider.get_status() if self.ai_provider else None,
                "tts": self.tts_provider.get_status() if self.tts_provider else None,
            },
        }

    def _handle_stt_error(self, error: Exception) -> None:
        """Handle STT provider errors with recovery attempts."""
        self.error_count += 1

        if self.metrics_collector:
            self.metrics_collector.record_error("stt", str(error))

        logger.warning(
            "STT error occurred, attempting recovery",
            error=str(error),
            error_count=self.error_count,
        )

        # Attempt to restart STT provider
        try:
            if hasattr(self.stt_provider, "stop"):
                self.stt_provider.stop()
            time.sleep(1)  # Brief pause before restart
            self.stt_provider.initialize()
            logger.info("STT provider restarted successfully")
        except Exception as e:
            logger.error("Failed to restart STT provider", error=str(e))
