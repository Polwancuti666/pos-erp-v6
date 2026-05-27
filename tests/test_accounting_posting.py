from decimal import Decimal

import pytest

from pos_erp.accounting import (
    AccountingException,
    AccountType,
    COAMapping,
    JournalStatus,
    post_paid_service_transaction,
)


def test_paid_transaction_posts_balanced_journal_to_two_decimal_precision():
    mapping = COAMapping(
        service_revenue="4100-SERVICE-REVENUE",
        cash_account="1100-CASH-ON-HAND",
    )

    journal = post_paid_service_transaction(
        pos_code="POS-JKT01-20260526-000001",
        branch_code="JKT01",
        payment_account_type=AccountType.CASH,
        gross_amount=Decimal("250000.005"),
        coa_mapping=mapping,
    )

    assert journal.status is JournalStatus.POSTED
    assert journal.journal_number == "JRN-JKT01-20260526-000001"
    assert journal.debit_total == Decimal("250000.01")
    assert journal.credit_total == Decimal("250000.01")
    assert journal.lines[0].account_code == "1100-CASH-ON-HAND"
    assert journal.lines[0].debit == Decimal("250000.01")
    assert journal.lines[1].account_code == "4100-SERVICE-REVENUE"
    assert journal.lines[1].credit == Decimal("250000.01")


def test_unmapped_coa_routes_to_exception_queue_without_posting():
    mapping = COAMapping(
        service_revenue=None,
        cash_account="1100-CASH-ON-HAND",
    )

    with pytest.raises(AccountingException) as exc_info:
        post_paid_service_transaction(
            pos_code="POS-JKT01-20260526-000002",
            branch_code="JKT01",
            payment_account_type=AccountType.CASH,
            gross_amount=Decimal("100000.00"),
            coa_mapping=mapping,
        )

    exception = exc_info.value
    assert exception.reason_code == "UNMAPPED_COA"
    assert exception.transaction_reference == "POS-JKT01-20260526-000002"
    assert "service_revenue" in exception.missing_fields
