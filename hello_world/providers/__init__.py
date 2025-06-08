"""Provider interfaces and implementations for STT, AI, and TTS."""

from .registry import registry

# Defer provider registration to avoid circular imports
def _register_all_providers():
    """Register all provider types."""
    from . import stt, ai, tts
    stt.register_providers()
    ai.register_providers()
    tts.register_providers()

# Register providers after module initialization
_register_all_providers()

__all__ = ['registry']