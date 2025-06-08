"""Provider registry for dynamic provider loading."""

from typing import Dict, Type, Callable, Any
import structlog

from .stt.base import STTProvider
from .ai.base import AIProvider
from .tts.base import TTSProvider


logger = structlog.get_logger()


class ProviderRegistry:
    """Registry for managing provider implementations."""

    def __init__(self):
        self._stt_providers: Dict[str, Type[STTProvider]] = {}
        self._ai_providers: Dict[str, Type[AIProvider]] = {}
        self._tts_providers: Dict[str, Type[TTSProvider]] = {}
        self._provider_configs: Dict[str, Callable[[], Dict[str, Any]]] = {}

    def register_stt_provider(
        self,
        name: str,
        provider_class: Type[STTProvider],
        config_getter: Callable[[], Dict[str, Any]] = None,
    ) -> None:
        """Register an STT provider."""
        self._stt_providers[name] = provider_class
        if config_getter:
            self._provider_configs[f"stt:{name}"] = config_getter
        logger.info(
            "Registered STT provider", name=name, class_name=provider_class.__name__
        )

    def register_ai_provider(
        self,
        name: str,
        provider_class: Type[AIProvider],
        config_getter: Callable[[], Dict[str, Any]] = None,
    ) -> None:
        """Register an AI provider."""
        self._ai_providers[name] = provider_class
        if config_getter:
            self._provider_configs[f"ai:{name}"] = config_getter
        logger.info(
            "Registered AI provider", name=name, class_name=provider_class.__name__
        )

    def register_tts_provider(
        self,
        name: str,
        provider_class: Type[TTSProvider],
        config_getter: Callable[[], Dict[str, Any]] = None,
    ) -> None:
        """Register a TTS provider."""
        self._tts_providers[name] = provider_class
        if config_getter:
            self._provider_configs[f"tts:{name}"] = config_getter
        logger.info(
            "Registered TTS provider", name=name, class_name=provider_class.__name__
        )

    def get_stt_provider(self, name: str, **kwargs) -> STTProvider:
        """Get an STT provider instance."""
        if name not in self._stt_providers:
            raise ValueError(f"Unknown STT provider: {name}")

        provider_class = self._stt_providers[name]
        config_key = f"stt:{name}"

        # Get provider-specific configuration
        if config_key in self._provider_configs:
            config = self._provider_configs[config_key]()
            kwargs.update(config)

        return provider_class(**kwargs)

    def get_ai_provider(self, name: str, **kwargs) -> AIProvider:
        """Get an AI provider instance."""
        if name not in self._ai_providers:
            raise ValueError(f"Unknown AI provider: {name}")

        provider_class = self._ai_providers[name]
        config_key = f"ai:{name}"

        # Get provider-specific configuration
        if config_key in self._provider_configs:
            config = self._provider_configs[config_key]()
            kwargs.update(config)

        return provider_class(**kwargs)

    def get_tts_provider(self, name: str, **kwargs) -> TTSProvider:
        """Get a TTS provider instance."""
        if name not in self._tts_providers:
            raise ValueError(f"Unknown TTS provider: {name}")

        provider_class = self._tts_providers[name]
        config_key = f"tts:{name}"

        # Get provider-specific configuration
        if config_key in self._provider_configs:
            config = self._provider_configs[config_key]()
            kwargs.update(config)

        return provider_class(**kwargs)

    def list_stt_providers(self) -> list[str]:
        """List available STT providers."""
        return list(self._stt_providers.keys())

    def list_ai_providers(self) -> list[str]:
        """List available AI providers."""
        return list(self._ai_providers.keys())

    def list_tts_providers(self) -> list[str]:
        """List available TTS providers."""
        return list(self._tts_providers.keys())

    def clear(self) -> None:
        """Clear all registered providers."""
        self._stt_providers.clear()
        self._ai_providers.clear()
        self._tts_providers.clear()
        self._provider_configs.clear()


# Global registry instance
registry = ProviderRegistry()
