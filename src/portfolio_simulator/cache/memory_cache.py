"""In-memory LRU cache with TTL for hot-path access."""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass

import pandas as pd


@dataclass
class _CacheEntry:
    data: pd.Series
    expires_at: float  # time.monotonic() timestamp


class MemoryCache:
    """In-memory LRU cache with time-to-live eviction.

    Sits in front of the SQLite cache to avoid repeated disk reads
    during a single session.
    """

    def __init__(self, max_size: int = 500, default_ttl_hours: int = 24) -> None:
        self._max_size = max_size
        self._default_ttl_seconds = default_ttl_hours * 3600
        self._store: OrderedDict[str, _CacheEntry] = OrderedDict()

    def get(self, key: str) -> pd.Series | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return entry.data

    def put(self, key: str, data: pd.Series, ttl_hours: int | None = None) -> None:
        ttl = (ttl_hours * 3600) if ttl_hours else self._default_ttl_seconds
        self._store[key] = _CacheEntry(data=data, expires_at=time.monotonic() + ttl)
        self._store.move_to_end(key)
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()
