"""Bounded dict that evicts oldest entries when full."""

from collections import OrderedDict
from typing import Generic, TypeVar

_K = TypeVar("_K")
_V = TypeVar("_V")


class BoundedDict(Generic[_K, _V]):
    """A dict with a maximum size that evicts oldest entries on overflow."""

    def __init__(self, max_size: int = 500):
        self._max_size = max_size
        self._data: OrderedDict[_K, _V] = OrderedDict()

    def get(self, key: _K, default: _V | None = None) -> _V | None:
        return self._data.get(key, default)

    def __getitem__(self, key: _K) -> _V:
        return self._data[key]

    def __setitem__(self, key: _K, value: _V) -> None:
        if key in self._data:
            self._data.move_to_end(key)
            self._data[key] = value
            return
        if len(self._data) >= self._max_size:
            self._data.popitem(last=False)
        self._data[key] = value

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def __len__(self) -> int:
        return len(self._data)

    def keys(self) -> list[_K]:
        """Snapshot of the current keys, safe to iterate while mutating the dict."""
        return list(self._data)

    def pop(self, key: _K, default: _V | None = None) -> _V | None:
        return self._data.pop(key, default)
