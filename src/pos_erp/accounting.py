from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum


class AccountType(str, Enum):
    CASH = "cash"


class JournalStatus(str, Enum):
    POSTED = "POSTED"


@dataclass(frozen=True)
class COAMapping:
    service_revenue: str | None
    cash_account: str | None


@dataclass(frozen=True)
class JournalLine:
    account_code: str
    debit: Decimal = Decimal("0.00")
    credit: Decimal = Decimal("0.00")


@dataclass(frozen=True)
class Journal:
    journal_number: str
    branch_code: str
    transaction_reference: str
    lines: tuple[JournalLine, ...]
    status: JournalStatus

    @property
    def debit_total(self) -> Decimal:
        return sum((line.debit for line in self.lines), Decimal("0.00"))

    @property
    def credit_total(self) -> Decimal:
        return sum((line.credit for line in self.lines), Decimal("0.00"))


class AccountingException(Exception):
    def __init__(
        self,
        *,
        reason_code: str,
        transaction_reference: str,
        missing_fields: list[str],
    ) -> None:
        super().__init__(f"{reason_code}: missing {', '.join(missing_fields)}")
        self.reason_code = reason_code
        self.transaction_reference = transaction_reference
        self.missing_fields = missing_fields


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _server_sequence_from_pos_code(pos_code: str) -> str:
    return pos_code.rsplit("-", 1)[-1]


def _business_date_from_pos_code(pos_code: str) -> str:
    parts = pos_code.split("-")
    return parts[-2]


def post_paid_service_transaction(
    *,
    pos_code: str,
    branch_code: str,
    payment_account_type: AccountType,
    gross_amount: Decimal,
    coa_mapping: COAMapping,
) -> Journal:
    missing_fields: list[str] = []
    if not coa_mapping.service_revenue:
        missing_fields.append("service_revenue")
    if payment_account_type is AccountType.CASH and not coa_mapping.cash_account:
        missing_fields.append("cash_account")

    if missing_fields:
        raise AccountingException(
            reason_code="UNMAPPED_COA",
            transaction_reference=pos_code,
            missing_fields=missing_fields,
        )

    amount = _money(gross_amount)
    business_date = _business_date_from_pos_code(pos_code)
    server_sequence = _server_sequence_from_pos_code(pos_code)
    journal_number = f"JRN-{branch_code}-{business_date}-{server_sequence}"

    lines = (
        JournalLine(account_code=coa_mapping.cash_account or "", debit=amount),
        JournalLine(account_code=coa_mapping.service_revenue or "", credit=amount),
    )
    journal = Journal(
        journal_number=journal_number,
        branch_code=branch_code,
        transaction_reference=pos_code,
        lines=lines,
        status=JournalStatus.POSTED,
    )
    if journal.debit_total != journal.credit_total:
        raise AccountingException(
            reason_code="UNBALANCED_JOURNAL",
            transaction_reference=pos_code,
            missing_fields=[],
        )
    return journal
