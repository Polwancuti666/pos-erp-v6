from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class PostgreSQLSettings:
    host: str
    port: int
    database: str
    user: str
    password: str
    @property
    def sync_url(self) -> str:
        return f"postgresql://{self.user}:***@{self.host}:{self.port}/{self.database}"
    @property
    def safe_url(self) -> str:
        return self.sync_url

def build_async_database_url(settings: PostgreSQLSettings) -> str:
    return f"postgresql+psycopg://{settings.user}:{settings.password}@{settings.host}:{settings.port}/{settings.database}"

def postgres_healthcheck_command(settings: PostgreSQLSettings) -> list[str]:
    return ["CMD-SHELL", f"pg_isready -U {settings.user} -d {settings.database} -h {settings.host} -p {settings.port}"]
