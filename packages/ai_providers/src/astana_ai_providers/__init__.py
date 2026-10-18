"""Optional hosted explanation providers; model choice belongs to server config."""

from .generators import HostedExplanationGenerator, ProviderError, create_generator

__all__ = ["HostedExplanationGenerator", "ProviderError", "create_generator"]
