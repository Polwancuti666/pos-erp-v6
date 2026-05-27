from pos_erp.postgresql import PostgreSQLSettings, build_async_database_url, postgres_healthcheck_command


def test_postgresql_settings_builds_sync_and_async_urls_without_exposing_password():
    settings = PostgreSQLSettings(host="db", port=5432, database="pos_erp", user="pos_app", password="secret")
    assert settings.sync_url == "postgresql://pos_app:***@db:5432/pos_erp"
    assert build_async_database_url(settings) == "postgresql+psycopg://pos_app:secret@db:5432/pos_erp"
    assert settings.safe_url == "postgresql://pos_app:***@db:5432/pos_erp"


def test_postgres_healthcheck_uses_pg_isready_for_compose():
    settings = PostgreSQLSettings(host="db", port=5432, database="pos_erp", user="pos_app", password="secret")
    assert postgres_healthcheck_command(settings) == ["CMD-SHELL", "pg_isready -U pos_app -d pos_erp -h db -p 5432"]
