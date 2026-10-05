from .providers.base import LLMProvider
from ..config import Config


def get_llm_provider() -> LLMProvider:
    provider_name = Config.LLM_PROVIDER

    print(
        f"[PROVIDER_FACTORY] LLM_PROVIDER = {provider_name}",
        flush=True
    )

    if provider_name == "gemini":
        from .providers.gemini import GeminiProvider

        print(
            "[PROVIDER_FACTORY] Using GeminiProvider",
            flush=True
        )

        return GeminiProvider()

    if provider_name == "mock":
        from .providers.mock import MockProvider

        print(
            "[PROVIDER_FACTORY] Using MockProvider",
            flush=True
        )

        return MockProvider()

    raise ValueError(
        f"Unsupported LLM_PROVIDER: {provider_name}"
    )
