"""AI providers."""


def register_providers():
    """Register all AI providers."""
    # Import at function level to avoid circular imports
    from ..registry import registry
    from ...config.settings import settings
    from .claude import ClaudeProvider
    from .gemini import GeminiProvider

    def get_claude_config():
        config = settings.get_provider_config("claude")
        return {
            "system_prompt": config.get(
                "system_prompt", settings.system_prompts.default
            )
        }

    registry.register_ai_provider("claude", ClaudeProvider, get_claude_config)

    def get_gemini_config():
        config = settings.get_provider_config("gemini")
        return {
            "system_prompt": config.get(
                "system_prompt", settings.system_prompts.default
            )
        }

    registry.register_ai_provider("gemini", GeminiProvider, get_gemini_config)
