import unittest
import sys
import os
import logging
import pickle
import binascii
from addondev.support import Repo, initializer, logger
logger.setLevel(logging.DEBUG)

Repo.repo = "nexus"
root_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
source_path = os.path.join(root_path, 'plugin.video.crunchyreroll')
initializer(source_path)

# pylint: disable=C0413,W0611
from . import mock  # noqa: F401, E402


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
def exec_route(url, args=[""]):
    dummy_handle = 1
    sys.argv = [url, dummy_handle, *args]
    main_path = os.path.join(source_path, "main.py")
    with open(main_path, 'rb') as source:
        code = compile(source.read(), 'main.py', 'exec')
        # pylint: disable=W0122
        exec(code, {'__name__': '__main__'}, {'process_errors': False})


class RouteTest(unittest.TestCase):

    def test_root(self):
        url = "plugin://plugin.video.crunchyreroll/"
        exec_route(url)

    def test_search(self):
        pickle_query = serialize_data("My hero", {
            "search_query": "my hero"
        })
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/search"
        query = f"?{pickle_query}"
        args = [query]
        exec_route(url, args)

    def test_search_empty(self):
        pickle_query = serialize_data("empty", {
            "search_query": "empty"
        })
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/search"
        query = f"?{pickle_query}"
        args = [query]
        exec_route(url, args)

    def test_watchlist(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/watchlist"
        exec_route(url)

    def test_watchlist_page_2(self):
        pickle_query = serialize_data("Watchlist", {
            "start": 20
        })
        query = f"?{pickle_query}"
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/watchlist"
        args = [query]
        exec_route(url, args)

    def test_popular(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/popular"
        exec_route(url)

    def test_newly_added(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/newly_added"
        exec_route(url)

    def test_show_series(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/show_series"
        # GG5H5XQX4 is for Frieren
        pickle_query = serialize_data("Series", {
            "series_id": "GG5H5XQX4"
        })
        query = f"?{pickle_query}"
        args = [query]
        exec_route(url, args)

    def test_show_season(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/show_season"
        # GYE5CQMQ5 is for the first Frieren season
        pickle_query = serialize_data("Season", {
            "season_id": "GYE5CQMQ5"
        })
        query = f"?{pickle_query}"
        args = [query]
        exec_route(url, args)

    def test_play_episode(self):
        url = "plugin://plugin.video.crunchyreroll/resources/lib/main/play_episode"
        # G0DUND0K2 if for the first episode of Frieren
        pickle_query = serialize_data("Episode", {
            "episode_id": "G0DUND0K2"
        })
        query = f"?{pickle_query}"
        args = [query]
        exec_route(url, args)
