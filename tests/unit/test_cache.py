"""Tests for caching layer."""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from portfolio_simulator.cache.memory_cache import MemoryCache
from portfolio_simulator.cache.sqlite_cache import SQLiteCache


@pytest.fixture
def sample_series():
    idx = pd.bdate_range("2020-01-02", periods=100)
    return pd.Series(np.random.default_rng(42).normal(100, 10, 100), index=idx, name="TEST")


class TestMemoryCache:
    def test_put_and_get(self, sample_series):
        cache = MemoryCache()
        cache.put("key1", sample_series)
        result = cache.get("key1")
        assert result is not None
        pd.testing.assert_series_equal(result, sample_series)

    def test_miss(self):
        cache = MemoryCache()
        assert cache.get("nonexistent") is None

    def test_invalidate(self, sample_series):
        cache = MemoryCache()
        cache.put("key1", sample_series)
        cache.invalidate("key1")
        assert cache.get("key1") is None

    def test_clear(self, sample_series):
        cache = MemoryCache()
        cache.put("k1", sample_series)
        cache.put("k2", sample_series)
        cache.clear()
        assert cache.get("k1") is None

    def test_lru_eviction(self, sample_series):
        cache = MemoryCache(max_size=2)
        cache.put("a", sample_series)
        cache.put("b", sample_series)
        cache.put("c", sample_series)  # Should evict 'a'
        assert cache.get("a") is None
        assert cache.get("b") is not None
        assert cache.get("c") is not None


class TestSQLiteCache:
    @pytest.fixture
    def db_path(self, tmp_path):
        return tmp_path / "test.db"

    def test_put_and_get(self, sample_series, db_path):
        cache = SQLiteCache(db_path)
        cache.put("key1", sample_series)
        result = cache.get("key1")
        assert result is not None
        # Compare values and index (ignore freq metadata)
        np.testing.assert_array_almost_equal(result.values, sample_series.values)
        assert result.name == sample_series.name
        cache.close()

    def test_miss(self, db_path):
        cache = SQLiteCache(db_path)
        assert cache.get("nonexistent") is None
        cache.close()

    def test_invalidate(self, sample_series, db_path):
        cache = SQLiteCache(db_path)
        cache.put("key1", sample_series)
        cache.invalidate("key1")
        assert cache.get("key1") is None
        cache.close()

    def test_expired_entry(self, sample_series, db_path):
        cache = SQLiteCache(db_path)
        cache.put("key1", sample_series, ttl_hours=0)  # Expires immediately
        import time
        time.sleep(0.01)
        assert cache.get("key1") is None
        cache.close()
