"""
Hearth Core - Providers

Modular provider system for different AI models.
Makes adding new providers trivial.
"""

from typing import Dict, Any

from .base import BaseProvider, ProviderResponse
from .xai import XAIProvider
from .claude_cli import ClaudeCLIProvider
from .openai import OpenAIProvider
from .gemini import GeminiProvider


# Registry of available providers
PROVIDERS = {
    "xai": XAIProvider,
    "claude-cli": ClaudeCLIProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
}


def create_provider(config: Dict[str, Any]) -> BaseProvider:
    """
    Factory function to create a provider from config.

    Args:
        config: Provider configuration from hearth.yaml, e.g.:
            {
                "provider": "xai",
                "model": "grok-3",
                "api_key_env": "XAI_API_KEY",
                "max_tokens": 2048,
                "temperature": 0.7
            }

    Returns:
        Initialized provider instance

    Raises:
        ValueError: If provider type is unknown
    """
    provider_type = config.get("provider")

    if not provider_type:
        raise ValueError("Provider config missing 'provider' field")

    if provider_type not in PROVIDERS:
        available = ", ".join(PROVIDERS.keys())
        raise ValueError(
            f"Unknown provider: {provider_type}. "
            f"Available providers: {available}"
        )

    provider_class = PROVIDERS[provider_type]
    return provider_class(config)


def register_provider(name: str, provider_class: type):
    """
    Register a custom provider.

    This allows external plugins to add new providers:

    ```python
    from hearth.core.providers import register_provider, BaseProvider

    class MyCustomProvider(BaseProvider):
        # ... implementation ...

    register_provider("my-custom", MyCustomProvider)
    ```

    Args:
        name: Provider name (used in config.yaml)
        provider_class: Provider class (must inherit from BaseProvider)
    """
    if not issubclass(provider_class, BaseProvider):
        raise TypeError(f"{provider_class} must inherit from BaseProvider")

    PROVIDERS[name] = provider_class


__all__ = [
    "BaseProvider",
    "ProviderResponse",
    "XAIProvider",
    "ClaudeCLIProvider",
    "OpenAIProvider",
    "GeminiProvider",
    "create_provider",
    "register_provider",
    "PROVIDERS",
]
