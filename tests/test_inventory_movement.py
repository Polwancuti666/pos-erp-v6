from decimal import Decimal

import pytest

from pos_erp.inventory import (
    InventoryPolicy,
    MovementReason,
    MovementType,
    NegativeStockBlocked,
    StockLedger,
    consume_service_inventory,
    record_stock_adjustment,
)


def test_service_completion_consumes_mapped_bom_items_with_audit_context():
    ledger = StockLedger(
        branch_code="JKT01",
        balances={"shampoo-ml": Decimal("1000.00"), "cream-g": Decimal("500.00")},
    )

    movements = consume_service_inventory(
        ledger,
        service_id="HAIRSPA-001",
        transaction_id="TRM-001",
        bom_items={"shampoo-ml": Decimal("50.00"), "cream-g": Decimal("20.00")},
        actor_id="therapist-1",
        device_id="POSA",
        occurred_at="2026-05-26T10:00:00+07:00",
    )

    assert ledger.balance_of("shampoo-ml") == Decimal("950.00")
    assert ledger.balance_of("cream-g") == Decimal("480.00")
    assert [movement.item_id for movement in movements] == ["shampoo-ml", "cream-g"]
    assert all(movement.movement_type is MovementType.OUT for movement in movements)
    assert all(movement.reason is MovementReason.SERVICE_CONSUMPTION for movement in movements)
    assert movements[0].reference_id == "TRM-001"
    assert movements[0].branch_code == "JKT01"
    assert movements[0].actor_id == "therapist-1"
    assert movements[0].device_id == "POSA"


def test_negative_stock_is_blocked_by_default_and_balance_is_not_changed():
    ledger = StockLedger(
        branch_code="JKT01",
        balances={"serum-ml": Decimal("10.00")},
    )

    with pytest.raises(NegativeStockBlocked) as exc_info:
        consume_service_inventory(
            ledger,
            service_id="FACIAL-001",
            transaction_id="TRM-002",
            bom_items={"serum-ml": Decimal("12.00")},
            actor_id="therapist-2",
            device_id="POSA",
            occurred_at="2026-05-26T11:00:00+07:00",
        )

    assert ledger.balance_of("serum-ml") == Decimal("10.00")
    assert exc_info.value.item_id == "serum-ml"
    assert exc_info.value.available == Decimal("10.00")
    assert exc_info.value.required == Decimal("12.00")


def test_negative_stock_can_escalate_instead_of_blocking_when_policy_allows():
    ledger = StockLedger(
        branch_code="JKT01",
        balances={"toner-ml": Decimal("5.00")},
        policy=InventoryPolicy(allow_negative_with_escalation=True),
    )

    movements = consume_service_inventory(
        ledger,
        service_id="FACIAL-002",
        transaction_id="TRM-003",
        bom_items={"toner-ml": Decimal("8.00")},
        actor_id="therapist-3",
        device_id="POSB",
        occurred_at="2026-05-26T12:00:00+07:00",
    )

    assert ledger.balance_of("toner-ml") == Decimal("-3.00")
    assert movements[0].requires_escalation is True
    assert movements[0].escalation_reason == "NEGATIVE_STOCK_ALLOWED_BY_POLICY"


def test_stock_adjustment_records_in_or_out_movement_with_reason_and_audit():
    ledger = StockLedger(
        branch_code="BDG01",
        balances={"mask-pcs": Decimal("20.00")},
    )

    movement = record_stock_adjustment(
        ledger,
        item_id="mask-pcs",
        quantity=Decimal("5.00"),
        movement_type=MovementType.IN,
        reason=MovementReason.MANUAL_ADJUSTMENT,
        reference_id="ADJ-001",
        actor_id="inventory-admin-1",
        device_id="BACKOFFICE",
        occurred_at="2026-05-26T13:00:00+07:00",
    )

    assert ledger.balance_of("mask-pcs") == Decimal("25.00")
    assert movement.quantity == Decimal("5.00")
    assert movement.movement_type is MovementType.IN
    assert movement.reason is MovementReason.MANUAL_ADJUSTMENT
    assert movement.branch_code == "BDG01"
    assert movement.actor_id == "inventory-admin-1"


def test_offline_stock_movement_uses_local_temporary_reference_and_pending_sync():
    ledger = StockLedger(
        branch_code="SBY01",
        balances={"oil-ml": Decimal("100.00")},
    )

    movement = record_stock_adjustment(
        ledger,
        item_id="oil-ml",
        quantity=Decimal("10.00"),
        movement_type=MovementType.OUT,
        reason=MovementReason.DAMAGED_STOCK,
        reference_id="ADJ-OFFLINE-001",
        actor_id="inventory-admin-2",
        device_id="POSC",
        occurred_at="2026-05-26T14:00:00+07:00",
        online=False,
        local_sequence=9,
    )

    assert ledger.balance_of("oil-ml") == Decimal("90.00")
    assert movement.local_temp_id == "TMP-STK-SBY01-POSC-20260526-000009"
    assert movement.pending_sync is True
    assert movement.final_document_id is None
