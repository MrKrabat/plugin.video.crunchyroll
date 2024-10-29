# -*- coding: utf-8 -*-
# Crunchyroll
# Copyright (C) 2018 MrKrabat
# Copyright (C) 2023 smirgol
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import math
import time

import xbmc
import xbmcgui
import xbmcvfs

from . import utils
from . import view
from .globals import G
from .model import CrunchyrollError, ProfileData
from .utils import get_listables_from_response
from .videoplayer import VideoPlayer


def show_profiles():
    # api request
    req = G.api.make_request(
        method="GET",
        url=G.api.PROFILES_LIST_ENDPOINT
    )

    # check for error
    if not req or "error" in req:
        view.add_item({"title": G.addon.getLocalizedString(30061)})
        view.end_of_directory()
        return False

    profiles = req.get("profiles")
    profile_list_items = list(map(lambda profile: ProfileData(profile).to_item(), profiles))
    current_profile = 0

    if bool(G.api.profile_data.profile_id):
        current_profile = \
            [i for i in range(len(profiles)) if profiles[i].get("profile_id") == G.api.profile_data.profile_id][0]

    selected = xbmcgui.Dialog().select(
        G.args.addon.getLocalizedString(30073),
        profile_list_items,
        preselect=current_profile,
        useDetails=True
    )

    if selected == -1:
        return True
    else:
        G.api.create_session(action="refresh_profile", profile_id=profiles[selected].get("profile_id"))
        return True


def show_queue():
    """ shows anime queue/playlist
    """
    # api request
    req = G.api.make_request(
        method="GET",
        url=G.api.WATCHLIST_LIST_ENDPOINT.format(G.api.account_data.account_id),
        params={
            "n": 1024,
            "locale": G.args.subtitle
        }
    )

    # check for error
    if not req or "error" in req:
        view.add_item({"title": G.args.addon.getLocalizedString(30061)})
        view.end_of_directory()
        return False

    view.add_listables(
        listables=get_listables_from_response(req.get('items')),
        is_folder=False,
        options=view.OPT_CTX_SEASONS | view.OPT_CTX_EPISODES  # | view.OPT_SORT_EPISODES_EXPERIMENTAL
    )

    view.end_of_directory("episodes", cache_to_disc=False)
    return True


def search_anime():
    """Search for anime
    """

    # ask for search string
    if not G.args.get_arg('search'):
        d = xbmcgui.Dialog().input(G.args.addon.getLocalizedString(30041), type=xbmcgui.INPUT_ALPHANUM)
        if not d:
            return
    else:
        d = G.args.get_arg('search')

    # api request
    # available types seem to be: music,series,episode,top_results,movie_listing
    # @todo: we could search for all types, then first present a listing of the types we have search results for
    #        the user then could pick one of these types and get presented with a filtered search result for that
    #        type only.
    req = G.api.make_request(
        method="GET",
        url=G.api.SEARCH_ENDPOINT,
        params={
            "n": 50,
            "q": d,
            "locale": G.args.subtitle,
            "start": G.args.get_arg('offset', 0, int),
            "type": "series"
        }
    )

    # check for error
    if not req or "error" in req:
        view.add_item({"title": G.args.addon.getLocalizedString(30061)})
        view.end_of_directory()
        return False

    if not req.get('items') or len(req.get('items')) == 0:
        view.add_item({"title": G.args.addon.getLocalizedString(30090)})
        view.end_of_directory()
        return False

    type_data = req.get('items')[0]  # @todo: for now we support only the first type, which should be series

    view.add_listables(
        listables=get_listables_from_response(type_data.get('items')),
        is_folder=True,
        options=view.OPT_CTX_WATCHLIST | view.OPT_MARK_ON_WATCHLIST | view.OPT_CTX_SEASONS | view.OPT_CTX_EPISODES
    )

    # pagination
    items_left = type_data.get('total') - (G.args.get_arg('offset', 0, int) * 50) - len(type_data.get('items'))
    if items_left > 0:
        view.add_item(
            {
                "title": G.args.addon.getLocalizedString(30044),
                "offset": G.args.get_arg('offset', 0, int) + 50,
                "search": d,
                "mode": G.args.get_arg('mode')
            },
            is_folder=True
        )

    view.end_of_directory("tvshows")
    return True


