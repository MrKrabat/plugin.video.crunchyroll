import unittest
import sys
import os
from unittest.mock import MagicMock
from .mocks import MockPersistentDict

codequick_mock = MagicMock()
codequick_storage_mock = MagicMock()
codequick_storage_mock.PersistentDict = MockPersistentDict

sys.modules['codequick'] = codequick_mock
sys.modules['codequick.storage'] = codequick_storage_mock

# Need to be imported after modules modifications
# pylint: disable=E0401,C0413,C0411
from resources.lib.client import CrunchyrollClient # noqa = E402

if 'CRUNCHYROLL_EMAIL' not in os.environ:
    print("You need to defined CRUNCHYROLL_EMAIL to run tests", file=sys.stderr)
    sys.exit(1)
EMAIL = os.environ['CRUNCHYROLL_EMAIL']

if 'CRUNCHYROLL_PASSWORD' not in os.environ:
    print("You need to defined CRUNCHYROLL_PASSWORD to run tests", file=sys.stderr)
    sys.exit(1)
PASSWORD = os.environ['CRUNCHYROLL_PASSWORD']
LOCALE = "fr-FR"
PAGE_SIZE = 20
RESOLUTION = "720"


class ClientTest(unittest.TestCase):

    def test_client_creation(self):
        CrunchyrollClient(EMAIL, PASSWORD, LOCALE, PAGE_SIZE, RESOLUTION)
