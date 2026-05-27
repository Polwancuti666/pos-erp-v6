
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class DeploymentManifest:
    service_name: str
    image: str
    replicas: int
    database_secret_name: str
    encryption_secret_name: str
    monitoring_enabled: bool

@dataclass(frozen=True)
class ManifestValidation:
    ready: bool
    missing_requirements: tuple[str, ...]

def validate_manifest(manifest: DeploymentManifest) -> ManifestValidation:
    missing = []
    if not manifest.image:
        missing.append("IMAGE")
    if manifest.replicas < 1:
        missing.append("REPLICAS")
    if not manifest.database_secret_name:
        missing.append("DATABASE_SECRET")
    if not manifest.encryption_secret_name:
        missing.append("ENCRYPTION_SECRET")
    if not manifest.monitoring_enabled:
        missing.append("MONITORING")
    return ManifestValidation(not missing, tuple(missing))
