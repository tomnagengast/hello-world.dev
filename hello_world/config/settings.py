"""Configuration settings for the conversation system."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
import json
import structlog


logger = structlog.get_logger()


@dataclass
class SystemPrompts:
    """System prompts for AI providers."""
    default: str = "You are a breezy but focused senior developer who gets straight to the point without getting stuck in the weeds. Be conversational but efficient."
    
    
@dataclass
class AudioSettings:
    """Audio configuration settings."""
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    format: str = "int16"
    

@dataclass
class ProviderSettings:
    """Provider-specific settings."""
    # WhisperKit
    whisperkit_model: str = "large-v3_turbo"
    whisperkit_compute_units: str = "cpuAndNeuralEngine"
    whisperkit_vad_enabled: bool = True
    
    # Claude
    claude_output_format: str = "stream-json"
    
    # Gemini
    gemini_model: str = "gemini-pro"
    gemini_temperature: float = 0.7
    gemini_max_tokens: int = 2048
    
    # ElevenLabs
    elevenlabs_voice_id: str = "pNInz6obpgDQGcFmaJgB"  # Adam voice
    elevenlabs_model_id: str = "eleven_flash_v2_5"
    elevenlabs_output_format: str = "mp3_22050_32"
    elevenlabs_stability: float = 0.5
    elevenlabs_similarity_boost: float = 0.8
    elevenlabs_style: float = 0.0
    elevenlabs_speed: float = 1.0
    elevenlabs_use_speaker_boost: bool = True
    

@dataclass
class TimeoutSettings:
    """Timeout settings for various operations."""
    ai_response_timeout: int = 30  # seconds
    tts_generation_timeout: int = 10  # seconds
    whisperkit_restart_timeout: int = 5  # seconds
    

@dataclass
class RetrySettings:
    """Retry configuration."""
    max_retries: int = 3
    initial_backoff: float = 1.0  # seconds
    backoff_multiplier: float = 2.0
    max_backoff: float = 30.0  # seconds
    

class Settings:
    """Main settings class for the conversation system."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = Path(config_file) if config_file else None
        
        # Initialize sub-settings
        self.system_prompts = SystemPrompts()
        self.audio = AudioSettings()
        self.providers = ProviderSettings()
        self.timeouts = TimeoutSettings()
        self.retries = RetrySettings()
        
        # Load from file if provided
        if self.config_file and self.config_file.exists():
            self.load_from_file()
            
        # Override with environment variables
        self.load_from_env()
        
    def load_from_file(self) -> None:
        """Load settings from configuration file."""
        # PSEUDOCODE: Load from JSON/YAML file
        # try:
        #     with open(self.config_file, 'r') as f:
        #         config = json.load(f)
        #         
        #     # Update settings from config
        #     if "system_prompts" in config:
        #         self.system_prompts.default = config["system_prompts"].get("default", self.system_prompts.default)
        #         
        #     if "audio" in config:
        #         for key, value in config["audio"].items():
        #             if hasattr(self.audio, key):
        #                 setattr(self.audio, key, value)
        #                 
        #     # ... similar for other settings
        #     
        #     logger.info("Loaded settings from file", file=str(self.config_file))
        #     
        # except Exception as e:
        #     logger.error("Failed to load settings from file", 
        #                 file=str(self.config_file),
        #                 error=str(e))
        
        pass
        
    def load_from_env(self) -> None:
        """Load settings from environment variables."""
        # AI Provider selection
        self.ai_provider = os.getenv("AI_PROVIDER", "claude")
        self.tts_provider = os.getenv("TTS_PROVIDER", "elevenlabs")
        
        # Provider-specific overrides
        if os.getenv("WHISPERKIT_MODEL"):
            self.providers.whisperkit_model = os.getenv("WHISPERKIT_MODEL")
            
        if os.getenv("ELEVENLABS_VOICE_ID"):
            self.providers.elevenlabs_voice_id = os.getenv("ELEVENLABS_VOICE_ID")
            
        # Timeout overrides
        if os.getenv("AI_RESPONSE_TIMEOUT"):
            self.timeouts.ai_response_timeout = int(os.getenv("AI_RESPONSE_TIMEOUT"))
            
    def save_to_file(self, file_path: Optional[str] = None) -> None:
        """Save current settings to file."""
        # PSEUDOCODE: Save settings
        # save_path = Path(file_path) if file_path else self.config_file
        # if not save_path:
        #     raise ValueError("No file path provided")
        #     
        # config = {
        #     "system_prompts": {"default": self.system_prompts.default},
        #     "audio": {
        #         "sample_rate": self.audio.sample_rate,
        #         "channels": self.audio.channels,
        #         "chunk_size": self.audio.chunk_size,
        #         "format": self.audio.format
        #     },
        #     "providers": {
        #         "whisperkit_model": self.providers.whisperkit_model,
        #         # ... other provider settings
        #     },
        #     "timeouts": {
        #         "ai_response_timeout": self.timeouts.ai_response_timeout,
        #         # ... other timeout settings
        #     },
        #     "retries": {
        #         "max_retries": self.retries.max_retries,
        #         # ... other retry settings
        #     }
        # }
        # 
        # with open(save_path, 'w') as f:
        #     json.dump(config, f, indent=2)
        #     
        # logger.info("Saved settings to file", file=str(save_path))
        
        pass
        
    def get_provider_config(self, provider_type: str) -> Dict[str, Any]:
        """Get configuration for a specific provider."""
        if provider_type == "whisperkit":
            return {
                "model": self.providers.whisperkit_model,
                "compute_units": self.providers.whisperkit_compute_units,
                "vad_enabled": self.providers.whisperkit_vad_enabled
            }
        elif provider_type == "claude":
            return {
                "output_format": self.providers.claude_output_format,
                "system_prompt": self.system_prompts.default
            }
        elif provider_type == "gemini":
            return {
                "model": self.providers.gemini_model,
                "temperature": self.providers.gemini_temperature,
                "max_tokens": self.providers.gemini_max_tokens,
                "system_prompt": self.system_prompts.default
            }
        elif provider_type == "elevenlabs":
            return {
                "voice_id": self.providers.elevenlabs_voice_id,
                "model_id": self.providers.elevenlabs_model_id,
                "output_format": self.providers.elevenlabs_output_format,
                "stability": self.providers.elevenlabs_stability,
                "similarity_boost": self.providers.elevenlabs_similarity_boost,
                "style": self.providers.elevenlabs_style,
                "speed": self.providers.elevenlabs_speed,
                "use_speaker_boost": self.providers.elevenlabs_use_speaker_boost
            }
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")


# Global settings instance
settings = Settings()