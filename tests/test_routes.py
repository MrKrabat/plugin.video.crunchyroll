import unittest
import sys
import os
import logging
import pickle
import binascii
from addondev.support import Repo, initializer, logger
logger.setLevel(logging.DEBUG)

Repo.repo = "matrix"
root_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
source_path = os.path.join(root_path, 'plugin.video.crunchyreroll')
initializer(source_path)

# Need to be imported after modules modifications
# pylint: disable=E0401,C0413,W0611
from resources.lib.client import CrunchyrollClient # noqa = E402
from . import mock  # noqa: F401, E402

if 'CRUNCHYROLL_EMAIL' not in os.environ:
    print("You need to defined CRUNCHYROLL_EMAIL to run tests", file=sys.stderr)
    sys.exit(1)
EMAIL = os.environ['CRUNCHYROLL_EMAIL']

if 'CRUNCHYROLL_PASSWORD' not in os.environ:
    print("You need to defined CRUNCHYROLL_PASSWORD to run tests", file=sys.stderr)
    sys.exit(1)
PASSWORD = os.environ['CRUNCHYROLL_PASSWORD']
SETTINGS = {
    "prefered_audio": "fr-FR",
    "prefered_subtitle": "fr-FR",
    "page_size": 20
}


def serialize_data(title, kwargs):
    data = {
        "_title_": title
    }
    for key, value in kwargs.items():
        data[key] = value
    data_encoded = binascii.hexlify(pickle.dumps(data)).decode("ascii")
    query = f"_pickle_={data_encoded}"
    return query


# pylint: disable=W0102
def _exec_route(url, args=[""]):
    dummy_handle = 1
    sys.argv = [url, dummy_handle, *args]
    main_path = os.path.join(source_path, "main.py")
    with open(main_path, 'rb') as source:
        code = compile(source.read(), 'main.py', 'exec')
        # pylint: disable=W0122
        exec(code, {'__name__': '__main__'}, {'process_errors': False})


# pylint: disable=W0102
def exec_route(url):
    _exec_route(url)


def exec_route_with_params(url, title, params):
    pickle_query = serialize_data(title, params)
    query = f"?{pickle_query}"
    args = [query]
    _exec_route(url, args)


class RouteTest(unittest.TestCase):

    def test_route_root(self):
        url = "plugin://plugin.video.crunchyreroll/"
        exec_route(url)

    def test_route_menu(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/menu"
        client = CrunchyrollClient(EMAIL, PASSWORD, SETTINGS)
        profile_id = client.auth.data['profile_id']
        exec_route_with_params(url, "Menu", {"profile_id": profile_id})

    def test_route_search(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/search"
        exec_route_with_params(url, "Search", {"search_query": "my hero"})

    def test_route_search_empty(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/search"
        exec_route_with_params(url, "Search Empty", {"search_query": "empty"})

    def test_route_watchlist(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/watchlist"
        exec_route(url)

    def test_route_watchlist_page_2(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/watchlist"
        exec_route_with_params(url, "Watchlist", {"start": 20})

    def test_route_popular(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/popular"
        exec_route(url)

    def test_route_newly_added(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/newly_added"
        exec_route(url)

    def test_route_show_series(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/show_series"
        # GG5H5XQX4 is for Frieren
        exec_route_with_params(url, "Series", {"series_id": "GG5H5XQX4"})

    def test_route_show_season(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/show_season"
        # GYE5CQMQ5 is for the first Frieren season
        exec_route_with_params(url, "Season", {"season_id": "GYE5CQMQ5"})

    def test_route_alpha(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/alpha"
        exec_route(url)

    def test_route_alpha_one(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/alpha_one"
        # Retriving series by alphabetic order is basically retriving a slice of the catalog that match the letter
        # In this scenario, we are testing prefix A
        client = CrunchyrollClient(EMAIL, PASSWORD, SETTINGS)
        index = client.get_alpha()
        item = index[1]
        assert item['prefix'] == 'A'
        exec_route_with_params(url, item['prefix'], {"number": item['number'], "start": item['start']})

    def test_route_categories(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/categories"
        exec_route(url)

    def test_route_sub_category(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/sub_category"
        client = CrunchyrollClient(EMAIL, PASSWORD, SETTINGS)
        categories_list = client.get_categories()
        category = categories_list[0]
        exec_route_with_params(url, category.to_dict()['label'], category.to_dict()['params'])

    def test_route_browse_sub_category(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/browse_sub_category"
        client = CrunchyrollClient(EMAIL, PASSWORD, SETTINGS)
        categories_list = client.get_categories()
        category = categories_list[0]
        sub_categories_list = client.get_sub_categories(category.id)
        sub_category = sub_categories_list[0]
        exec_route_with_params(url, category.to_dict()['label'], sub_category.to_dict()['params'])

    def test_route_simulcast(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/simulcast"
        exec_route(url)

    def test_route_my_lists(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/my_lists"
        exec_route(url)

    def test_route_crunchylists(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/crunchylists"
        exec_route(url)

    def test_route_crunchylist(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/crunchylist"
        client = CrunchyrollClient(EMAIL, PASSWORD, SETTINGS)
        lists = client.get_crunchylists()
        item = lists[0]
        exec_route_with_params(url, item['title'], {'list_id': item['list_id']})

    def test_route_history(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/history"
        exec_route(url)

    def test_route_history_page_2(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/history"
        exec_route_with_params(url, "Page 2", {"page": 2})

    def test_route_play_episode(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/play_episode"
        # G0DUND0K2 if for the first episode of Frieren
        exec_route_with_params(url, "Episode", {"episode_id": "G0DUND0K2"})
