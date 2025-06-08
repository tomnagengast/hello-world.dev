"""Configuration settings for the conversation system."""

import os
from pathlib import Path
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass, field
import json
import structlog
from dotenv import load_dotenv
import threading


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
    

@dataclass
class MetricsSettings:
    """Metrics collection settings."""
    enabled: bool = True
    collection_interval_ms: int = 100
    max_pending_metrics: int = 1000
    cleanup_interval_days: int = 30
    

@dataclass 
class LoggingSettings:
    """Logging configuration settings."""
    level: str = "INFO"
    format: str = "json"
    file_enabled: bool = True
    file_rotation_mb: int = 10
    file_backup_count: int = 7
    session_logs: bool = True
    

class Settings:
    """Main settings class for the conversation system."""
    
    def __init__(self, config_file: Optional[Union[str, Path]] = None, 
                 auto_reload: bool = True):
        self.config_file = Path(config_file) if config_file else None
        self.auto_reload = auto_reload
        self._lock = threading.RLock()
        self._env_loaded = False
        
        # Initialize sub-settings
        self.system_prompts = SystemPrompts()
        self.audio = AudioSettings()
        self.providers = ProviderSettings()
        self.timeouts = TimeoutSettings()
        self.retries = RetrySettings()
        self.metrics = MetricsSettings()
        self.logging = LoggingSettings()
        
        # Load .env file first
        self._load_env_file()
        
        # Load from file if provided
        if self.config_file and self.config_file.exists():
            self.load_from_file()
            
        # Override with environment variables
        self.load_from_env()
        
    def _load_env_file(self) -> None:
        """Load environment variables from .env file."""
        if not self._env_loaded:
            # Look for .env in current directory and parent directories
            current_dir = Path.cwd()
            for parent in [current_dir] + list(current_dir.parents):
                env_file = parent / ".env"
                if env_file.exists():
                    load_dotenv(env_file)
                    logger.debug("Loaded .env file", path=str(env_file))
                    break
            self._env_loaded = True
        
    def load_from_file(self) -> None:
        """Load settings from configuration file."""
        if not self.config_file or not self.config_file.exists():
            return
            
        try:
            with self._lock:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    
                # Update system prompts
                if "system_prompts" in config:
                    prompts_config = config["system_prompts"]
                    self.system_prompts.default = prompts_config.get("default", self.system_prompts.default)
                    
                # Update audio settings
                if "audio" in config:
                    audio_config = config["audio"]
                    for key, value in audio_config.items():
                        if hasattr(self.audio, key):
                            setattr(self.audio, key, value)
                            
                # Update provider settings
                if "providers" in config:
                    providers_config = config["providers"]
                    for key, value in providers_config.items():
                        if hasattr(self.providers, key):
                            setattr(self.providers, key, value)
                            
                # Update timeout settings
                if "timeouts" in config:
                    timeouts_config = config["timeouts"]
                    for key, value in timeouts_config.items():
                        if hasattr(self.timeouts, key):
                            setattr(self.timeouts, key, value)
                            
                # Update retry settings
                if "retries" in config:
                    retries_config = config["retries"]
                    for key, value in retries_config.items():
                        if hasattr(self.retries, key):
                            setattr(self.retries, key, value)
                            
                # Update metrics settings
                if "metrics" in config:
                    metrics_config = config["metrics"]
                    for key, value in metrics_config.items():
                        if hasattr(self.metrics, key):
                            setattr(self.metrics, key, value)
                            
                # Update logging settings
                if "logging" in config:
                    logging_config = config["logging"]
                    for key, value in logging_config.items():
                        if hasattr(self.logging, key):
                            setattr(self.logging, key, value)
                    
                logger.info("Loaded settings from file", file=str(self.config_file))
                
        except Exception as e:
            logger.error("Failed to load settings from file", 
                        file=str(self.config_file),
                        error=str(e))
        
    def load_from_env(self) -> None:
        """Load settings from environment variables."""
        with self._lock:
            # AI Provider selection
            self.ai_provider = os.getenv("AI_PROVIDER", "claude")
            self.tts_provider = os.getenv("TTS_PROVIDER", "elevenlabs")
            
            # System prompts
            if os.getenv("SYSTEM_PROMPT_DEFAULT"):
                self.system_prompts.default = os.getenv("SYSTEM_PROMPT_DEFAULT")
            
            # Audio settings
            if os.getenv("AUDIO_SAMPLE_RATE"):
                self.audio.sample_rate = int(os.getenv("AUDIO_SAMPLE_RATE"))
            if os.getenv("AUDIO_CHANNELS"):
                self.audio.channels = int(os.getenv("AUDIO_CHANNELS"))
            if os.getenv("AUDIO_CHUNK_SIZE"):
                self.audio.chunk_size = int(os.getenv("AUDIO_CHUNK_SIZE"))
                
            # Provider-specific overrides
            if os.getenv("WHISPERKIT_MODEL"):
                self.providers.whisperkit_model = os.getenv("WHISPERKIT_MODEL")
            if os.getenv("WHISPERKIT_COMPUTE_UNITS"):
                self.providers.whisperkit_compute_units = os.getenv("WHISPERKIT_COMPUTE_UNITS")
            if os.getenv("WHISPERKIT_VAD_ENABLED"):
                self.providers.whisperkit_vad_enabled = os.getenv("WHISPERKIT_VAD_ENABLED").lower() == "true"
                
            if os.getenv("CLAUDE_OUTPUT_FORMAT"):
                self.providers.claude_output_format = os.getenv("CLAUDE_OUTPUT_FORMAT")
                
            if os.getenv("GEMINI_MODEL"):
                self.providers.gemini_model = os.getenv("GEMINI_MODEL")
            if os.getenv("GEMINI_TEMPERATURE"):
                self.providers.gemini_temperature = float(os.getenv("GEMINI_TEMPERATURE"))
            if os.getenv("GEMINI_MAX_TOKENS"):
                self.providers.gemini_max_tokens = int(os.getenv("GEMINI_MAX_TOKENS"))
                
            if os.getenv("ELEVENLABS_VOICE_ID"):
                self.providers.elevenlabs_voice_id = os.getenv("ELEVENLABS_VOICE_ID")
            if os.getenv("ELEVENLABS_MODEL_ID"):
                self.providers.elevenlabs_model_id = os.getenv("ELEVENLABS_MODEL_ID")
            if os.getenv("ELEVENLABS_OUTPUT_FORMAT"):
                self.providers.elevenlabs_output_format = os.getenv("ELEVENLABS_OUTPUT_FORMAT")
                
            # Timeout overrides
            if os.getenv("AI_RESPONSE_TIMEOUT"):
                self.timeouts.ai_response_timeout = int(os.getenv("AI_RESPONSE_TIMEOUT"))
            if os.getenv("TTS_GENERATION_TIMEOUT"):
                self.timeouts.tts_generation_timeout = int(os.getenv("TTS_GENERATION_TIMEOUT"))
            if os.getenv("WHISPERKIT_RESTART_TIMEOUT"):
                self.timeouts.whisperkit_restart_timeout = int(os.getenv("WHISPERKIT_RESTART_TIMEOUT"))
                
            # Retry settings
            if os.getenv("MAX_RETRIES"):
                self.retries.max_retries = int(os.getenv("MAX_RETRIES"))
            if os.getenv("INITIAL_BACKOFF"):
                self.retries.initial_backoff = float(os.getenv("INITIAL_BACKOFF"))
                
            # Metrics settings
            if os.getenv("METRICS_ENABLED"):
                self.metrics.enabled = os.getenv("METRICS_ENABLED").lower() == "true"
            if os.getenv("METRICS_COLLECTION_INTERVAL_MS"):
                self.metrics.collection_interval_ms = int(os.getenv("METRICS_COLLECTION_INTERVAL_MS"))
                
            # Logging settings
            if os.getenv("LOG_LEVEL"):
                self.logging.level = os.getenv("LOG_LEVEL")
            if os.getenv("LOG_FORMAT"):
                self.logging.format = os.getenv("LOG_FORMAT")
            if os.getenv("LOG_FILE_ENABLED"):
                self.logging.file_enabled = os.getenv("LOG_FILE_ENABLED").lower() == "true"
            
    def save_to_file(self, file_path: Optional[Union[str, Path]] = None) -> None:
        """Save current settings to file."""
        save_path = Path(file_path) if file_path else self.config_file
        if not save_path:
            raise ValueError("No file path provided")
            
        try:
            with self._lock:
                config = {
                    "system_prompts": {
                        "default": self.system_prompts.default
                    },
                    "audio": {
                        "sample_rate": self.audio.sample_rate,
                        "channels": self.audio.channels,
                        "chunk_size": self.audio.chunk_size,
                        "format": self.audio.format
                    },
                    "providers": {
                        "whisperkit_model": self.providers.whisperkit_model,
                        "whisperkit_compute_units": self.providers.whisperkit_compute_units,
                        "whisperkit_vad_enabled": self.providers.whisperkit_vad_enabled,
                        "claude_output_format": self.providers.claude_output_format,
                        "gemini_model": self.providers.gemini_model,
                        "gemini_temperature": self.providers.gemini_temperature,
                        "gemini_max_tokens": self.providers.gemini_max_tokens,
                        "elevenlabs_voice_id": self.providers.elevenlabs_voice_id,
                        "elevenlabs_model_id": self.providers.elevenlabs_model_id,
                        "elevenlabs_output_format": self.providers.elevenlabs_output_format
                    },
                    "timeouts": {
                        "ai_response_timeout": self.timeouts.ai_response_timeout,
                        "tts_generation_timeout": self.timeouts.tts_generation_timeout,
                        "whisperkit_restart_timeout": self.timeouts.whisperkit_restart_timeout
                    },
                    "retries": {
                        "max_retries": self.retries.max_retries,
                        "initial_backoff": self.retries.initial_backoff,
                        "backoff_multiplier": self.retries.backoff_multiplier,
                        "max_backoff": self.retries.max_backoff
                    },
                    "metrics": {
                        "enabled": self.metrics.enabled,
                        "collection_interval_ms": self.metrics.collection_interval_ms,
                        "max_pending_metrics": self.metrics.max_pending_metrics,
                        "cleanup_interval_days": self.metrics.cleanup_interval_days
                    },
                    "logging": {
                        "level": self.logging.level,
                        "format": self.logging.format,
                        "file_enabled": self.logging.file_enabled,
                        "file_rotation_mb": self.logging.file_rotation_mb,
                        "file_backup_count": self.logging.file_backup_count,
                        "session_logs": self.logging.session_logs
                    }
                }
                
                # Ensure parent directory exists
                save_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(save_path, 'w') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                    
                logger.info("Saved settings to file", file=str(save_path))
                
        except Exception as e:
            logger.error("Failed to save settings to file", 
                        file=str(save_path), error=str(e))
            raise
        
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
            
    def reload(self) -> None:
        """Reload settings from file and environment."""
        with self._lock:
            if self.config_file and self.config_file.exists():
                self.load_from_file()
            self.load_from_env()
            logger.info("Settings reloaded")
            
    def validate(self) -> list[str]:
        """Validate current settings and return list of issues."""
        issues = []
        
        # Validate audio settings
        if self.audio.sample_rate not in [8000, 16000, 44100, 48000]:
            issues.append(f"Invalid sample rate: {self.audio.sample_rate}")
        if self.audio.channels not in [1, 2]:
            issues.append(f"Invalid channels: {self.audio.channels}")
            
        # Validate timeout settings
        if self.timeouts.ai_response_timeout <= 0:
            issues.append(f"Invalid AI response timeout: {self.timeouts.ai_response_timeout}")
        if self.timeouts.tts_generation_timeout <= 0:
            issues.append(f"Invalid TTS timeout: {self.timeouts.tts_generation_timeout}")
            
        # Validate retry settings
        if self.retries.max_retries < 0:
            issues.append(f"Invalid max retries: {self.retries.max_retries}")
        if self.retries.initial_backoff <= 0:
            issues.append(f"Invalid initial backoff: {self.retries.initial_backoff}")
            
        # Validate provider settings
        if self.ai_provider not in ["claude", "gemini"]:
            issues.append(f"Unknown AI provider: {self.ai_provider}")
        if self.tts_provider not in ["elevenlabs"]:
            issues.append(f"Unknown TTS provider: {self.tts_provider}")
            
        return issues
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary for serialization."""
        return {
            "ai_provider": self.ai_provider,
            "tts_provider": self.tts_provider,
            "system_prompts": {
                "default": self.system_prompts.default
            },
            "audio": {
                "sample_rate": self.audio.sample_rate,
                "channels": self.audio.channels,
                "chunk_size": self.audio.chunk_size,
                "format": self.audio.format
            },
            "providers": {
                "whisperkit_model": self.providers.whisperkit_model,
                "whisperkit_compute_units": self.providers.whisperkit_compute_units,
                "whisperkit_vad_enabled": self.providers.whisperkit_vad_enabled,
                "claude_output_format": self.providers.claude_output_format,
                "gemini_model": self.providers.gemini_model,
                "gemini_temperature": self.providers.gemini_temperature,
                "gemini_max_tokens": self.providers.gemini_max_tokens,
                "elevenlabs_voice_id": self.providers.elevenlabs_voice_id,
                "elevenlabs_model_id": self.providers.elevenlabs_model_id,
                "elevenlabs_output_format": self.providers.elevenlabs_output_format
            },
            "timeouts": {
                "ai_response_timeout": self.timeouts.ai_response_timeout,
                "tts_generation_timeout": self.timeouts.tts_generation_timeout,
                "whisperkit_restart_timeout": self.timeouts.whisperkit_restart_timeout
            },
            "retries": {
                "max_retries": self.retries.max_retries,
                "initial_backoff": self.retries.initial_backoff,
                "backoff_multiplier": self.retries.backoff_multiplier,
                "max_backoff": self.retries.max_backoff
            },
            "metrics": {
                "enabled": self.metrics.enabled,
                "collection_interval_ms": self.metrics.collection_interval_ms,
                "max_pending_metrics": self.metrics.max_pending_metrics,
                "cleanup_interval_days": self.metrics.cleanup_interval_days
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "file_enabled": self.logging.file_enabled,
                "file_rotation_mb": self.logging.file_rotation_mb,
                "file_backup_count": self.logging.file_backup_count,
                "session_logs": self.logging.session_logs
            }
        }


# Global settings instance
settings = Settings()