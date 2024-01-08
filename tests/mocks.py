import os
import json
import tempfile


class MockPersistentDict():
    def __init__(self, store_path):
        tmp_dir = tempfile.gettempdir()
        store_dir_path = os.path.join(tmp_dir, "codequick_storage")
        if not os.path.exists(store_dir_path):
            os.makedirs(store_dir_path)
        self.store_path = os.path.join(store_dir_path, f"{store_path}.json")
        if os.path.exists(self.store_path):
            self._read_file()
        else:
            self._data = {}

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

    def _read_file(self):
        with open(self.store_path, "r", encoding="utf8") as fh:
            self._data = json.load(fh)
            fh.close()

    def flush(self):
        with open(self.store_path, "w", encoding="utf8") as fh:
            json.dump(self._data, fh)
            fh.close()
