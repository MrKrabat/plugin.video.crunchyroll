import unittest
import sys
import os
from unittest.mock import MagicMock
from .mocks import MockPersistentDict
root_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
source_path = os.path.join(root_path, 'src')
sys.path.append(source_path)

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

    def test_get_watchlist(self):
        client = CrunchyrollClient(EMAIL, PASSWORD, LOCALE, PAGE_SIZE, RESOLUTION)
        client.get_watchlist()
        client.get_watchlist(start=10)

    def test_search_anime(self):
        client = CrunchyrollClient(EMAIL, PASSWORD, LOCALE, PAGE_SIZE, RESOLUTION)
        client.search_anime(query="my hero")
        client.search_anime(query="my hero", start=10)

    def test_get_history(self):
        client = CrunchyrollClient(EMAIL, PASSWORD, LOCALE, PAGE_SIZE, RESOLUTION)
        client.get_history()
        client.get_history(page=2)

    def test_get_crunchylists(self):
        client = CrunchyrollClient(EMAIL, PASSWORD, LOCALE, PAGE_SIZE, RESOLUTION)
        crunchylists = client.get_crunchylists()
        client.get_crunchylist(crunchylists[0]['list_id'])

    def test_get_one_episode(self):
        # Frieren
        series_id = "GG5H5XQX4"
        client = CrunchyrollClient(EMAIL, PASSWORD, LOCALE, PAGE_SIZE, RESOLUTION)
        seasons = client.get_series_seasons(series_id)
        episodes = client.get_season_episodes(seasons[0].id)
        client.get_stream_url(episodes[0].id)

    def test_playhead_manipulation(self):
        # SPY x FAMILY E34
        episode_id = "GD9UVQPXZ"
        client = CrunchyrollClient(EMAIL, PASSWORD, LOCALE, PAGE_SIZE, RESOLUTION)
        playheads = client.get_playhead([episode_id])
        if len(playheads['data']) == 0:
            playheads = {'data': [{"playhead": 0, "content_id": episode_id, "fully_watched": False}]}
        client.update_playhead(episode_id, playheads['data'][0]['playhead']+10)
        client.update_playhead(episode_id, playheads['data'][0]['playhead'])

    def test_alpha_browse(self):
        client = CrunchyrollClient(EMAIL, PASSWORD, LOCALE, PAGE_SIZE, RESOLUTION)
        index = client.get_alpha()
        client.browse(sort_by="alphabetical", start=index[0]['start'], number=index[0]['number'])

    def test_get_popular(self):
        client = CrunchyrollClient(EMAIL, PASSWORD, LOCALE, PAGE_SIZE, RESOLUTION)
        client.get_popular()
        client.get_popular(start=10)
        client.get_popular(categories=['action'])
        client.get_popular(categories=['action,fantasy'])

    def test_newly_added(self):
        client = CrunchyrollClient(EMAIL, PASSWORD, LOCALE, PAGE_SIZE, RESOLUTION)
        client.get_newly_added()
        client.get_newly_added(start=10)
        client.get_newly_added(categories=['action'])
        client.get_newly_added(categories=['action,fantasy'])

    def test_get_categories(self):
        client = CrunchyrollClient(EMAIL, PASSWORD, LOCALE, PAGE_SIZE, RESOLUTION)
        categories = client.get_categories()
        client.get_sub_categories(categories[0].id)

    def test_get_seasonal_tags(self):
        client = CrunchyrollClient(EMAIL, PASSWORD, LOCALE, PAGE_SIZE, RESOLUTION)
        client.get_seasonal_tags()
