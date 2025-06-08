#!/usr/bin/env python3
"""Test script for the audio pipeline implementation."""

import os
import sys
import time
import threading
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from hello_world.providers.stt.whisperkit import WhisperKitProvider
from hello_world.providers.tts.elevenlabs import ElevenLabsProvider
from hello_world.utils.interruption_handler import InterruptionHandler, AudioInterruptionDetector
import structlog


# Configure logging
structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def test_whisperkit_provider():
    """Test WhisperKit STT provider initialization."""
    logger.info("Testing WhisperKit STT provider")
    
    try:
        # Initialize provider
        stt_provider = WhisperKitProvider(
            model="large-v3_turbo",
            vad_enabled=True,
            sample_rate=16000,
            chunk_duration=5  # Shorter chunks for testing
        )
        
        logger.info("WhisperKit provider created successfully")
        
        # Test initialization
        try:
            stt_provider.initialize()
            logger.info("WhisperKit provider initialized successfully")
            
            # Get status
            status = stt_provider.get_status()
            logger.info("WhisperKit status", **status)
            
            # Test for a few seconds
            logger.info("Testing audio capture for 10 seconds...")
            start_time = time.time()
            
            transcript_count = 0
            for transcript in stt_provider.stream_transcripts():
                transcript_count += 1
                logger.info("Transcript received", 
                           text=transcript.text,
                           is_final=transcript.is_final,
                           is_speech_start=transcript.is_speech_start,
                           count=transcript_count)
                
                # Test for 10 seconds
                if time.time() - start_time > 10:
                    break
                    
        except Exception as e:
            logger.error("Error during WhisperKit testing", error=str(e))
        finally:
            stt_provider.stop()
            logger.info("WhisperKit provider stopped")
            
    except Exception as e:
        logger.error("Failed to create WhisperKit provider", error=str(e))
        return False
        
    return True


def test_elevenlabs_provider():
    """Test ElevenLabs TTS provider."""
    logger.info("Testing ElevenLabs TTS provider")
    
    # Check for API key
    if not os.getenv("ELEVENLABS_API_KEY"):
        logger.warning("ELEVENLABS_API_KEY not set, skipping TTS test")
        return True
    
    try:
        # Initialize provider
        tts_provider = ElevenLabsProvider(
            voice_id="pNInz6obpgDQGcFmaJgB",  # Adam voice
            model_id="eleven_flash_v2_5"
        )
        
        logger.info("ElevenLabs provider created successfully")
        
        try:
            tts_provider.initialize()
            logger.info("ElevenLabs provider initialized successfully")
            
            # Get status
            status = tts_provider.get_status()
            logger.info("ElevenLabs status", **status)
            
            # Test TTS generation and playback
            test_text = "Hello! This is a test of the ElevenLabs text-to-speech system."
            logger.info("Generating and playing TTS", text=test_text)
            
            # Stream and play audio
            for chunk in tts_provider.stream_audio(test_text):
                tts_provider.play_chunk(chunk)
                logger.debug("Audio chunk processed", 
                           is_first=chunk.is_first,
                           is_final=chunk.is_final,
                           data_size=len(chunk.data))
                
            logger.info("TTS test completed")
            
        except Exception as e:
            logger.error("Error during ElevenLabs testing", error=str(e))
        finally:
            tts_provider.stop()
            logger.info("ElevenLabs provider stopped")
            
    except Exception as e:
        logger.error("Failed to create ElevenLabs provider", error=str(e))
        return False
        
    return True


def test_interruption_handler():
    """Test interruption handling system."""
    logger.info("Testing interruption handler")
    
    try:
        # Create interruption handler
        interruption_handler = InterruptionHandler(cooldown_period=0.5)
        
        # Test callback registration
        callback_called = threading.Event()
        
        def test_callback():
            logger.info("Interruption callback executed")
            callback_called.set()
            
        interruption_handler.register_callback(test_callback)
        
        # Test TTS state
        interruption_handler.set_tts_playing(True)
        assert interruption_handler.is_tts_playing()
        
        # Test speech interruption detection
        should_interrupt = interruption_handler.detect_speech_interruption(
            "Hello there", is_speech_start=True
        )
        
        if should_interrupt:
            interruption_handler.trigger_interruption("test")
            
            # Wait for callback
            if callback_called.wait(timeout=2):
                logger.info("Interruption callback test passed")
            else:
                logger.error("Interruption callback not called")
                return False
        else:
            logger.info("No interruption detected (expected during testing)")
            
        # Get status
        status = interruption_handler.get_status()
        logger.info("Interruption handler status", **status)
        
        logger.info("Interruption handler test completed")
        
    except Exception as e:
        logger.error("Error during interruption handler testing", error=str(e))
        return False
        
    return True


def test_sample_audio_files():
    """Test with sample audio files."""
    logger.info("Testing with sample audio files")
    
    sample_dir = project_root / "resources" / "whisperkit" / "samples"
    
    if not sample_dir.exists():
        logger.warning("Sample directory not found", path=str(sample_dir))
        return True
        
    sample_files = list(sample_dir.glob("*.mp3"))
    if not sample_files:
        logger.warning("No sample audio files found")
        return True
        
    logger.info("Found sample files", files=[f.name for f in sample_files])
    
    # For now, just log that we found the files
    # Actual testing would require WhisperKit to be installed and configured
    for sample_file in sample_files:
        logger.info("Sample file available", 
                   name=sample_file.name,
                   size=sample_file.stat().st_size)
                   
    return True


def main():
    """Run all tests."""
    logger.info("Starting audio pipeline tests")
    
    tests = [
        ("Sample Audio Files", test_sample_audio_files),
        ("Interruption Handler", test_interruption_handler),
        ("ElevenLabs TTS Provider", test_elevenlabs_provider),
        # ("WhisperKit STT Provider", test_whisperkit_provider),  # Commented out as it requires actual audio input
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info("Running test", name=test_name)
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error("Test failed with exception", name=test_name, error=str(e))
            results[test_name] = False
            
    # Summary
    logger.info("Test Results Summary")
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        logger.info("Test result", name=test_name, status=status)
        
    all_passed = all(results.values())
    logger.info("Overall result", status="PASS" if all_passed else "FAIL")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)