def show_history():
    """ shows history of watched anime
    """
    items_per_page = 50
    current_page = G.args.get_arg('offset', 1, int)

    req = G.api.make_request(
        method="GET",
        url=G.api.HISTORY_ENDPOINT.format(G.api.account_data.account_id),
        params={
            "page_size": items_per_page,
            "page": current_page,
            "locale": G.args.subtitle,
        }
    )

    # check for error
    if not req or "error" in req:
        view.add_item({"title": G.args.addon.getLocalizedString(30061)})
        view.end_of_directory()
        return False

    # episodes / episodes  (crunchy / xbmc)
    view.add_listables(
        listables=get_listables_from_response(req.get('data')),
        is_folder=False
    )

    # pagination
    num_pages = int(math.ceil(req["total"] / items_per_page))
    if current_page < num_pages:
        view.add_item(
            {
                "title": G.args.addon.getLocalizedString(30044),
                "offset": G.args.get_arg('offset', 1, int) + 1,
                "mode": G.args.get_arg('mode')
            },
            is_folder=True
        )

    view.end_of_directory("episodes", cache_to_disc=False)
    return True


def show_resume_episodes():
    """ shows episode to resume for watching animes
    """
    items_per_page = 50

    req = G.api.make_request(
        method="GET",
        url=G.api.RESUME_ENDPOINT.format(G.api.account_data.account_id),
        params={
            "n": items_per_page,
            "locale": G.args.subtitle,
            "start": G.args.get_arg('offset', 0, int),
        }
    )

    # check for error
    if not req or "error" in req:
        view.add_item({"title": G.args.addon.getLocalizedString(30061)})
        view.end_of_directory()
        return False

    # episodes / episodes  (crunchy / xbmc)
    view.add_listables(
        listables=get_listables_from_response(req.get('data')),
        is_folder=False,
        options=view.OPT_CTX_SEASONS | view.OPT_CTX_EPISODES
    )

    # pagination
    items_left = req.get("total") - (G.args.get_arg('offset', 0, int) * items_per_page) - len(req.get("data"))
    if items_left > 0:
        view.add_item(
            {
                "title": G.args.addon.getLocalizedString(30044),
                "offset": G.args.get_arg('offset', 0, int) + items_per_page,
                "mode": G.args.get_arg('mode')
            },
            is_folder=True
        )

    view.end_of_directory("episodes", cache_to_disc=False)

    return True


def list_anime_seasons():
    """ view all available anime seasons and filter by selected season
    """
    season_filter: str = G.args.get_arg('season_filter', "")

    # if no seasons filter applied, list all available seasons
    if not season_filter:
        return list_anime_seasons_without_filter()

    # else, if we have a season filter, show all from season
    req = G.api.make_request(
        method="GET",
        url=G.api.BROWSE_ENDPOINT,
        params={
            "locale": G.args.subtitle,
            "season_tag": season_filter,
            "n": 100
        }
    )

    # check for error
    if req.get("error") is not None:
        view.add_item({"title": G.args.addon.getLocalizedString(30061)})
        view.end_of_directory()
        return False

    # season / season  (crunchy / xbmc)
    view.add_listables(
        listables=get_listables_from_response(req.get('items')),
        is_folder=True,
        options=view.OPT_CTX_WATCHLIST | view.OPT_MARK_ON_WATCHLIST | view.OPT_CTX_SEASONS | view.OPT_CTX_EPISODES
    )

    view.end_of_directory("seasons")


def list_anime_seasons_without_filter():
    """ view all available anime seasons and filter by selected season
    """
    req = G.api.make_request(
        method="GET",
        url=G.api.SEASONAL_TAGS_ENDPOINT,
        params={
            "locale": G.args.subtitle,
        }
    )

    # check for error
    if req.get("error") is not None:
        view.add_item({"title": G.args.addon.getLocalizedString(30061)})
        view.end_of_directory()
        return False

    for season_tag_item in req.get("data"):
        # add to view
        view.add_item(
            {
                "title": season_tag_item.get("localization", {}).get("title"),
                "season_filter": season_tag_item.get("id", {}),
                "mode": G.args.get_arg('mode')
            },
            is_folder=True
        )

    view.end_of_directory("seasons")

    return True


