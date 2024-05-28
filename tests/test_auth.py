import unittest
import sys
import os
import time
import logging
from requests.exceptions import HTTPError
from addondev.support import Repo, initializer, logger
logger.setLevel(logging.DEBUG)

Repo.repo = "matrix"
root_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
source_path = os.path.join(root_path, 'plugin.video.crunchyreroll')
initializer(source_path)

if 'CRUNCHYROLL_EMAIL' not in os.environ:
    print("You need to defined CRUNCHYROLL_EMAIL to run tests", file=sys.stderr)
    sys.exit(1)
EMAIL = os.environ['CRUNCHYROLL_EMAIL']

if 'CRUNCHYROLL_PASSWORD' not in os.environ:
    print("You need to defined CRUNCHYROLL_PASSWORD to run tests", file=sys.stderr)
    sys.exit(1)
PASSWORD = os.environ['CRUNCHYROLL_PASSWORD']

# Need to be imported after modules modifications
# pylint: disable=E0401,C0413,C0411
from resources.lib.auth import CrunchyrollAuth # noqa = E402,


class AuthTest(unittest.TestCase):

    def test_is_auth_true(self):
        auth = CrunchyrollAuth(EMAIL, PASSWORD)
        self.assertTrue(auth.is_auth())

    def test_auth_failure(self):
        with self.assertRaises(HTTPError):
            CrunchyrollAuth("dummy", "wrong_password")

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
        print(f"Sleep for {wait+2}s")
        time.sleep(wait+2)
        self.assertTrue(auth.need_refresh())

    def test_refresh(self):
        auth = CrunchyrollAuth(EMAIL, PASSWORD)
        first_access_token = auth.data['access_token']
        print("Sleep for 5s")
        time.sleep(5)
        # pylint: disable=W0212
        auth._refresh()
        second_access_token = auth.data['access_token']
        self.assertIsNot(first_access_token, second_access_token)


if __name__ == "__main__":
    unittest.main()
