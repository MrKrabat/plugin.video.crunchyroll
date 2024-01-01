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
from resources.lib.client import CrunchyrollClient

if 'CRUNCHYROLL_EMAIL' not in os.environ:
    print("You need to defined CRUNCHYROLL_EMAIL to run tests", file=sys.stderr)
    exit(1)
EMAIL=os.environ['CRUNCHYROLL_EMAIL']

if 'CRUNCHYROLL_PASSWORD' not in os.environ:
    print("You need to defined CRUNCHYROLL_PASSWORD to run tests", file=sys.stderr)
    exit(1)
PASSWORD=os.environ['CRUNCHYROLL_PASSWORD']
LOCALE="fr-FR"

class ClientTest(unittest.TestCase):
    
    def test_client_creation(self):
        client = CrunchyrollClient(EMAIL, PASSWORD, LOCALE)
