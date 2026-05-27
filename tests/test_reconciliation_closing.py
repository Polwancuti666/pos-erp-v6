from decimal import Decimal

from pos_erp.reconciliation import (
    ClosingDecision,
    ClosingStatus,
    ReconciliationPolicy,
    evaluate_shift_closing,
)


def test_variance_within_dual_threshold_allows_shift_closing():
    decision = evaluate_shift_closing(
        operational_sales=Decimal("5000000.00"),
        counted_cash=Decimal("4950000.00"),
        pending_queued_transactions=0,
        policy=ReconciliationPolicy(),
    )

    assert decision.status is ClosingStatus.ALLOWED
    assert decision.variance_amount == Decimal("50000.00")
    assert decision.variance_percent == Decimal("1.00")
    assert decision.alert_roles == ()


def test_variance_amount_above_100000_blocks_shift_closing_and_alerts_owner_accounting():
    decision = evaluate_shift_closing(
        operational_sales=Decimal("5000000.00"),
        counted_cash=Decimal("4850000.00"),
        pending_queued_transactions=0,
        policy=ReconciliationPolicy(),
    )

    assert decision.status is ClosingStatus.BLOCKED
    assert decision.reason_code == "VARIANCE_ABOVE_THRESHOLD"
    assert decision.variance_amount == Decimal("150000.00")
    assert decision.variance_percent == Decimal("3.00")
    assert decision.alert_roles == ("Accounting Lead", "Owner")


def test_variance_percent_above_5_blocks_even_when_amount_is_below_100000():
    decision = evaluate_shift_closing(
        operational_sales=Decimal("1000000.00"),
        counted_cash=Decimal("940000.00"),
        pending_queued_transactions=0,
        policy=ReconciliationPolicy(),
    )

    assert decision.status is ClosingStatus.BLOCKED
    assert decision.reason_code == "VARIANCE_ABOVE_THRESHOLD"
    assert decision.variance_amount == Decimal("60000.00")
    assert decision.variance_percent == Decimal("6.00")
    assert decision.alert_roles == ("Accounting Lead", "Owner")


def test_exact_threshold_values_do_not_trigger_alert_or_block():
    decision = evaluate_shift_closing(
        operational_sales=Decimal("2000000.00"),
        counted_cash=Decimal("1900000.00"),
        pending_queued_transactions=0,
        policy=ReconciliationPolicy(),
    )

    assert decision.status is ClosingStatus.ALLOWED
    assert decision.variance_amount == Decimal("100000.00")
    assert decision.variance_percent == Decimal("5.00")
    assert decision.alert_roles == ()


def test_pending_queued_transactions_require_acknowledgement_before_closing():
    decision = evaluate_shift_closing(
        operational_sales=Decimal("5000000.00"),
        counted_cash=Decimal("5000000.00"),
        pending_queued_transactions=2,
        pending_acknowledged=False,
        policy=ReconciliationPolicy(),
    )

    assert decision.status is ClosingStatus.ACK_REQUIRED
    assert decision.reason_code == "PENDING_QUEUE_ACK_REQUIRED"
    assert decision.required_acknowledgement_roles == ("Branch Manager", "IT Admin")


def test_pending_queued_transactions_can_close_after_manager_it_acknowledgement_when_variance_ok():
    decision = evaluate_shift_closing(
        operational_sales=Decimal("5000000.00"),
        counted_cash=Decimal("5000000.00"),
        pending_queued_transactions=2,
        pending_acknowledged=True,
        policy=ReconciliationPolicy(),
    )

    assert decision.status is ClosingStatus.ALLOWED
    assert decision.reason_code is None
