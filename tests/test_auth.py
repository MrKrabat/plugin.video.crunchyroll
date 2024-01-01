import unittest
from unittest.mock import MagicMock
from .mocks import mockPersistentDict
import sys
import time
import os
from requests.exceptions import HTTPError

codequick_mock = MagicMock()
codequick_storage_mock = MagicMock()
codequick_storage_mock.PersistentDict = mockPersistentDict

sys.modules['codequick'] = codequick_mock
sys.modules['codequick.storage'] = codequick_storage_mock

# Need to be imported after modules modifications
from resources.lib.auth import CrunchyrollAuth

if 'CRUNCHYROLL_EMAIL' not in os.environ:
    print("You need to defined CRUNCHYROLL_EMAIL to run tests", file=sys.stderr)
    exit(1)
EMAIL=os.environ['CRUNCHYROLL_EMAIL']

if 'CRUNCHYROLL_PASSWORD' not in os.environ:
    print("You need to defined CRUNCHYROLL_PASSWORD to run tests", file=sys.stderr)
    exit(1)
PASSWORD=os.environ['CRUNCHYROLL_PASSWORD']

class AuthTest(unittest.TestCase):

    def test_is_auth_true(self):
        auth = CrunchyrollAuth(EMAIL, PASSWORD)
        self.assertTrue(auth.is_auth())

    def test_auth_failure(self):
        with self.assertRaises(HTTPError):
            auth = CrunchyrollAuth("dummy", "wrong_password")

    def test_is_auth_false(self):
        auth = CrunchyrollAuth(EMAIL, PASSWORD)
        # Change expires_in to reduce test duration
        auth.data['expires_in'] = 5
        wait = auth.data['expires_in']
        print(f"Sleep for {wait+1}s")
        time.sleep(wait+1)
        self.assertFalse(auth.is_auth())

    def test_need_refresh_false(self):
        auth = CrunchyrollAuth(EMAIL, PASSWORD)
        self.assertFalse(auth.need_refresh())

    def test_need_refresh_true(self):
        auth = CrunchyrollAuth(EMAIL, PASSWORD)
        # Change expires_in to reduce test duration
        auth.data['expires_in'] = 5
        wait = auth.data['expires_in'] * 3 / 4
        print(f"Sleep for {wait+1}s")
        time.sleep(wait+1)
        self.assertTrue(auth.need_refresh())

    def test_refresh(self):
        auth = CrunchyrollAuth(EMAIL, PASSWORD)
        first_access_token = auth.data['access_token']
        print(f"Sleep for 5s")
        time.sleep(5)
        auth._refresh()
        second_access_token = auth.data['access_token']
        self.assertIsNot(first_access_token, second_access_token)
        

if __name__ == "__main__":
    unittest.main()