def list_filter():
    """ view all anime from selected mode
    """
    category_filter: str = G.args.get_arg('category_filter', "")

    # we re-use this method which is normally used for the categories to also show some special views, that share
    # the same logic
    specials = ["popularity", "newly_added", "alphabetical"]

    # if no category_filter filter applied, list all available categories
    if not category_filter and category_filter not in specials:
        return list_filter_without_category()

    # else, if we have a category filter, show all from category

    items_per_page = G.args.get_arg('items_per_page', 50, int)  # change this if desired

    # default query params - might get modified by special categories below
    params = {
        "locale": G.args.subtitle,
        "categories": category_filter,
        "n": items_per_page,
        "start": G.args.get_arg('offset', 0, int),
        "ratings": 'true'
    }

    # hack to re-use this for other views
    if category_filter in specials:
        params.update({"sort_by": category_filter})
        params.pop("categories")

    # api request
    req = G.api.make_request(
        method="GET",
        url=G.api.BROWSE_ENDPOINT,
        params=params
    )

    # check for error
    if req is None or req.get("error") is not None:
        view.add_item({"title": G.args.addon.getLocalizedString(30061)})
        view.end_of_directory()
        return False

    # series / collection  (crunchy / xbmc)
    view.add_listables(
        listables=get_listables_from_response(req.get('items')),
        is_folder=True,
        options=view.OPT_CTX_WATCHLIST | view.OPT_MARK_ON_WATCHLIST | view.OPT_CTX_SEASONS | view.OPT_CTX_EPISODES
    )

    items_left = req.get('total') - G.args.get_arg('offset', 0, int) - len(req.get('items'))

    # show next page button
    if items_left > 0:
        view.add_item(
            {
                "title": G.args.addon.getLocalizedString(30044),
                "offset": G.args.get_arg('offset', 0, int) + items_per_page,
                "category_filter": category_filter,
                "mode": G.args.get_arg('mode')
            },
            is_folder=True
        )

    view.end_of_directory("tvshows")

    return True


def list_filter_without_category():
    # api request for category names / tags
    req = G.api.make_request(
        method="GET",
        url=G.api.CATEGORIES_ENDPOINT,
        params={
            "locale": G.args.subtitle,
        }
    )

    # check for error
    if req.get("error") is not None:
        view.add_item({"title": G.args.addon.getLocalizedString(30061)})
        view.end_of_directory()
        return False

    for category_item in req.get("items"):
        try:
            # add to view
            view.add_item(
                {
                    "title": category_item.get("localization", {}).get("title"),
                    "plot": category_item.get("localization", {}).get("description"),
                    "plotoutline": category_item.get("localization", {}).get("description"),
                    "thumb": utils.get_img_from_struct(category_item, "low", 1),
                    "fanart": utils.get_img_from_struct(category_item, "background", 1),
                    "category_filter": category_item.get("tenant_category", {}),
                    "mode": G.args.get_arg('mode')
                },
                is_folder=True
            )
        except Exception:
            utils.log_error_with_trace(
                "Failed to add category name item to list_filter view: %s" % (json.dumps(category_item, indent=4))
            )

    view.end_of_directory("tvshows")

    return True


def view_season():
    """ view all seasons/arcs of an anime
    """
    # api request
    req = G.api.make_request(
        method="GET",
        url=G.api.SEASONS_ENDPOINT.format(G.api.account_data.cms.bucket),
        params={
            "locale": G.args.subtitle,
            "series_id": G.args.get_arg('series_id'),
            "preferred_audio_language": G.api.account_data.default_audio_language,
            "force_locale": ""
        }
    )

    # check for error
    if not req or "error" in req:
        view.add_item({"title": G.args.addon.getLocalizedString(30061)})
        view.end_of_directory()
        return False

    # season / season  (crunchy / xbmc)
    view.add_listables(
        listables=get_listables_from_response(req.get('items')),
        is_folder=True
    )

    view.end_of_directory("seasons")
    return True


def view_episodes():
    """ view all episodes of season
    """
    # api request
    req = G.api.make_request(
        method="GET",
        url=G.api.EPISODES_ENDPOINT.format(G.api.account_data.cms.bucket),
        params={
            "locale": G.args.subtitle,
            "season_id": G.args.get_arg('season_id')
        }
    )

    # check for error
    if not req or "error" in req:
        view.add_item({"title": G.args.addon.getLocalizedString(30061)})
        view.end_of_directory()
        return False

    # episodes / episodes  (crunchy / xbmc)
    view.add_listables(
        listables=get_listables_from_response(req.get('items')),
        is_folder=False,
        options=view.OPT_NO_SEASON_TITLE
    )

    view.end_of_directory("episodes", cache_to_disc=False)
    return True


