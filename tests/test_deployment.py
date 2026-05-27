
from pos_erp.deployment import DeploymentManifest, validate_manifest


def test_deployment_manifest_requires_database_secret_encryption_and_monitoring():
    manifest = DeploymentManifest(
        service_name="pos-erp-v6",
        image="pos-erp:v6",
        replicas=2,
        database_secret_name="pos-erp-db",
        encryption_secret_name="pos-erp-encryption",
        monitoring_enabled=True,
    )
    result = validate_manifest(manifest)
    assert result.ready is True
    assert result.missing_requirements == ()


def test_deployment_manifest_reports_missing_production_requirements():
    result = validate_manifest(DeploymentManifest("pos-erp-v6", "", 0, "", "", False))
    assert result.ready is False
    assert "IMAGE" in result.missing_requirements
    assert "REPLICAS" in result.missing_requirements
    assert "DATABASE_SECRET" in result.missing_requirements
    assert "ENCRYPTION_SECRET" in result.missing_requirements
    assert "MONITORING" in result.missing_requirements
