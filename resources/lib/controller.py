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
from .api import API
from .model import CrunchyrollError, ProfileData
from .utils import get_listables_from_response
from .videoplayer import VideoPlayer


def show_profiles(args, api: API):
    # api request
    req = api.make_request(
        method="GET",
        url=api.PROFILES_LIST_ENDPOINT
    )

    # check for error
    if not req or "error" in req:
        view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    profiles = req.get("profiles")
    profile_list_items = list(map(lambda profile: ProfileData(profile, args).to_item(args), profiles))
    current_profile = 0

    if bool(api.profile_data.profile_id):
        current_profile = \
            [i for i in range(len(profiles)) if profiles[i].get("profile_id") == api.profile_data.profile_id][0]

    selected = xbmcgui.Dialog().select(
        args.addon.getLocalizedString(30073),
        profile_list_items,
        preselect=current_profile,
        useDetails=True
    )

    if selected == -1:
        return True
    else:
        api.create_session(action="refresh_profile", profile_id=profiles[selected].get("profile_id"))
        return True


def show_queue(args, api: API):
    """ shows anime queue/playlist
    """
    # api request
    req = api.make_request(
        method="GET",
        url=api.WATCHLIST_LIST_ENDPOINT.format(api.account_data.account_id),
        params={
            "n": 1024,
            "locale": args.subtitle
        }
    )

    # check for error
    if not req or "error" in req:
        view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    view.add_listables(
        args=args,
        api=api,
        listables=get_listables_from_response(args, req.get('items')),
        is_folder=False,
        options=view.OPT_CTX_SEASONS | view.OPT_CTX_EPISODES
    )

    view.end_of_directory(args, "episodes")
    return True


def search_anime(args, api: API):
    """Search for anime
    """

    # ask for search string
    if not args.get_arg('search'):
        d = xbmcgui.Dialog().input(args.addon.getLocalizedString(30041), type=xbmcgui.INPUT_ALPHANUM)
        if not d:
            return
    else:
        d = args.get_arg('search')

    # api request
    # available types seem to be: music,series,episode,top_results,movie_listing
    # @todo: we could search for all types, then first present a listing of the types we have search results for
    #        the user then could pick one of these types and get presented with a filtered search result for that
    #        type only.
    req = api.make_request(
        method="GET",
        url=api.SEARCH_ENDPOINT,
        params={
            "n": 50,
            "q": d,
            "locale": args.subtitle,
            "start": args.get_arg('offset', 0, int),
            "type": "series"
        }
    )

    # check for error
    if not req or "error" in req:
        view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    type_data = req.get('items')[0]  # @todo: for now we support only the first type, which should be series

    view.add_listables(
        args=args,
        api=api,
        listables=get_listables_from_response(args, type_data.get('items')),
        is_folder=True,
        options=view.OPT_CTX_WATCHLIST | view.OPT_MARK_ON_WATCHLIST | view.OPT_CTX_SEASONS | view.OPT_CTX_EPISODES
    )

    # pagination
    items_left = type_data.get('total') - (args.get_arg('offset', 0, int) * 50) - len(type_data.get('items'))
    if items_left > 0:
        view.add_item(args,
                      {"title": args.addon.getLocalizedString(30044),
                       "offset": args.get_arg('offset', 0, int) + 50,
                       "search": d,
                       "mode": args.get_arg('mode')},
                      is_folder=True)

    view.end_of_directory(args, "tvshows")
    return True


def show_history(args, api: API):
    """ shows history of watched anime
    """
    items_per_page = 50
    current_page = args.get_arg('offset', 1, int)

    req = api.make_request(
        method="GET",
        url=api.HISTORY_ENDPOINT.format(api.account_data.account_id),
        params={
            "page_size": items_per_page,
            "page": current_page,
            "locale": args.subtitle,
        }
    )

    # check for error
    if not req or "error" in req:
        view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    # episodes / episodes  (crunchy / xbmc)
    view.add_listables(
        args=args,
        api=api,
        listables=get_listables_from_response(args, req.get('data')),
        is_folder=False
    )

    # pagination
    num_pages = int(math.ceil(req["total"] / items_per_page))
    if current_page < num_pages:
        view.add_item(args,
                      {"title": args.addon.getLocalizedString(30044),
                       "offset": args.get_arg('offset', 1, int) + 1,
                       "mode": args.get_arg('mode')},
                      is_folder=True)

    view.end_of_directory(args, "episodes")
    return True


