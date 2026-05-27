
from pos_erp.config import AppConfig


def test_default_config_uses_safe_local_values_without_real_secrets():
    cfg = AppConfig.from_env({})
    assert cfg.environment == "local"
    assert cfg.database_url == "sqlite:///:memory:"
    assert cfg.secret_key == "dev-only-change-me"
    assert cfg.has_placeholder_secret is True


def test_config_loads_database_gateway_and_erp_values_from_env():
    cfg = AppConfig.from_env({
        "POS_ERP_ENV": "production",
        "POS_ERP_DATABASE_URL": "postgresql://app:pass@db/pos",
        "POS_ERP_SECRET_KEY": "prod-secret",
        "POS_ERP_PAYMENT_WEBHOOK_SECRET": "pay-secret",
        "POS_ERP_ERP_BASE_URL": "https://erp.example.test",
    })
    assert cfg.environment == "production"
    assert cfg.database_url == "postgresql://app:pass@db/pos"
    assert cfg.payment_webhook_secret == "pay-secret"
    assert cfg.erp_base_url == "https://erp.example.test"
    assert cfg.has_placeholder_secret is False
