from pathlib import Path


def test_dockerfile_uses_python_and_uvicorn_fastapi_entrypoint():
    content = Path("Dockerfile").read_text()
    assert "FROM python:3.11-slim" in content
    assert "uvicorn" in content
    assert "pos_erp.fastapi_app:app" in content


def test_docker_compose_defines_app_postgres_and_named_volume():
    content = Path("docker-compose.yml").read_text()
    assert "postgres:16-alpine" in content
    assert "pos-erp-api" in content
    assert "pos_erp_postgres_data" in content
    assert "5432:5432" in content


def test_env_example_documents_required_provider_secrets_without_real_values():
    content = Path(".env.example").read_text()
    assert "POSTGRES_PASSWORD=change-me" in content
    assert "MIDTRANS_SERVER_KEY=change-me" in content
    assert "BCA_CLIENT_SECRET=change-me" in content
    assert "real-secret" not in content