def show_resume_episodes(args, api: API):
    """ shows episode to resume for watching animes
    """
    items_per_page = 50

    req = api.make_request(
        method="GET",
        url=api.RESUME_ENDPOINT.format(api.account_data.account_id),
        params={
            "n": items_per_page,
            "locale": args.subtitle,
            "start": args.get_arg('offset', 0, int),
        }
    )

    # check for error
    if not req or "error" in req:
        view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    # episodes / episodes  (crunchy / xbmc)
    view.add_listables(
        args=args,
        api=api,
        listables=get_listables_from_response(args, req.get('data')),
        is_folder=False,
        options=view.OPT_CTX_SEASONS | view.OPT_CTX_EPISODES
    )

    # pagination
    items_left = req.get("total") - (args.get_arg('offset', 0, int) * items_per_page) - len(req.get("data"))
    if items_left > 0:
        view.add_item(args,
                      {"title": args.addon.getLocalizedString(30044),
                       "offset": args.get_arg('offset', 0, int) + items_per_page,
                       "mode": args.get_arg('mode')},
                      is_folder=True)

    view.end_of_directory(args, "episodes")

    return True


def list_anime_seasons(args, api: API):
    """ view all available anime seasons and filter by selected season
    """
    season_filter: str = args.get_arg('season_filter', "")

    # if no seasons filter applied, list all available seasons
    if not season_filter:
        return list_anime_seasons_without_filter(args, api)

    # else, if we have a season filter, show all from season
    req = api.make_request(
        method="GET",
        url=api.BROWSE_ENDPOINT,
        params={
            "locale": args.subtitle,
            "season_tag": season_filter,
            "n": 100
        }
    )

    # check for error
    if req.get("error") is not None:
        view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    # season / season  (crunchy / xbmc)
    view.add_listables(
        args=args,
        api=api,
        listables=get_listables_from_response(args, req.get('items')),
        is_folder=True,
        options=view.OPT_CTX_WATCHLIST | view.OPT_MARK_ON_WATCHLIST | view.OPT_CTX_SEASONS | view.OPT_CTX_EPISODES
    )

    view.end_of_directory(args, "seasons")


def list_anime_seasons_without_filter(args, api: API):
    """ view all available anime seasons and filter by selected season
    """
    req = api.make_request(
        method="GET",
        url=api.SEASONAL_TAGS_ENDPOINT,
        params={
            "locale": args.subtitle,
        }
    )

    # check for error
    if req.get("error") is not None:
        view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    for season_tag_item in req.get("data"):
        # add to view
        view.add_item(
            args,
            {
                "title": season_tag_item.get("localization", {}).get("title"),
                "season_filter": season_tag_item.get("id", {}),
                "mode": args.get_arg('mode')
            },
            is_folder=True
        )

    view.end_of_directory(args, "seasons")

    return True


