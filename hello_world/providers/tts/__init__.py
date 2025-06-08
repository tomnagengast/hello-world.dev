"""Text-to-Speech providers."""


def register_providers():
    """Register all TTS providers."""
    # Import at function level to avoid circular imports
    from ..registry import registry
    from ...config.settings import settings
    from .elevenlabs import ElevenLabsProvider

    def get_elevenlabs_config():
        config = settings.get_provider_config("elevenlabs")
        return {
            "voice_id": config.get("voice_id", "pNInz6obpgDQGcFmaJgB"),
            "model_id": config.get("model_id", "eleven_flash_v2_5"),
            "output_format": config.get("output_format", "mp3_22050_32"),
            "stability": config.get("stability", 0.5),
            "similarity_boost": config.get("similarity_boost", 0.8),
            "style": config.get("style", 0.0),
            "speed": config.get("speed", 1.0),
            "use_speaker_boost": config.get("use_speaker_boost", True),
        }

    registry.register_tts_provider(
        "elevenlabs", ElevenLabsProvider, get_elevenlabs_config
    )
