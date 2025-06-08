"""WhisperKit STT provider for file processing."""

import subprocess
import time
from pathlib import Path
from typing import Iterator, Optional, Union
import structlog

from .base import STTProvider, Transcript


logger = structlog.get_logger()


class WhisperKitFileProvider(STTProvider):
    """
    WhisperKit STT provider for processing audio files directly.
    Designed for testing and batch processing scenarios.
    """

    def __init__(
        self,
        model: str = "large-v3_turbo",
        compute_units: str = "cpuAndNeuralEngine",
        whisperkit_path: str = "/opt/homebrew/bin/whisperkit-cli",
        verbose: bool = False,
    ):
        self.model = model
        self.compute_units = compute_units
        self.whisperkit_path = whisperkit_path
        self.verbose = verbose

        # State management
        self.current_file: Optional[Path] = None
        self.process: Optional[subprocess.Popen] = None
        self.is_initialized = False

        # Performance metrics
        self.processing_start_time: Optional[float] = None
        self.processing_end_time: Optional[float] = None

    def initialize(self) -> None:
        """Initialize the provider by checking WhisperKit availability."""
        logger.info(
            "Initializing WhisperKit file provider",
            model=self.model,
            whisperkit_path=self.whisperkit_path,
        )

        # Check if WhisperKit CLI is available
        try:
            result = subprocess.run(
                [self.whisperkit_path, "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise RuntimeError(f"WhisperKit CLI not working: {result.stderr}")
        except FileNotFoundError:
            raise RuntimeError(f"WhisperKit CLI not found at {self.whisperkit_path}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("WhisperKit CLI check timed out")

        self.is_initialized = True
        logger.info("WhisperKit file provider initialized successfully")

    def process_file(self, file_path: Union[str, Path]) -> Iterator[Transcript]:
        """
        Process an audio file and yield transcripts.

        Args:
            file_path: Path to the audio file to process

        Yields:
            Transcript objects containing the transcribed text
        """
        if not self.is_initialized:
            raise RuntimeError("Provider not initialized. Call initialize() first.")

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        self.current_file = file_path
        logger.info("Processing audio file", file_path=str(file_path))

        # Build WhisperKit command
        cmd = [
            self.whisperkit_path,
            "transcribe",
            "--audio-path",
            str(file_path),
            "--model",
            self.model,
            "--audio-encoder-compute-units",
            self.compute_units,
            "--text-decoder-compute-units",
            self.compute_units,
        ]

        if self.verbose:
            cmd.append("--verbose")

        try:
            self.processing_start_time = time.time()

            # Run WhisperKit process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
            )

            logger.info(
                "WhisperKit subprocess started",
                pid=self.process.pid,
                command=" ".join(cmd),
            )

            # Read output line by line
            transcript_text = ""
            while True:
                line = self.process.stdout.readline()
                if not line:
                    # Check if process has terminated
                    if self.process.poll() is not None:
                        break
                    continue

                # Clean and accumulate text
                line = line.strip()
                if line:
                    transcript_text += line + " "

            # Wait for process to complete
            return_code = self.process.wait()
            self.processing_end_time = time.time()

            if return_code != 0:
                stderr_output = (
                    self.process.stderr.read() if self.process.stderr else ""
                )
                logger.error(
                    "WhisperKit process failed",
                    return_code=return_code,
                    stderr=stderr_output,
                )
                raise RuntimeError(
                    f"WhisperKit failed with code {return_code}: {stderr_output}"
                )

            # Create final transcript
            processing_time = self.processing_end_time - self.processing_start_time
            transcript = Transcript(
                text=transcript_text.strip(),
                timestamp=self.processing_end_time,
                is_final=True,
                is_speech_start=len(transcript_text.strip()) > 0,
                confidence=None,  # WhisperKit doesn't provide confidence scores
                latency=processing_time * 1000,  # Convert to milliseconds
            )

            logger.info(
                "File processing completed",
                processing_time_ms=processing_time * 1000,
                text_length=len(transcript.text),
            )

            yield transcript

        except Exception as e:
            logger.error(
                "Error processing file", error=str(e), file_path=str(file_path)
            )
            raise
        finally:
            if self.process:
                try:
                    # Ensure process is terminated
                    if self.process.poll() is None:
                        self.process.terminate()
                        self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
                except Exception as e:
                    logger.warning("Error cleaning up process", error=str(e))
                finally:
                    self.process = None

    def stream_transcripts(self) -> Iterator[Transcript]:
        """
        Stream transcripts - not applicable for file processing.
        Raises NotImplementedError as this provider is for file processing only.
        """
        raise NotImplementedError(
            "WhisperKitFileProvider is for file processing only. "
            "Use process_file() method instead."
        )

    def stop(self) -> None:
        """Stop the provider and clean up resources."""
        logger.info("Stopping WhisperKit file provider")

        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("WhisperKit process didn't terminate, killing")
                self.process.kill()
                self.process.wait()
            except Exception as e:
                logger.error("Error stopping WhisperKit process", error=str(e))
            finally:
                self.process = None

        self.current_file = None
        logger.info("WhisperKit file provider stopped")

    def get_status(self) -> dict:
        """Get provider status."""
        return {
            "provider": "whisperkit_file",
            "model": self.model,
            "is_initialized": self.is_initialized,
            "current_file": str(self.current_file) if self.current_file else None,
            "process_running": self.process is not None and self.process.poll() is None,
            "compute_units": self.compute_units,
            "whisperkit_path": self.whisperkit_path,
            "last_processing_time_ms": (
                (self.processing_end_time - self.processing_start_time) * 1000
                if self.processing_start_time and self.processing_end_time
                else None
            ),
        }

    @staticmethod
    def supported_formats() -> list[str]:
        """Return list of supported audio formats."""
        return [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"]

    def is_format_supported(self, file_path: Union[str, Path]) -> bool:
        """Check if the file format is supported."""
        file_path = Path(file_path)
        return file_path.suffix.lower() in self.supported_formats()
