from decimal import Decimal

import pytest

from pos_erp.treatment import (
    ConfirmationRequired,
    ServiceCatalog,
    StaffDirectory,
    TreatmentCart,
    TreatmentStatus,
)


def make_catalog() -> ServiceCatalog:
    return ServiceCatalog(
        prices={
            "svc-haircut": Decimal("100000.00"),
            "svc-creambath": Decimal("150000.00"),
        }
    )


def make_staff() -> StaffDirectory:
    return StaffDirectory(
        staff_price_tiers={
            "staff-a": "senior",
            "staff-b": "senior",
            "staff-c": "junior",
        },
        available_staff={"staff-a", "staff-b", "staff-c"},
    )


def test_before_payment_cashier_can_add_and_remove_service_with_price_recalculation():
    cart = TreatmentCart(transaction_id="TMP-JKT01-POSA-20260526-000001")
    catalog = make_catalog()
    staff = make_staff()

    cart.add_service("svc-haircut", staff_id="staff-a", catalog=catalog, staff_directory=staff)
    cart.add_service("svc-creambath", staff_id="staff-b", catalog=catalog, staff_directory=staff)
    assert cart.total_price == Decimal("250000.00")

    cart.remove_service("svc-haircut")
    assert cart.total_price == Decimal("150000.00")
    assert [line.service_id for line in cart.lines] == ["svc-creambath"]


def test_service_and_staff_edits_are_blocked_after_payment():
    cart = TreatmentCart(transaction_id="POS-JKT01-20260526-000001")
    catalog = make_catalog()
    staff = make_staff()
    cart.add_service("svc-haircut", staff_id="staff-a", catalog=catalog, staff_directory=staff)
    cart.mark_paid()

    with pytest.raises(ValueError, match="cannot edit treatment after payment"):
        cart.add_service("svc-creambath", staff_id="staff-b", catalog=catalog, staff_directory=staff)


def test_unavailable_selected_staff_suggests_same_price_tier_alternative():
    cart = TreatmentCart(transaction_id="TMP-JKT01-POSA-20260526-000001")
    catalog = make_catalog()
    staff = make_staff()
    cart.add_service("svc-haircut", staff_id="staff-a", catalog=catalog, staff_directory=staff)
    staff.mark_unavailable("staff-a")

    suggestion = cart.revalidate_staff(line_id="svc-haircut", staff_directory=staff)

    assert suggestion.status is TreatmentStatus.REASSIGNMENT_SUGGESTED
    assert suggestion.suggested_staff_id == "staff-b"
    assert suggestion.requires_confirmation is True


def test_staff_reassignment_requires_explicit_confirmation():
    cart = TreatmentCart(transaction_id="TMP-JKT01-POSA-20260526-000001")
    catalog = make_catalog()
    staff = make_staff()
    cart.add_service("svc-haircut", staff_id="staff-a", catalog=catalog, staff_directory=staff)

    with pytest.raises(ConfirmationRequired):
        cart.change_staff(
            line_id="svc-haircut",
            new_staff_id="staff-b",
            staff_directory=staff,
            confirmed=False,
        )

    cart.change_staff(
        line_id="svc-haircut",
        new_staff_id="staff-b",
        staff_directory=staff,
        confirmed=True,
    )
    assert cart.lines[0].staff_id == "staff-b"


def test_no_available_staff_offers_waitlist_or_cancellation():
    cart = TreatmentCart(transaction_id="TMP-JKT01-POSA-20260526-000001")
    catalog = make_catalog()
    staff = make_staff()
    cart.add_service("svc-haircut", staff_id="staff-a", catalog=catalog, staff_directory=staff)
    staff.mark_unavailable("staff-a")
    staff.mark_unavailable("staff-b")

    suggestion = cart.revalidate_staff(line_id="svc-haircut", staff_directory=staff)

    assert suggestion.status is TreatmentStatus.WAITLIST_OR_CANCEL
    assert suggestion.suggested_staff_id is None
    assert suggestion.options == ("WAITLIST", "CANCEL")
