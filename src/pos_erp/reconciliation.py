from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum


class ClosingStatus(str, Enum):
    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"
    ACK_REQUIRED = "ACK_REQUIRED"


@dataclass(frozen=True)
class ReconciliationPolicy:
    amount_threshold: Decimal = Decimal("100000.00")
    percent_threshold: Decimal = Decimal("5.00")


@dataclass(frozen=True)
class ClosingDecision:
    status: ClosingStatus
    variance_amount: Decimal
    variance_percent: Decimal
    reason_code: str | None = None
    alert_roles: tuple[str, ...] = ()
    required_acknowledgement_roles: tuple[str, ...] = ()


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _percent(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal("0.00")
    return ((numerator / denominator) * Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def evaluate_shift_closing(
    *,
    operational_sales: Decimal,
    counted_cash: Decimal,
    pending_queued_transactions: int,
    policy: ReconciliationPolicy,
    pending_acknowledged: bool = False,
) -> ClosingDecision:
    variance_amount = _money(abs(operational_sales - counted_cash))
    variance_percent = _percent(variance_amount, operational_sales)

    above_amount = variance_amount > policy.amount_threshold
    above_percent = variance_percent > policy.percent_threshold
    if above_amount or above_percent:
        return ClosingDecision(
            status=ClosingStatus.BLOCKED,
            reason_code="VARIANCE_ABOVE_THRESHOLD",
            variance_amount=variance_amount,
            variance_percent=variance_percent,
            alert_roles=("Accounting Lead", "Owner"),
        )

    if pending_queued_transactions > 0 and not pending_acknowledged:
        return ClosingDecision(
            status=ClosingStatus.ACK_REQUIRED,
            reason_code="PENDING_QUEUE_ACK_REQUIRED",
            variance_amount=variance_amount,
            variance_percent=variance_percent,
            required_acknowledgement_roles=("Branch Manager", "IT Admin"),
        )

    return ClosingDecision(
        status=ClosingStatus.ALLOWED,
        variance_amount=variance_amount,
        variance_percent=variance_percent,
    )
