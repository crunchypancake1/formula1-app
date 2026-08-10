import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.bounded_dict import BoundedDict
from utils.bounded_set import BoundedSet


# ── BoundedDict ──────────────────────────────────────────────────────────────


class TestBoundedDictSetAndGet:
    def test_set_and_get(self):
        d = BoundedDict(max_size=10)
        d["a"] = 1
        assert d["a"] == 1

    def test_contains(self):
        d = BoundedDict(max_size=10)
        d["x"] = 42
        assert "x" in d
        assert "y" not in d

    def test_eviction_at_max_size(self):
        d = BoundedDict(max_size=3)
        d["a"] = 1
        d["b"] = 2
        d["c"] = 3
        d["d"] = 4
        assert "a" not in d
        assert "b" in d
        assert "c" in d
        assert "d" in d
        assert len(d) == 3

    def test_update_moves_to_end(self):
        d = BoundedDict(max_size=3)
        d["a"] = 1
        d["b"] = 2
        d["c"] = 3
        # Update A — moves it to end
        d["a"] = 10
        # Insert D — B is now oldest, should be evicted
        d["d"] = 4
        assert "b" not in d
        assert "a" in d
        assert d["a"] == 10
        assert "c" in d
        assert "d" in d
        assert len(d) == 3

    def test_get_default(self):
        d = BoundedDict(max_size=10)
        assert d.get("missing") is None
        assert d.get("missing", 99) == 99

    def test_len(self):
        d = BoundedDict(max_size=10)
        assert len(d) == 0
        d["a"] = 1
        assert len(d) == 1
        d["b"] = 2
        assert len(d) == 2


# ── BoundedSet ───────────────────────────────────────────────────────────────


class TestBoundedSet:
    def test_add_and_contains(self):
        s = BoundedSet(max_size=10)
        s.add("x")
        assert "x" in s
        assert "y" not in s

    def test_eviction_at_max_size(self):
        s = BoundedSet(max_size=3)
        s.add("a")
        s.add("b")
        s.add("c")
        s.add("d")
        assert "a" not in s
        assert "b" in s
        assert "c" in s
        assert "d" in s

    def test_add_existing_moves_to_end(self):
        s = BoundedSet(max_size=3)
        s.add("a")
        s.add("b")
        s.add("c")
        # Re-add A — moves it to end
        s.add("a")
        # Add D — B is now oldest, should be evicted
        s.add("d")
        assert "b" not in s
        assert "a" in s
        assert "c" in s
        assert "d" in s
