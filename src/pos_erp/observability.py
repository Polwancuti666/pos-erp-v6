
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"

@dataclass(frozen=True)
class HealthCheckResult:
    status: HealthStatus
    failed_components: tuple[str, ...]

def health_check(*, database_ok: bool, outbox_queue_ok: bool, erp_adapter_ok: bool, payment_adapter_ok: bool) -> HealthCheckResult:
    components = {"database": database_ok, "outbox_queue": outbox_queue_ok, "erp_adapter": erp_adapter_ok, "payment_adapter": payment_adapter_ok}
    failed = tuple(name for name, ok in components.items() if not ok)
    return HealthCheckResult(HealthStatus.HEALTHY if not failed else HealthStatus.UNHEALTHY, failed)

class MetricsRegistry:
    def __init__(self):
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, int] = {}
    def increment(self, name: str, *, amount: int = 1) -> None:
        self._counters[name] = self._counters.get(name, 0) + amount
    def gauge(self, name: str, value: int) -> None:
        self._gauges[name] = value
    def snapshot(self) -> dict[str, dict[str, int]]:
        return {"counters": dict(self._counters), "gauges": dict(self._gauges)}
