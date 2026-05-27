
from __future__ import annotations
from copy import deepcopy

class InMemoryRepository:
    def __init__(self):
        self._data: dict[str, dict[str, object]] = {}
    def save(self, collection: str, entity_id: str, entity: object) -> None:
        self._data.setdefault(collection, {})[entity_id] = deepcopy(entity)
    def get(self, collection: str, entity_id: str):
        value = self._data.get(collection, {}).get(entity_id)
        return deepcopy(value)

class UnitOfWork:
    def __init__(self, repository: InMemoryRepository):
        self.repository = repository
        self._staged: list[tuple[str, str, object]] = []
    def __enter__(self):
        return self
    def stage_save(self, collection: str, entity_id: str, entity: object) -> None:
        self._staged.append((collection, entity_id, entity))
    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            self._staged.clear()
            return False
        for collection, entity_id, entity in self._staged:
            self.repository.save(collection, entity_id, entity)
        self._staged.clear()
        return False
