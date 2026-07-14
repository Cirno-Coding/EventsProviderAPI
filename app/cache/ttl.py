import time
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._storage: dict[str, tuple[float, T]] = {}

    def get(self, key: str) -> T | None:
        item = self._storage.get(key)

        if item is None:
            return None

        expires_at, value = item

        if expires_at <= time.monotonic():
            self._storage.pop(key, None)
            return None

        return value

    def set(self, key: str, value: T) -> None:
        expires_at = time.monotonic() + self._ttl_seconds
        self._storage[key] = (expires_at, value)

    def delete(self, key: str) -> None:
        self._storage.pop(key, None)

    def clear(self) -> None:
        self._storage.clear()
