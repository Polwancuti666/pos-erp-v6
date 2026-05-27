
from __future__ import annotations
from dataclasses import dataclass
from os import environ

@dataclass(frozen=True)
class AppConfig:
    environment: str
    database_url: str
    secret_key: str
    payment_webhook_secret: str | None = None
    erp_base_url: str | None = None

    @property
    def has_placeholder_secret(self) -> bool:
        return self.secret_key == "dev-only-change-me"

    @classmethod
    def _build_database_url(cls, source: dict[str, str]) -> str:
        """Build DATABASE_URL from POS_ERP_DATABASE_URL or individual POSTGRES_* vars."""
        url = source.get("POS_ERP_DATABASE_URL")
        if url:
            return url
        user = source.get("POSTGRES_USER")
        password = source.get("POSTGRES_PASSWORD")
        host = source.get("POSTGRES_HOST", "postgres")
        port = source.get("POSTGRES_PORT", "5432")
        db = source.get("POSTGRES_DB", "pos_erp")
        if user and password:
            return f"postgresql://{user}:{password}@{host}:{port}/{db}"
        return "sqlite:///:memory:"

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "AppConfig":
        source = environ if env is None else env
        return cls(
            environment=source.get("POS_ERP_ENV", "local"),
            database_url=cls._build_database_url(source),
            secret_key=source.get("POS_ERP_SECRET_KEY", "dev-only-change-me"),
            payment_webhook_secret=source.get("POS_ERP_PAYMENT_WEBHOOK_SECRET"),
            erp_base_url=source.get("POS_ERP_ERP_BASE_URL"),
        )
