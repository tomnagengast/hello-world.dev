"""TTS testing utility implementation."""

import time
import io
from pathlib import Path
from typing import Optional, Dict, Any
import structlog
import pygame

from ..providers import registry
from ..providers.tts.base import TTSProvider, AudioChunk
from ..config.settings import settings

logger = structlog.get_logger()


class TTSTestUtility:
    """Utility for testing TTS providers in isolation."""
    
    def __init__(self, provider: str = "elevenlabs", voice: Optional[str] = None, 
                 speed: float = 1.0, debug: bool = False):
        self.provider_name = provider
        self.voice = voice
        self.speed = speed
        self.debug = debug
        self.provider: Optional[TTSProvider] = None
        self.metrics: Dict[str, Any] = {}
        
    def _initialize_provider(self) -> None:
        """Initialize the TTS provider."""
        try:
            # Get provider from registry
            provider_kwargs = {}
            
            # Set voice if specified
            if self.voice:
                provider_kwargs["voice_id"] = self.voice
                
            # Set speed if specified and not default
            if self.speed != 1.0:
                provider_kwargs["speed"] = self.speed
                
            self.provider = registry.get_tts_provider(self.provider_name, **provider_kwargs)
            self.provider.initialize()
            
            logger.info("TTS provider initialized", 
                       provider=self.provider_name, 
                       voice=self.voice, 
                       speed=self.speed)
                       
        except Exception as e:
            logger.error("Failed to initialize TTS provider", 
                        provider=self.provider_name, 
                        error=str(e))
            raise RuntimeError(f"Failed to initialize TTS provider '{self.provider_name}': {str(e)}")
    
    def run_tts_test(self, text: str, output_file: Optional[str] = None, 
                     output_format: str = "mp3") -> bool:
        """
        Run TTS test with the given text.
        
        Args:
            text: Text to convert to speech
            output_file: Optional output file path
            output_format: Audio format for output file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Initialize provider
            start_init = time.time()
            self._initialize_provider()
            init_time = time.time() - start_init
            
            self.metrics["initialization_time"] = init_time
            self.metrics["text_length"] = len(text)
            
            if output_file:
                # File output mode
                return self._run_file_output_test(text, output_file, output_format)
            else:
                # Speaker playback mode
                return self._run_playback_test(text)
                
        except Exception as e:
            logger.error("TTS test failed", error=str(e))
            if self.debug:
                raise
            return False
        finally:
            if self.provider:
                try:
                    self.provider.stop()
                except Exception as e:
                    logger.warning("Error stopping provider", error=str(e))
    
    def _run_playback_test(self, text: str) -> bool:
        """Run TTS test with speaker playback."""
        try:
            print(f"🔊 Playing: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            print(f"Provider: {self.provider_name}")
            if self.voice:
                print(f"Voice: {self.voice}")
            print(f"Speed: {self.speed}x")
            print("\nPress Ctrl+C to stop playback...")
            
            # Generate and play audio
            start_gen = time.time()
            audio_chunks = []
            
            for chunk in self.provider.stream_audio(text):
                audio_chunks.append(chunk)
                
                # Play chunk immediately for real-time playback
                self.provider.play_chunk(chunk)
                
                # Handle interruption
                if chunk.is_final:
                    break
            
            gen_time = time.time() - start_gen
            self.metrics["generation_time"] = gen_time
            self.metrics["total_chunks"] = len(audio_chunks)
            
            # Wait for playback to complete
            # Check provider status to see if playing
            while True:
                status = self.provider.get_status()
                if not status.get("is_playing", False):
                    break
                time.sleep(0.1)
            
            print("✅ Playback completed successfully")
            return True
            
        except KeyboardInterrupt:
            print("\n⏹️  Playback stopped by user")
            if self.provider:
                self.provider.stop_playback()
            return True
        except Exception as e:
            logger.error("Playback test failed", error=str(e))
            return False
    
    def _run_file_output_test(self, text: str, output_file: str, output_format: str) -> bool:
        """Run TTS test with file output."""
        try:
            output_path = Path(output_file)
            print(f"💾 Generating audio file: {output_path}")
            print(f"Provider: {self.provider_name}")
            if self.voice:
                print(f"Voice: {self.voice}")
            print(f"Speed: {self.speed}x")
            print(f"Format: {output_format}")
            
            # Generate audio data
            start_gen = time.time()
            audio_data = io.BytesIO()
            chunk_count = 0
            
            for chunk in self.provider.stream_audio(text):
                if chunk.data:
                    audio_data.write(chunk.data)
                    chunk_count += 1
                
                if chunk.is_final:
                    break
            
            gen_time = time.time() - start_gen
            
            # Write to file
            audio_bytes = audio_data.getvalue()
            if not audio_bytes:
                raise ValueError("No audio data generated")
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write audio file
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            
            # Update metrics
            self.metrics["generation_time"] = gen_time
            self.metrics["total_chunks"] = chunk_count
            self.metrics["output_file_size"] = len(audio_bytes)
            self.metrics["output_file"] = str(output_path)
            
            print(f"✅ Audio file generated successfully: {output_path}")
            print(f"   File size: {len(audio_bytes):,} bytes")
            print(f"   Generation time: {gen_time:.2f}s")
            
            return True
            
        except Exception as e:
            logger.error("File output test failed", error=str(e))
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from the test."""
        # Always include basic info
        self.metrics.update({
            "provider_name": self.provider_name,
            "voice_used": self.voice,
            "speed_used": self.speed
        })
        
        # Add provider status if available
        if self.provider:
            try:
                provider_status = self.provider.get_status()
                self.metrics["provider_status"] = provider_status
            except Exception as e:
                logger.warning("Failed to get provider status", error=str(e))
        
        return self.metrics.copy()