def start_playback():
    """ plays an episode
    """
    video_player = VideoPlayer()
    video_player.start_playback()

    utils.crunchy_log("Starting loop", xbmc.LOGINFO)
    # stay in this method while playing to not lose video_player, as backgrounds threads reference it
    while video_player.is_playing():
        time.sleep(1)

    utils.crunchy_log("playback stopped", xbmc.LOGINFO)

    video_player.clear_active_stream()


def add_to_queue() -> bool:
    # api request
    try:
        G.api.make_request(
            method="POST",
            url=G.api.WATCHLIST_V2_ENDPOINT.format(G.api.account_data.account_id),
            json_data={
                "content_id": G.args.get_arg('content_id')
            },
            params={
                "locale": G.args.subtitle,
                "preferred_audio_language": G.api.account_data.default_audio_language
            },
            headers={
                'Content-Type': 'application/json'
            }
        )
    except CrunchyrollError as e:
        if 'content.add_watchlist_item_v2.item_already_exists' in str(e):
            xbmcgui.Dialog().notification(
                '%s Error' % G.args.addon_name,
                'Failed to add item to watchlist',
                xbmcgui.NOTIFICATION_ERROR,
                3
            )
            return False
        else:
            raise e

    xbmcgui.Dialog().notification(
        G.args.addon_name,
        G.args.addon.getLocalizedString(30071),
        xbmcgui.NOTIFICATION_INFO,
        2,
        False
    )

    return True


# NOTE: be super careful when moving the content_id to json or params. it might delete the whole playlist! *sadpanda*
# def remove_from_queue():
#     # we absolutely need a content_id, otherwise it will delete the whole playlist!
#     if not G.args.content_id:
#         return False
#
#     # api request
#     req = G.api.make_request(
#         method="DELETE",
#         url=G.api.WATCHLIST_REMOVE_ENDPOINT.format(G.api.account_data.account_id, G.args.content_id, G.args.content_id),
#     )
#
#     # check for error - probably does not work
#     if req and "error" in req:
#         view.add_item({"title": G.args.addon.getLocalizedString(30061)})
#         view.end_of_directory()
#         xbmcgui.Dialog().notification(
#             '%s Error' % G.args.addon_name,
#             'Failed to remove item from watchlist',
#             xbmcgui.NOTIFICATION_ERROR,
#             3
#         )
#         return False
#
#     xbmcgui.Dialog().notification(
#         '%s Success' % G.args.addon_name,
#         'Item removed from watchlist',
#         xbmcgui.NOTIFICATION_INFO,
#         2
#     )
#
#     return True


def crunchylists_lists():
    """ Retrieve all crunchylists """

    # api request
    req = G.api.make_request(
        method='GET',
        url=G.api.CRUNCHYLISTS_LISTS_ENDPOINT.format(G.api.account_data.account_id),
        params={
            'locale': G.args.subtitle
        }
    )

    # check for error
    if not req or 'error' in req:
        view.add_item({'title': G.args.addon.getLocalizedString(30061)})
        view.end_of_directory()
        return False

    for crunchy_list in req.get('data'):
        # add to view
        view.add_item(
            {
                'title': crunchy_list.get('title'),
                'fanart': xbmcvfs.translatePath(G.args.addon.getAddonInfo('fanart')),
                'mode': 'crunchylists_item',
                'crunchylists_item_id': crunchy_list.get('list_id')
            },
            is_folder=True
        )

    view.end_of_directory("tvshows")

    return None


def crunchylists_item():
    """ Retrieve all items for a crunchylist """

    utils.crunchy_log("Fetching crunchylist: %s" % G.args.get_arg('crunchylists_item_id'))

    # api request
    req = G.api.make_request(
        method='GET',
        url=G.api.CRUNCHYLISTS_VIEW_ENDPOINT.format(G.api.account_data.account_id,
                                                    G.args.get_arg('crunchylists_item_id')),
        params={
            'locale': G.args.subtitle
        }
    )

    # check for error
    if not req or 'error' in req:
        view.add_item({'title': G.args.addon.getLocalizedString(30061)})
        view.end_of_directory()
        return False

    view.add_listables(
        listables=get_listables_from_response(req.get('data')),
        is_folder=True,
        options=view.OPT_CTX_SEASONS | view.OPT_CTX_EPISODES
    )

    view.end_of_directory("tvshows")

    return None