def list_filter(args, api: API):
    """ view all anime from selected mode
    """
    category_filter: str = args.get_arg('category_filter', "")

    # we re-use this method which is normally used for the categories to also show some special views, that share
    # the same logic
    specials = ["popularity", "newly_added", "alphabetical"]

    # if no category_filter filter applied, list all available categories
    if not category_filter and category_filter not in specials:
        return list_filter_without_category(args, api)

    # else, if we have a category filter, show all from category

    items_per_page = args.get_arg('items_per_page', 50, int)  # change this if desired

    # default query params - might get modified by special categories below
    params = {
        "locale": args.subtitle,
        "categories": category_filter,
        "n": items_per_page,
        "start": args.get_arg('offset', 0, int),
        "ratings": 'true'
    }

    # hack to re-use this for other views
    if category_filter in specials:
        params.update({"sort_by": category_filter})
        params.pop("categories")

    # api request
    req = api.make_request(
        method="GET",
        url=api.BROWSE_ENDPOINT,
        params=params
    )

    # check for error
    if req is None or req.get("error") is not None:
        view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    # series / collection  (crunchy / xbmc)
    view.add_listables(
        args=args,
        api=api,
        listables=get_listables_from_response(args, req.get('items')),
        is_folder=True,
        options=view.OPT_CTX_WATCHLIST | view.OPT_MARK_ON_WATCHLIST | view.OPT_CTX_SEASONS | view.OPT_CTX_EPISODES
    )

    items_left = req.get('total') - args.get_arg('offset', 0, int) - len(req.get('items'))

    # show next page button
    if items_left > 0:
        view.add_item(
            args,
            {
                "title": args.addon.getLocalizedString(30044),
                "offset": args.get_arg('offset', 0, int) + items_per_page,
                "category_filter": category_filter,
                "mode": args.get_arg('mode')
            },
            is_folder=True
        )

    view.end_of_directory(args, "tvshows")

    return True


def list_filter_without_category(args, api: API):
    # api request for category names / tags
    req = api.make_request(
        method="GET",
        url=api.CATEGORIES_ENDPOINT,
        params={
            "locale": args.subtitle,
        }
    )

    # check for error
    if req.get("error") is not None:
        view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    for category_item in req.get("items"):
        try:
            # add to view
            view.add_item(
                args,
                {
                    "title": category_item.get("localization", {}).get("title"),
                    "plot": category_item.get("localization", {}).get("description"),
                    "plotoutline": category_item.get("localization", {}).get("description"),
                    "thumb": utils.get_img_from_struct(category_item, "low", 1),
                    "fanart": utils.get_img_from_struct(category_item, "background", 1),
                    "category_filter": category_item.get("tenant_category", {}),
                    "mode": args.get_arg('mode')
                },
                is_folder=True
            )
        except Exception:
            utils.log_error_with_trace(
                args,
                "Failed to add category name item to list_filter view: %s" % (json.dumps(category_item, indent=4))
            )

    view.end_of_directory(args, "tvshows")

    return True


def view_season(args, api: API):
    """ view all seasons/arcs of an anime
    """
    # api request
    req = api.make_request(
        method="GET",
        url=api.SEASONS_ENDPOINT.format(api.account_data.cms.bucket),
        params={
            "locale": args.subtitle,
            "series_id": args.get_arg('series_id'),
            "preferred_audio_language": api.account_data.default_audio_language,
            "force_locale": ""
        }
    )

    # check for error
    if not req or "error" in req:
        view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    # season / season  (crunchy / xbmc)
    view.add_listables(
        args=args,
        api=api,
        listables=get_listables_from_response(args, req.get('items')),
        is_folder=True
    )

    view.end_of_directory(args, "seasons")
    return True


def view_episodes(args, api: API):
    """ view all episodes of season
    """
    # api request
    req = api.make_request(
        method="GET",
        url=api.EPISODES_ENDPOINT.format(api.account_data.cms.bucket),
        params={
            "locale": args.subtitle,
            "season_id": args.get_arg('season_id')
        }
    )

    # check for error
    if not req or "error" in req:
        view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    # episodes / episodes  (crunchy / xbmc)
    view.add_listables(
        args=args,
        api=api,
        listables=get_listables_from_response(args, req.get('items')),
        is_folder=False
    )

    view.end_of_directory(args, "episodes")
    return True


