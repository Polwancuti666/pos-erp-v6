
from pos_erp.migrations import Migration, MigrationRunner


def test_migration_runner_applies_pending_migrations_in_order():
    runner = MigrationRunner([
        Migration("001_init", "CREATE TABLE transactions"),
        Migration("002_audit", "CREATE TABLE audit_log"),
    ])
    result = runner.apply(applied_versions=())
    assert result.applied_versions == ("001_init", "002_audit")
    assert result.sql_statements == ("CREATE TABLE transactions", "CREATE TABLE audit_log")


def test_migration_runner_skips_already_applied_versions():
    runner = MigrationRunner([
        Migration("001_init", "CREATE TABLE transactions"),
        Migration("002_audit", "CREATE TABLE audit_log"),
    ])
    result = runner.apply(applied_versions=("001_init",))
    assert result.applied_versions == ("002_audit",)
    assert result.sql_statements == ("CREATE TABLE audit_log",)


def test_migration_runner_rejects_duplicate_versions():
    try:
        MigrationRunner([Migration("001", "A"), Migration("001", "B")])
    except ValueError as exc:
        assert "duplicate" in str(exc).lower()
    else:
        raise AssertionError("Expected duplicate migration versions to be rejected")
