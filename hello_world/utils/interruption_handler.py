"""Interruption handling for conversation flow with advanced VAD."""

import threading
import time
import collections
import numpy as np
import webrtcvad
from typing import Optional, Callable, Deque
import structlog


logger = structlog.get_logger()


class InterruptionHandler:
    """Handles interruption detection and coordination with advanced VAD."""

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        vad_aggressiveness: int = 3,
        voice_threshold: float = 0.7,
        silence_duration_ms: int = 500,
    ):
        self.is_interrupted = False
        self._lock = threading.Lock()
        self._callbacks = []
        self._last_interruption_time = 0

        # VAD settings
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.vad_aggressiveness = vad_aggressiveness
        self.voice_threshold = voice_threshold
        self.silence_duration_ms = silence_duration_ms

        # Initialize VAD
        self.vad = webrtcvad.Vad(vad_aggressiveness)

        # Voice activity tracking
        self.voice_frames: Deque[bool] = collections.deque(maxlen=100)
        self.is_voice_active = False
        self.last_voice_time = 0

        # Audio level tracking with dynamic thresholds
        self.audio_levels: Deque[float] = collections.deque(maxlen=50)
        self.noise_floor = 0.0
        self.dynamic_threshold = 0.0
        self._update_threshold_counter = 0

    def process_audio_frame(self, audio_data: np.ndarray) -> bool:
        """
        Process audio frame for voice activity detection.
        Returns True if voice activity detected (potential interruption).
        """
        current_time = time.time()

        # Calculate audio level (RMS)
        audio_level = float(np.sqrt(np.mean(audio_data.astype(np.float32) ** 2)))
        self.audio_levels.append(audio_level)

        # Update dynamic threshold periodically
        self._update_threshold_counter += 1
        if self._update_threshold_counter % 20 == 0:  # Every ~600ms
            self._update_dynamic_threshold()

        # Ensure frame is correct size and format for webrtcvad
        if len(audio_data) != self.frame_size:
            # Pad or truncate to correct size
            if len(audio_data) < self.frame_size:
                audio_data = np.pad(audio_data, (0, self.frame_size - len(audio_data)))
            else:
                audio_data = audio_data[: self.frame_size]

        # Convert to bytes for VAD (int16 format)
        audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()

        try:
            # Use webrtcvad for voice activity detection
            is_voice = self.vad.is_speech(audio_bytes, self.sample_rate)

            # Also check audio level against dynamic threshold
            level_voice = audio_level > self.dynamic_threshold

            # Combine VAD and level detection
            voice_detected = is_voice and level_voice

            self.voice_frames.append(voice_detected)

            # Calculate voice activity ratio over recent frames
            if len(self.voice_frames) > 10:
                voice_ratio = sum(list(self.voice_frames)[-10:]) / 10
                was_voice_active = self.is_voice_active
                self.is_voice_active = voice_ratio >= self.voice_threshold

                # Update last voice time if voice is active
                if self.is_voice_active:
                    self.last_voice_time = current_time

                # Detect voice start (transition from silence to voice)
                if not was_voice_active and self.is_voice_active:
                    logger.debug(
                        "Voice activity started",
                        voice_ratio=voice_ratio,
                        audio_level=audio_level,
                        threshold=self.dynamic_threshold,
                    )
                    return True

        except Exception as e:
            logger.error("VAD processing error", error=str(e))
            return False

        return False

    def _update_dynamic_threshold(self) -> None:
        """Update dynamic threshold based on recent audio levels."""
        if len(self.audio_levels) < 10:
            return

        # Calculate noise floor (minimum of recent levels)
        recent_levels = list(self.audio_levels)
        recent_levels.sort()
        self.noise_floor = float(
            np.mean(recent_levels[: len(recent_levels) // 4])
        )  # Bottom 25%

        # Set dynamic threshold above noise floor
        self.dynamic_threshold = max(float(self.noise_floor * 3.0), 0.01)

        logger.debug(
            "Updated audio thresholds",
            noise_floor=self.noise_floor,
            dynamic_threshold=self.dynamic_threshold,
        )

    def is_silence(self) -> bool:
        """Check if we're currently in a silence period."""
        if not self.last_voice_time:
            return True

        silence_duration = (time.time() - self.last_voice_time) * 1000
        return silence_duration > self.silence_duration_ms

    def get_voice_activity_stats(self) -> dict:
        """Get current voice activity statistics."""
        return {
            "is_voice_active": self.is_voice_active,
            "last_voice_time": self.last_voice_time,
            "silence_duration_ms": (time.time() - self.last_voice_time) * 1000
            if self.last_voice_time
            else 0,
            "is_silence": self.is_silence(),
            "noise_floor": self.noise_floor,
            "dynamic_threshold": self.dynamic_threshold,
            "recent_voice_ratio": sum(list(self.voice_frames)[-10:])
            / min(10, len(self.voice_frames))
            if self.voice_frames
            else 0,
        }

    def trigger_interruption(self) -> None:
        """Trigger an interruption event."""
        with self._lock:
            if self.is_interrupted:
                # Already interrupted
                return

            self.is_interrupted = True
            self._last_interruption_time = time.time()

        logger.info("Interruption triggered")

        # Execute callbacks
        for callback in self._callbacks:
            try:
                callback()
            except Exception as e:
                logger.error("Interruption callback error", error=str(e))

    def reset(self) -> None:
        """Reset interruption state."""
        with self._lock:
            self.is_interrupted = False

        logger.debug("Interruption state reset")

    def is_interrupted_atomic(self) -> bool:
        """Check interruption state atomically."""
        with self._lock:
            return self.is_interrupted

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called on interruption."""
        self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[], None]) -> None:
        """Unregister an interruption callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def get_time_since_interruption(self) -> Optional[float]:
        """Get time since last interruption in seconds."""
        if self._last_interruption_time == 0:
            return None
        return time.time() - self._last_interruption_time
