"""Bounded set that evicts oldest entries when full."""

from collections import OrderedDict


class BoundedSet:
    """A set with a maximum size that evicts oldest entries on overflow."""

    def __init__(self, max_size: int = 100):
        self._max_size = max_size
        self._data: OrderedDict = OrderedDict()

    def __contains__(self, item) -> bool:
        return item in self._data

    def add(self, item):
        if item in self._data:
            self._data.move_to_end(item)
            return
        if len(self._data) >= self._max_size:
            self._data.popitem(last=False)
        self._data[item] = None
