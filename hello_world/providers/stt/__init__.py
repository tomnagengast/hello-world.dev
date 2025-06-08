"""Speech-to-Text providers."""

def register_providers():
    """Register all STT providers."""
    # Import at function level to avoid circular imports
    from ..registry import registry
    from ...config.settings import settings
    from .whisperkit import WhisperKitProvider
    
    def get_whisperkit_config():
        config = settings.get_provider_config("whisperkit")
        # Map settings to WhisperKit init parameters
        return {
            "model": config.get("model", "large-v3_turbo"),
            "vad_enabled": config.get("vad_enabled", True),
            "compute_units": config.get("compute_units", "cpuAndNeuralEngine"),
            "sample_rate": settings.audio.sample_rate,
            "channels": settings.audio.channels
        }
    
    registry.register_stt_provider(
        "whisperkit", 
        WhisperKitProvider,
        get_whisperkit_config
    )