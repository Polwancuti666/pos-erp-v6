from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class MovementType(str, Enum):
    IN = "IN"
    OUT = "OUT"


class MovementReason(str, Enum):
    SERVICE_CONSUMPTION = "SERVICE_CONSUMPTION"
    MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT"
    DAMAGED_STOCK = "DAMAGED_STOCK"


@dataclass(frozen=True)
class InventoryPolicy:
    allow_negative_with_escalation: bool = False


@dataclass(frozen=True)
class StockMovement:
    item_id: str
    quantity: Decimal
    movement_type: MovementType
    reason: MovementReason
    reference_id: str
    branch_code: str
    actor_id: str
    device_id: str
    occurred_at: str
    pending_sync: bool = False
    local_temp_id: str | None = None
    final_document_id: str | None = None
    requires_escalation: bool = False
    escalation_reason: str | None = None


class NegativeStockBlocked(Exception):
    def __init__(self, *, item_id: str, available: Decimal, required: Decimal):
        super().__init__(
            f"Insufficient stock for {item_id}: available {available}, required {required}."
        )
        self.item_id = item_id
        self.available = available
        self.required = required


@dataclass
class StockLedger:
    branch_code: str
    balances: dict[str, Decimal] = field(default_factory=dict)
    policy: InventoryPolicy = field(default_factory=InventoryPolicy)

    def balance_of(self, item_id: str) -> Decimal:
        return self.balances.get(item_id, Decimal("0.00"))

    def apply(self, movement: StockMovement) -> None:
        current = self.balance_of(movement.item_id)
        if movement.movement_type is MovementType.IN:
            self.balances[movement.item_id] = current + movement.quantity
            return

        new_balance = current - movement.quantity
        if new_balance < Decimal("0.00") and not self.policy.allow_negative_with_escalation:
            raise NegativeStockBlocked(
                item_id=movement.item_id,
                available=current,
                required=movement.quantity,
            )
        self.balances[movement.item_id] = new_balance


def consume_service_inventory(
    ledger: StockLedger,
    *,
    service_id: str,
    transaction_id: str,
    bom_items: dict[str, Decimal],
    actor_id: str,
    device_id: str,
    occurred_at: str,
) -> list[StockMovement]:
    _ensure_service_can_be_consumed(ledger, bom_items)

    movements: list[StockMovement] = []
    for item_id, quantity in bom_items.items():
        movement = StockMovement(
            item_id=item_id,
            quantity=quantity,
            movement_type=MovementType.OUT,
            reason=MovementReason.SERVICE_CONSUMPTION,
            reference_id=transaction_id,
            branch_code=ledger.branch_code,
            actor_id=actor_id,
            device_id=device_id,
            occurred_at=occurred_at,
            requires_escalation=_will_go_negative(ledger, item_id, quantity),
            escalation_reason=(
                "NEGATIVE_STOCK_ALLOWED_BY_POLICY"
                if _will_go_negative(ledger, item_id, quantity)
                else None
            ),
        )
        ledger.apply(movement)
        movements.append(movement)

    return movements


def record_stock_adjustment(
    ledger: StockLedger,
    *,
    item_id: str,
    quantity: Decimal,
    movement_type: MovementType,
    reason: MovementReason,
    reference_id: str,
    actor_id: str,
    device_id: str,
    occurred_at: str,
    online: bool = True,
    local_sequence: int | None = None,
) -> StockMovement:
    movement = StockMovement(
        item_id=item_id,
        quantity=quantity,
        movement_type=movement_type,
        reason=reason,
        reference_id=reference_id,
        branch_code=ledger.branch_code,
        actor_id=actor_id,
        device_id=device_id,
        occurred_at=occurred_at,
        pending_sync=not online,
        local_temp_id=(
            _build_stock_temp_id(
                branch_code=ledger.branch_code,
                device_id=device_id,
                occurred_at=occurred_at,
                local_sequence=local_sequence,
            )
            if not online
            else None
        ),
    )
    ledger.apply(movement)
    return movement


def _ensure_service_can_be_consumed(
    ledger: StockLedger,
    bom_items: dict[str, Decimal],
) -> None:
    if ledger.policy.allow_negative_with_escalation:
        return

    for item_id, quantity in bom_items.items():
        available = ledger.balance_of(item_id)
        if available - quantity < Decimal("0.00"):
            raise NegativeStockBlocked(
                item_id=item_id,
                available=available,
                required=quantity,
            )


def _will_go_negative(ledger: StockLedger, item_id: str, quantity: Decimal) -> bool:
    return ledger.balance_of(item_id) - quantity < Decimal("0.00")


def _build_stock_temp_id(
    *,
    branch_code: str,
    device_id: str,
    occurred_at: str,
    local_sequence: int | None,
) -> str:
    if local_sequence is None:
        raise ValueError("local_sequence is required for offline stock movement")
    business_date = occurred_at[:10].replace("-", "")
    return f"TMP-STK-{branch_code}-{device_id}-{business_date}-{local_sequence:06d}"