def start_playback(args, api: API):
    """ plays an episode
    """
    video_player = VideoPlayer(args, api)
    video_player.start_playback()

    utils.crunchy_log(args, "Starting loop", xbmc.LOGINFO)
    # stay in this method while playing to not lose video_player, as backgrounds threads reference it
    while video_player.is_playing():
        time.sleep(1)

    utils.crunchy_log(args, "playback stopped", xbmc.LOGINFO)

    video_player.clear_active_stream()


def add_to_queue(args, api: API) -> bool:
    # api request
    try:
        api.make_request(
            method="POST",
            url=API.WATCHLIST_V2_ENDPOINT.format(api.account_data.account_id),
            json_data={
                "content_id": args.get_arg('content_id')
            },
            params={
                "locale": args.subtitle,
                "preferred_audio_language": api.account_data.default_audio_language
            },
            headers={
                'Content-Type': 'application/json'
            }
        )
    except CrunchyrollError as e:
        if 'content.add_watchlist_item_v2.item_already_exists' in str(e):
            xbmcgui.Dialog().notification(
                '%s Error' % args.addon_name,
                'Failed to add item to watchlist',
                xbmcgui.NOTIFICATION_ERROR,
                3
            )
            return False
        else:
            raise e

    xbmcgui.Dialog().notification(
        args.addon_name,
        args.addon.getLocalizedString(30071),
        xbmcgui.NOTIFICATION_INFO,
        2,
        False
    )

    return True


# NOTE: be super careful when moving the content_id to json or params. it might delete the whole playlist! *sadpanda*
# def remove_from_queue(args, api: API):
#     # we absolutely need a content_id, otherwise it will delete the whole playlist!
#     if not args.content_id:
#         return False
#
#     # api request
#     req = api.make_request(
#         method="DELETE",
#         url=api.WATCHLIST_REMOVE_ENDPOINT.format(api.account_data.account_id, args.content_id, args.content_id),
#     )
#
#     # check for error - probably does not work
#     if req and "error" in req:
#         view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
#         view.end_of_directory(args)
#         xbmcgui.Dialog().notification(
#             '%s Error' % args.addon_name,
#             'Failed to remove item from watchlist',
#             xbmcgui.NOTIFICATION_ERROR,
#             3
#         )
#         return False
#
#     xbmcgui.Dialog().notification(
#         '%s Success' % args.addon_name,
#         'Item removed from watchlist',
#         xbmcgui.NOTIFICATION_INFO,
#         2
#     )
#
#     return True


def crunchylists_lists(args, api):
    """ Retrieve all crunchylists """

    # api request
    req = api.make_request(
        method='GET',
        url=api.CRUNCHYLISTS_LISTS_ENDPOINT.format(api.account_data.account_id),
        params={
            'locale': args.subtitle
        }
    )

    # check for error
    if not req or 'error' in req:
        view.add_item(args, {'title': args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    for crunchy_list in req.get('data'):
        # add to view
        view.add_item(
            args,
            {
                'title': crunchy_list.get('title'),
                'fanart': xbmcvfs.translatePath(args.addon.getAddonInfo('fanart')),
                'mode': 'crunchylists_item',
                'crunchylists_item_id': crunchy_list.get('list_id')
            },
            is_folder=True
        )

    view.end_of_directory(args, "tvshows")

    return None


def crunchylists_item(args, api):
    """ Retrieve all items for a crunchylist """

    utils.crunchy_log(args, "Fetching crunchylist: %s" % args.get_arg('crunchylists_item_id'))

    # api request
    req = api.make_request(
        method='GET',
        url=api.CRUNCHYLISTS_VIEW_ENDPOINT.format(api.account_data.account_id, args.get_arg('crunchylists_item_id')),
        params={
            'locale': args.subtitle
        }
    )

    # check for error
    if not req or 'error' in req:
        view.add_item(args, {'title': args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    view.add_listables(
        args=args,
        api=api,
        listables=get_listables_from_response(args, req.get('data')),
        is_folder=True,
        options=view.OPT_CTX_SEASONS | view.OPT_CTX_EPISODES
    )

    view.end_of_directory(args, "tvshows")

    return None
