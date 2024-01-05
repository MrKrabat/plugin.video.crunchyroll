from unittest.mock import Mock


class MockPersistentDict():
    def __init__(self, store_path):
        self._data = {}
        self.flush = Mock()
        self.store_path = store_path

    def __getitem__(self, k):
        return self._data[k]

    def __setitem__(self, k, v):
        self._data[k] = v

    def __enter__(self):
        return self

    def __iter__(self):
        return iter(self._data)

    def __exit__(self, *_):
        pass

    def __str__(self):
        return str(self._data)

    def get(self, k, default):
        if k in self._data:
            return self._data[k]
        return default
