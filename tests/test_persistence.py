
from pos_erp.persistence import InMemoryRepository, UnitOfWork


def test_repository_saves_and_loads_entities_by_collection_and_id():
    repo = InMemoryRepository()
    repo.save("transactions", "TRX-001", {"status": "PAID"})
    assert repo.get("transactions", "TRX-001") == {"status": "PAID"}


def test_unit_of_work_commits_staged_changes_atomically():
    repo = InMemoryRepository()
    with UnitOfWork(repo) as uow:
        uow.stage_save("transactions", "TRX-001", {"status": "PAID"})
        assert repo.get("transactions", "TRX-001") is None
    assert repo.get("transactions", "TRX-001") == {"status": "PAID"}


def test_unit_of_work_rolls_back_when_exception_occurs():
    repo = InMemoryRepository()
    try:
        with UnitOfWork(repo) as uow:
            uow.stage_save("transactions", "TRX-001", {"status": "PAID"})
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert repo.get("transactions", "TRX-001") is None
