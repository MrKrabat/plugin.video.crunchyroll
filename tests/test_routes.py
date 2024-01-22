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
source_path = os.path.join(root_path, 'plugin.video.crunchyroll')
initializer(source_path)


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
        url = "plugin://plugin.video.crunchyroll/"
        exec_route(url)

    def test_search(self):
        pickle_query = serialize_data("My hero", {
            "search_query": "my hero"
        })
        url = "plugin://plugin.video.crunchyroll/resources/lib/main/search"
        query = f"?{pickle_query}"
        args = [query]
        exec_route(url, args)

    def test_search_empty(self):
        pickle_query = serialize_data("empty", {
            "search_query": "empty"
        })
        url = "plugin://plugin.video.crunchyroll/resources/lib/main/search"
        query = f"?{pickle_query}"
        args = [query]
        exec_route(url, args)

    def test_watchlist(self):
        url = "plugin://plugin.video.crunchyroll/resources/lib/main/watchlist"
        exec_route(url)

    def test_watchlist_page_2(self):
        pickle_query = serialize_data("Watchlist", {
            "start": 20
        })
        query = f"?{pickle_query}"
        url = "plugin://plugin.video.crunchyroll/resources/lib/main/watchlist"
        args = [query]
        exec_route(url, args)

    def test_popular(self):
        url = "plugin://plugin.video.crunchyroll/resources/lib/main/popular"
        exec_route(url)

    def test_newly_added(self):
        url = "plugin://plugin.video.crunchyroll/resources/lib/main/newly_added"
        exec_route(url)
