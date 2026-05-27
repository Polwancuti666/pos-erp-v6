
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Migration:
    version: str
    sql: str

@dataclass(frozen=True)
class MigrationResult:
    applied_versions: tuple[str, ...]
    sql_statements: tuple[str, ...]

class MigrationRunner:
    def __init__(self, migrations: list[Migration]):
        versions = [m.version for m in migrations]
        if len(versions) != len(set(versions)):
            raise ValueError("duplicate migration version")
        self.migrations = sorted(migrations, key=lambda m: m.version)
    def apply(self, *, applied_versions: tuple[str, ...]) -> MigrationResult:
        applied = set(applied_versions)
        pending = [m for m in self.migrations if m.version not in applied]
        return MigrationResult(tuple(m.version for m in pending), tuple(m.sql for m in pending))
