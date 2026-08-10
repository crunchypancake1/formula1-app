import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class MockRepo:
    """Records all method calls for assertion. Returns configurable values."""
    def __init__(self, **return_values):
        self.calls = {}
        self._return_values = return_values

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        def method(*args, **kwargs):
            self.calls.setdefault(name, []).append((args, kwargs))
            return self._return_values.get(name)
        return method

    def call_count(self, method_name):
        return len(self.calls.get(method_name, []))

    def last_call(self, method_name):
        calls = self.calls.get(method_name, [])
        return calls[-1] if calls else None

    def all_calls(self, method_name):
        return self.calls.get(method_name, [])
