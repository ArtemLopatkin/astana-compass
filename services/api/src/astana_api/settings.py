"""Server-side configuration. Secrets never appear in repr or API responses."""
from dataclasses import dataclass, field
import os


@dataclass(frozen=True)
class Settings:
    mode: str = "fixture"
    repository_factory: str = "astana_city_data:create_repository"
    retriever_factory: str = "astana_retrieval:create_retriever"
    context_factory: str = "astana_city_context:create_context"
    cors_origins: tuple[str, ...] = ("http://localhost:3000",)
    request_timeout_seconds: float = 30
    max_body_bytes: int = 32768
    max_concurrent_requests: int = 16
    feedback_capacity: int = 500
    llm_provider: str = "none"
    llm_model: str = ""
    llm_api_key: str = field(default="", repr=False)

    def __post_init__(self):
        if self.mode not in {"fixture", "live"}:
            raise ValueError("ASTANA_MODE must be fixture or live")
        if self.llm_provider not in {"none", "openai", "nvidia"}:
            raise ValueError("LLM_PROVIDER must be none, openai or nvidia")
        if self.llm_provider != "none" and not (self.llm_model and self.llm_api_key):
            raise ValueError("Configured LLM requires model and server-side API key")
        if not 1 <= self.request_timeout_seconds <= 120:
            raise ValueError("Request timeout must be between 1 and 120 seconds")
        if not 1024 <= self.max_body_bytes <= 262144:
            raise ValueError("Body limit must be between 1024 and 262144 bytes")
        if not 1 <= self.max_concurrent_requests <= 128 or self.feedback_capacity < 1:
            raise ValueError("Invalid capacity")
        if "*" in self.cors_origins:
            raise ValueError("Use explicit CORS origins")

    @classmethod
    def from_env(cls):
        provider = os.getenv("LLM_PROVIDER", "none") or "none"
        provider_key = {"openai": "OPENAI_API_KEY", "nvidia": "NVIDIA_API_KEY"}.get(provider, "LLM_API_KEY")
        return cls(
            mode=os.getenv("ASTANA_MODE", "fixture"),
            repository_factory=os.getenv("ASTANA_REPOSITORY_FACTORY", cls.repository_factory),
            retriever_factory=os.getenv("ASTANA_RETRIEVER_FACTORY", cls.retriever_factory),
            context_factory=os.getenv("ASTANA_CONTEXT_FACTORY", cls.context_factory),
            cors_origins=tuple(x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if x.strip()),
            request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")),
            llm_provider=provider, llm_model=os.getenv("LLM_MODEL", ""),
            llm_api_key=os.getenv(provider_key, "") or os.getenv("LLM_API_KEY", ""),
        )
