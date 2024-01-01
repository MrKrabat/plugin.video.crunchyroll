from unittest.mock import Mock

class mockPersistentDict():
    def __init__(self, storePath):
        self._data = {}
        self.flush = Mock()
        self.storePath = storePath

    def __getitem__(self, k):
        return self._data[k]

    def __setitem__(self, k, v):
        self._data[k] = v

    def __enter__(self):
        return self

    def __iter__(self):
        return self._data

    def __exit__(self, *_):
        pass

    def __str__(self):
        return str(self._data)

    def get(self,k, default):
        if k in self._data:
            return self._data[k]
        else:
            return default

