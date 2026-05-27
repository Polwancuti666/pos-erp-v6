
from pos_erp.observability import HealthStatus, MetricsRegistry, health_check


def test_health_check_reports_unhealthy_when_queue_or_adapter_down():
    status = health_check(database_ok=True, outbox_queue_ok=False, erp_adapter_ok=True, payment_adapter_ok=False)
    assert status.status is HealthStatus.UNHEALTHY
    assert "outbox_queue" in status.failed_components
    assert "payment_adapter" in status.failed_components


def test_health_check_reports_healthy_when_all_components_ok():
    assert health_check(database_ok=True, outbox_queue_ok=True, erp_adapter_ok=True, payment_adapter_ok=True).status is HealthStatus.HEALTHY


def test_metrics_registry_counts_events_and_sets_gauges():
    metrics = MetricsRegistry()
    metrics.increment("sync_attempts_total")
    metrics.increment("sync_attempts_total", amount=2)
    metrics.gauge("pending_sync_count", 7)
    assert metrics.snapshot()["counters"]["sync_attempts_total"] == 3
    assert metrics.snapshot()["gauges"]["pending_sync_count"] == 7
