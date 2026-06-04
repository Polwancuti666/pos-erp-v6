from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class TreatmentStatus(str, Enum):
    OK = "OK"
    REASSIGNMENT_SUGGESTED = "REASSIGNMENT_SUGGESTED"
    WAITLIST_OR_CANCEL = "WAITLIST_OR_CANCEL"


class ConfirmationRequired(Exception):
    pass


@dataclass
class ServiceCatalog:
    prices: dict[str, Decimal]

    def price_for(self, service_id: str) -> Decimal:
        if service_id in self.prices:
            return self.prices[service_id]
        # Fallback: load from database
        try:
            from pos_erp.db import fetch_one
            row = fetch_one("SELECT price FROM treatment WHERE id = %s AND is_active = true", (service_id,))
            if row:
                price = Decimal(str(row["price"]))
                self.prices[service_id] = price  # cache for next time
                return price
        except Exception:
            pass
        raise KeyError(f"service '{service_id}' not found in catalog or database")


@dataclass
class StaffDirectory:
    staff_price_tiers: dict[str, str]
    available_staff: set[str]

    def is_available(self, staff_id: str) -> bool:
        return staff_id in self.available_staff

    def mark_unavailable(self, staff_id: str) -> None:
        self.available_staff.discard(staff_id)

    def same_tier_available_alternative(self, current_staff_id: str) -> str | None:
        current_tier = self.staff_price_tiers[current_staff_id]
        for staff_id in sorted(self.available_staff):
            if staff_id != current_staff_id and self.staff_price_tiers.get(staff_id) == current_tier:
                return staff_id
        return None


@dataclass(frozen=True)
class TreatmentLine:
    line_id: str
    service_id: str
    staff_id: str
    price: Decimal


@dataclass(frozen=True)
class StaffSuggestion:
    status: TreatmentStatus
    suggested_staff_id: str | None = None
    requires_confirmation: bool = False
    options: tuple[str, ...] = ()


class TreatmentCart:
    def __init__(self, *, transaction_id: str) -> None:
        self.transaction_id = transaction_id
        self.lines: list[TreatmentLine] = []
        self._paid = False

    @property
    def total_price(self) -> Decimal:
        return sum((line.price for line in self.lines), Decimal("0.00"))

    def mark_paid(self) -> None:
        self._paid = True

    def _ensure_editable(self) -> None:
        if self._paid:
            raise ValueError("cannot edit treatment after payment")

    def add_service(
        self,
        service_id: str,
        *,
        staff_id: str,
        catalog: ServiceCatalog,
        staff_directory: StaffDirectory,
    ) -> TreatmentLine:
        self._ensure_editable()
        if not staff_directory.is_available(staff_id):
            raise ValueError(f"staff {staff_id} is unavailable")
        line = TreatmentLine(
            line_id=service_id,
            service_id=service_id,
            staff_id=staff_id,
            price=catalog.price_for(service_id),
        )
        self.lines.append(line)
        return line

    def remove_service(self, line_id: str) -> None:
        self._ensure_editable()
        self.lines = [line for line in self.lines if line.line_id != line_id]

    def _find_line(self, line_id: str) -> TreatmentLine:
        for line in self.lines:
            if line.line_id == line_id:
                return line
        raise ValueError(f"unknown treatment line {line_id}")

    def revalidate_staff(self, *, line_id: str, staff_directory: StaffDirectory) -> StaffSuggestion:
        line = self._find_line(line_id)
        if staff_directory.is_available(line.staff_id):
            return StaffSuggestion(status=TreatmentStatus.OK)
        alternative = staff_directory.same_tier_available_alternative(line.staff_id)
        if alternative:
            return StaffSuggestion(
                status=TreatmentStatus.REASSIGNMENT_SUGGESTED,
                suggested_staff_id=alternative,
                requires_confirmation=True,
            )
        return StaffSuggestion(
            status=TreatmentStatus.WAITLIST_OR_CANCEL,
            options=("WAITLIST", "CANCEL"),
        )

    def change_staff(
        self,
        *,
        line_id: str,
        new_staff_id: str,
        staff_directory: StaffDirectory,
        confirmed: bool,
    ) -> None:
        self._ensure_editable()
        if not confirmed:
            raise ConfirmationRequired("staff reassignment requires customer/cashier confirmation")
        if not staff_directory.is_available(new_staff_id):
            raise ValueError(f"staff {new_staff_id} is unavailable")
        replacement: list[TreatmentLine] = []
        found = False
        for line in self.lines:
            if line.line_id == line_id:
                replacement.append(
                    TreatmentLine(
                        line_id=line.line_id,
                        service_id=line.service_id,
                        staff_id=new_staff_id,
                        price=line.price,
                    )
                )
                found = True
            else:
                replacement.append(line)
        if not found:
            raise ValueError(f"unknown treatment line {line_id}")
        self.lines = replacement
