
from pos_erp.permissions import Role
from pos_erp.sync_control import BranchCache, DeviceBinding, SyncApprovalRequired, approve_sync_batch, detect_connectivity_recovery


def test_connectivity_recovery_displays_queued_count_and_requires_approval():
    notice = detect_connectivity_recovery(was_online=False, is_online=True, queued_count=7)
    assert notice.recovered is True
    assert notice.queued_count == 7
    assert notice.requires_approval is True


def test_cashier_cannot_approve_sync_batch_but_manager_can():
    try:
        approve_sync_batch(batch_id="batch-1", approver_role=Role.CASHIER, approver_id="cashier-1", queued_count=3)
    except SyncApprovalRequired as exc:
        assert exc.required_roles == (Role.BRANCH_MANAGER, Role.OWNER, Role.IT_ADMIN)
    else:
        raise AssertionError("Expected cashier approval to be rejected")
    approval = approve_sync_batch(batch_id="batch-1", approver_role=Role.BRANCH_MANAGER, approver_id="manager-1", queued_count=3)
    assert approval.approved is True
    assert approval.retry_schedule_seconds == (10, 120, 1200)


def test_branch_cache_tracks_required_offline_snapshots():
    cache = BranchCache(service_catalog_version="svc-v1", staff_schedule_version="staff-v1", price_matrix_version="price-v1", branch_config_version="branch-v1")
    assert cache.is_ready_for_offline is True


def test_device_binding_requires_matching_branch_and_active_device():
    binding = DeviceBinding(device_id="POSA", branch_code="JKT01", active=True)
    assert binding.allows(branch_code="JKT01", device_id="POSA") is True
    assert binding.allows(branch_code="BDG01", device_id="POSA") is False
    assert DeviceBinding(device_id="POSA", branch_code="JKT01", active=False).allows(branch_code="JKT01", device_id="POSA") is False
