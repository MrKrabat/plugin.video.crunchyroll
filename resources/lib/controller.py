# -*- coding: utf-8 -*-
# Crunchyroll
# Copyright (C) 2018 MrKrabat
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
import sys
import time
from collections import OrderedDict

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

import inputstreamhelper  # noqa
import xbmc
import xbmcgui
import xbmcplugin
from requests import ConnectionError

from . import utils
from . import view
from .api import API
from .model import EpisodeData, MovieData
from .videostream import VideoStream


def show_queue(args, api):
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
    if "error" in req:
        view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    # display media
    for item in req.get("items"):
        # video no longer available
        # @TODO: re-add filtering of non-available items / premium content
        # if not ("most_likely_media" in item and "series" in item and item["most_likely_media"]["available"] and item["most_likely_media"]["premium_available"]):
        #    continue

        try:
            if item.get("panel").get("type") == "episode":
                entry = EpisodeData(item)
            elif item["panel"]["type"] == "movie":
                entry = MovieData(item)
            else:
                utils.crunchy_log(args, "queue | unhandled index for metadata. %s" % (json.dumps(item, indent=4)),
                                  xbmc.LOGERROR)
                continue

            view.add_item(
                args,
                {
                    "title": entry.title,
                    "tvshowtitle": entry.tvshowtitle,
                    "duration": entry.duration,
                    "playcount": entry.playcount,
                    "episode": entry.episode,
                    "episode_id": entry.episode_id,
                    "collection_id": entry.collection_id,
                    "series_id": entry.series_id,
                    "plot": entry.plot,
                    "plotoutline": entry.plotoutline,
                    "genre": "",  # no longer available
                    "year": entry.year,
                    "aired": entry.aired,
                    "premiered": entry.premiered,
                    "thumb": entry.thumb,
                    "fanart": entry.fanart,
                    "stream_id": entry.stream_id,
                    "playhead": entry.playhead,
                    "mode": "videoplay"
                },
                is_folder=False
                # potentially unsafe, it can possibly delete the whole playlist if something goes really wrong
                # callback=lambda li:
                #     li.addContextMenuItems([(args.addon.getLocalizedString(30068), 'RunPlugin(%s?mode=remove_from_queue&content_id=%s&session_restart=True)' % (sys.argv[0], entry.episode_id))])
            )
        except Exception:
            utils.log_error_with_trace(args, "Failed to add item to queue view: %s" % (json.dumps(item, indent=4)))

    view.end_of_directory(args)
    return True


def search_anime(args, api):
    """Search for anime
    """
    # ask for search string
    if not hasattr(args, "search"):
        d = xbmcgui.Dialog().input(args.addon.getLocalizedString(30041), type=xbmcgui.INPUT_ALPHANUM)
        if not d:
            return
    else:
        d = args.search

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
            "start": int(getattr(args, "offset", 0)),
            "type": "series"
        }
    )

    # check for error
    if "error" in req:
        view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    items_left = 0

    for types in req["items"]:
        for item in types["items"]:
            # add to view
            view.add_item(
                args,
                {
                    "title": item["title"],
                    "tvshowtitle": item["title"],
                    "series_id": item["id"],
                    "plot": item["description"],
                    "plotoutline": item["description"],
                    "genre": "",  # requires fetch from api endpoint
                    "year": item["series_metadata"]["series_launch_year"],
                    "studio": "",
                    "thumb": utils.get_image_from_struct(item, "poster_tall", 2),
                    "fanart": utils.get_image_from_struct(item, "poster_wide", 2),
                    "rating": 0,
                    "mode": "series"
                },
                is_folder=True,
                # for yet unknown reason, adding an item to the watchlist requires a session restart
                callback=lambda li:
                li.addContextMenuItems([(args.addon.getLocalizedString(30067),
                                         'RunPlugin(%s?mode=add_to_queue&content_id=%s&session_restart=True)' % (
                                             sys.argv[0], item["id"]))])
            )

        # for now break as we only support one type
        items_left = types["total"] - (int(getattr(args, "offset", 0)) * 50) - len(types["items"])
        break

    # show next page button
    if items_left > 0:
        view.add_item(args,
                      {"title": args.addon.getLocalizedString(30044),
                       "offset": int(getattr(args, "offset", 0)) + 50,
                       "search": d,
                       "mode": args.mode},
                      is_folder=True)

    view.end_of_directory(args)

    return True


def show_history(args, api):
    """ shows history of watched anime
    """
    items_per_page = 50
    current_page = int(getattr(args, "offset", 1))

    req = api.make_request(
        method="GET",
        url=api.HISTORY_ENDPOINT.format(api.account_data.account_id),
        params={
            "page_size": items_per_page,
            "page": current_page,
            "locale": args.subtitle
        }
    )

    # check for error
    if "error" in req:
        view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    num_pages = int(math.ceil(req["total"] / items_per_page))

    for item in req.get("data"):
        try:
            # skip episodes completely that don't have at least the type information
            # @see https://github.com/smirgol/plugin.video.crunchyroll/issues/8
            if not item.get('panel') or not item.get('panel').get('type'):
                continue

            if item.get("panel").get("type") == "episode":
                entry = EpisodeData(item)
            elif item.get("panel").get("type") == "movie":
                entry = MovieData(item)
            else:
                utils.crunchy_log(args, "history | unhandled index for metadata. %s" % (json.dumps(item, indent=4)),
                                  xbmc.LOGERROR)
                continue

            # add to view
            view.add_item(
                args,
                {
                    "title": entry.title,
                    "tvshowtitle": entry.tvshowtitle,
                    "duration": entry.duration,
                    "playcount": entry.playcount,
                    "episode": entry.episode,
                    "episode_id": entry.episode_id,
                    "collection_id": entry.collection_id,
                    "series_id": entry.series_id,
                    "plot": entry.plot,
                    "plotoutline": entry.plotoutline,
                    "genre": "",  # no longer available
                    "year": entry.year,
                    "aired": entry.aired,
                    "premiered": entry.premiered,
                    "thumb": entry.thumb,
                    "fanart": entry.fanart,
                    "stream_id": entry.stream_id,
                    "playhead": entry.playhead,
                    "mode": "videoplay"
                },
                is_folder=False
            )

        except Exception:
            utils.log_error_with_trace(args, "Failed to add item to history view: %s" % (json.dumps(item, indent=4)))

    if current_page < num_pages:
        view.add_item(args,
                      {"title": args.addon.getLocalizedString(30044),
                       "offset": int(getattr(args, "offset", 1)) + 1,
                       "mode": args.mode},
                      is_folder=True)

    view.end_of_directory(args)

    return True


def list_seasons(args, mode, api):
    """ view all available anime seasons and filter by selected season
    """
    season_filter = getattr(args, "season_filter", "")

    # if no seasons filter applied, list all available seasons
    if not season_filter:
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
                    "mode": args.mode
                },
                is_folder=True
            )

        view.end_of_directory(args)

        return

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

    for item in req.get('items'):
        try:
            view.add_item(
                args,
                {
                    "title": item["title"],
                    "tvshowtitle": item["title"],
                    "series_id": item["id"],
                    "plot": item["description"],
                    "plotoutline": item["description"],
                    "year": item["last_public"][:4],
                    "thumb": utils.get_image_from_struct(item, "poster_tall", 2),
                    "fanart": utils.get_image_from_struct(item, "poster_wide", 2),
                    "mode": "series"
                },
                is_folder=True,
                # for yet unknown reason, adding an item to the watchlist requires a session restart
                callback=lambda li:
                li.addContextMenuItems([(args.addon.getLocalizedString(30067),
                                         'RunPlugin(%s?mode=add_to_queue&content_id=%s&session_restart=True)' % (
                                             sys.argv[0], item["id"]))])

            )

        except Exception:
            utils.log_error_with_trace(args, "Failed to add item to seasons view: %s" % (json.dumps(item, indent=4)))

    view.end_of_directory(args)


def listSeries(args, mode, api):
    """ view all anime from selected mode
    """

    # @TODO: update
    #
    # # api request
    # payload = {"media_type": args.genre,
    #            "filter": mode,
    #            "limit": 30,
    #            "offset": int(getattr(args, "offset", 0)),
    #            "fields": "series.name,series.series_id,series.description,series.year,series.publisher_name, \
    #                           series.genres,series.portrait_image,series.landscape_image"}
    # req = api.request(args, "list_series", payload)
    #
    # # check for error
    # if "error" in req:
    #     view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
    #     view.endofdirectory(args)
    #     return False
    #
    # # display media
    # for item in req["data"]:
    #     # add to view
    #     view.add_item(args,
    #                   {"title": item["name"],
    #                    "tvshowtitle": item["name"],
    #                    "series_id": item["series_id"],
    #                    "plot": item["description"],
    #                    "plotoutline": item["description"],
    #                    "genre": ", ".join(item["genres"]),
    #                    "year": item["year"],
    #                    "studio": item["publisher_name"],
    #                    "thumb": item["portrait_image"]["full_url"],
    #                    "fanart": item["landscape_image"]["full_url"],
    #                    "mode": "series"},
    #                   is_folder=True)
    #
    # # show next page button
    # if len(req["data"]) >= 30:
    #     view.add_item(args,
    #                   {"title": args.addon.getLocalizedString(30044),
    #                    "offset": int(getattr(args, "offset", 0)) + 30,
    #                    "search": getattr(args, "search", ""),
    #                    "mode": args.mode},
    #                   is_folder=True)
    #
    # view.endofdirectory(args)
    return True


def list_filter(args, mode, api):
    """ view all anime from selected mode
    """
    category_filter = getattr(args, "category_filter", "")

    # we re-use this method which is normally used for the categories to also show some special views, that share
    # the same logic
    specials = ["popularity", "newly_added", "alphabetical"]

    # if no category_filter filter applied, list all available categories
    if not category_filter and category_filter not in specials:
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
                        "thumb": utils.get_image_from_struct(category_item, "low", 1),
                        "fanart": utils.get_image_from_struct(category_item, "background", 1),
                        "category_filter": category_item.get("tenant_category", {}),
                        "mode": args.mode
                    },
                    is_folder=True
                )
            except Exception:
                utils.log_error_with_trace(
                    args,
                    "Failed to add category name item to list_filter view: %s" % (json.dumps(category_item, indent=4))
                )

        view.end_of_directory(args)

        return

    # else, if we have a category filter, show all from category

    items_left = 0
    items_per_page = int(getattr(args, "items_per_page", 50))  # change this if desired

    # default query params - might get modified by special categories below
    params = {
        "locale": args.subtitle,
        "categories": category_filter,
        "n": items_per_page,
        "start": int(getattr(args, "offset", 0)),
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
    if req.get("error") is not None:
        view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    for item in req.get('items'):
        try:
            view.add_item(
                args,
                {
                    "title": item["title"],
                    "tvshowtitle": item["title"],
                    "series_id": item["id"],
                    "plot": item["description"],
                    "plotoutline": item["description"],
                    "year": item["last_public"][:4],
                    "thumb": utils.get_image_from_struct(item, "poster_tall", 2),
                    "fanart": utils.get_image_from_struct(item, "poster_wide", 2),
                    "mode": "series"
                },
                is_folder=True,
                # for yet unknown reason, adding an item to the watchlist requires a session restart
                callback=lambda li:
                li.addContextMenuItems([(args.addon.getLocalizedString(30067),
                                         'RunPlugin(%s?mode=add_to_queue&content_id=%s&session_restart=True)' % (
                                             sys.argv[0], item["id"]))])
            )

            items_left = req.get('total') - int(getattr(args, "offset", 0)) - len(req.get('items'))

        except Exception:
            utils.log_error_with_trace(
                args,
                "Failed to add item to list_filter view: %s %s" % (
                    json.dumps(params, indent=4),
                    json.dumps(item, indent=4)
                )
            )

    # show next page button
    if items_left > 0:
        view.add_item(
            args,
            {
                "title": args.addon.getLocalizedString(30044),
                "offset": int(getattr(args, "offset", 0)) + items_per_page,
                "category_filter": category_filter,
                "mode": args.mode
            },
            is_folder=True
        )

    view.end_of_directory(args)

    # @TODO: update
    #
    # # test if filter is selected
    # if hasattr(args, "search"):
    #     return listSeries(args, "tag:" + args.search)
    #
    # # api request
    # payload = {"media_type": args.genre}
    # req = api.request(args, "categories", payload)
    #
    # # check for error
    # if "error" in req:
    #     view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
    #     view.endofdirectory(args)
    #     return False
    #
    # # display media
    # for item in req["data"][mode]:
    #     # add to view
    #     view.add_item(args,
    #                   {"title": item["label"],
    #                    "search": item["tag"],
    #                    "mode": args.mode},
    #                   is_folder=True)
    #
    # view.endofdirectory(args)
    return True


def view_series(args, api):
    """ view all seasons/arcs of an anime
    """
    # api request
    req = api.make_request(
        method="GET",
        url=api.SEASONS_ENDPOINT.format(api.account_data.cms.bucket),
        params={
            "locale": args.subtitle,
            "series_id": args.series_id,
            "preferred_audio_language": api.account_data.default_audio_language,
            "force_locale": ""
        }
    )

    # check for error
    if "error" in req:
        view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    # display media
    for item in req["items"]:
        try:
            # filter items where either audio or subtitles match my configured language
            # otherwise it will break things when selecting the correct stream later.
            # @see: issues.txt
            if not utils.filter_series(args, item):
                continue

            # add to view
            view.add_item(
                args,
                {
                    "title": item["title"],
                    "tvshowtitle": item["title"],
                    "season": item["season_number"],
                    "collection_id": item["id"],
                    "series_id": args.series_id,
                    "plot": item["description"],
                    "plotoutline": item["description"],
                    "genre": None,  # item["media_type"],
                    "aired": None,  # item["created"][:10],
                    "premiered": None,  # item["created"][:10],
                    "status": u"Completed" if item["is_complete"] else u"Continuing",
                    "thumb": args.thumb,
                    "fanart": args.fanart,
                    "mode": "episodes"
                },
                is_folder=True
            )
        except Exception:
            utils.log_error_with_trace(args,
                                       "Failed to add item to view_series view: %s" % (json.dumps(item, indent=4)))

    view.end_of_directory(args)
    return True


def view_episodes(args, api):
    """ view all episodes of season
    """
    # api request
    req = api.make_request(
        method="GET",
        url=api.EPISODES_ENDPOINT.format(api.account_data.cms.bucket),
        params={
            "locale": args.subtitle,
            "season_id": args.collection_id
        }
    )

    # @TODO: collect all episodes ids and make a call to "playheads" api endpoint,
    #        to find out if and which we haven't seen fully yet.

    # check for error
    if "error" in req:
        view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    # for the watched status, we need an extra call to api, providing it with all episode ids.
    # this relies fully on the watched status from crunchyroll, the old approach with percentage was better,
    # but it's much more effort to get the duration of the episodes at this point, as it's not provided by the endpoint
    episode_ids = []
    for item in req["items"]:
        episode_ids.append(item.get('id'))

    req_playheads = api.make_request(
        method="GET",
        url=api.PLAYHEADS_ENDPOINT.format(api.account_data.account_id),
        params={
            "locale": args.subtitle,
            "content_ids": ','.join(episode_ids)
        }
    )

    # display media
    for item in req["items"]:
        try:
            stream_id = utils.get_stream_id_from_url(item.get('__links__', []).get('streams', []).get('href', ''))
            if stream_id is None:
                utils.crunchy_log(args, "failed to fetch stream_id for %s" % (item.get('series_title', 'undefined')),
                                  xbmc.LOGERROR)
                continue

            # add to view
            view.add_item(
                args,
                {
                    "title": item["series_title"] + " #" + str(item["episode_number"]) + " - " + item["title"],
                    "tvshowtitle": item["series_title"],
                    "duration": int(item["duration_ms"] / 1000),
                    "playcount": utils.get_watched_status_from_playheads_data(req_playheads, item["id"]),
                    "episode": item["episode_number"],
                    "episode_id": item["id"],
                    "collection_id": args.collection_id,
                    "series_id": item["series_id"],
                    "plot": item["description"],
                    "plotoutline": item["description"],
                    "aired": item["episode_air_date"][:10],
                    "premiered": item["availability_starts"][:10],  # ???
                    "thumb": utils.get_image_from_struct(item, "thumbnail", 2),
                    "fanart": args.fanart,
                    "mode": "videoplay",
                    # note that for fetching streams we need a special guid, not the episode_id
                    "stream_id": stream_id,
                    "playhead": None
                },
                is_folder=False
            )
        except Exception:
            utils.log_error_with_trace(args,
                                       "Failed to add item to view_episodes view: %s" % (json.dumps(item, indent=4)))

    view.end_of_directory(args)
    return True


def start_playback(args, api):
    """ plays an episode
    """
    ##############################
    # get stream url
    ##############################

    # there are tons of different stream types. not sure which one to pick...
    # also, would be very interesting to make the streams switchable in kodi...
    # adaptive_dash
    # adaptive_hls - I chose this, which works for me
    # download_dash
    # download_hls
    # drm_adaptive_dash
    # drm_adaptive_hls
    # drm_download_dash
    # drm_download_hls
    # drm_multitrack_adaptive_hls_v2
    # multitrack_adaptive_hls_v2
    # vo_adaptive_dash
    # vo_adaptive_hls
    # vo_drm_adaptive_dash
    # vo_drm_adaptive_hls

    video_stream_helper = VideoStream(args, api)

    try:
        stream_info = video_stream_helper.get_player_stream_data()
        if not stream_info or not stream_info.stream_url:
            utils.crunchy_log(args, "Failed to load stream info for playback", xbmc.LOGERROR)

            item = xbmcgui.ListItem(getattr(args, "title", "Title not provided"))
            xbmcplugin.setResolvedUrl(int(args.argv[1]), False, item)
            xbmcgui.Dialog().ok(args.addonname, args.addon.getLocalizedString(30064))

    except Exception:
        utils.log_error_with_trace(args, "Failed to prepare stream info data")
        item = xbmcgui.ListItem(getattr(args, "title", "Title not provided"))
        xbmcplugin.setResolvedUrl(int(args.argv[1]), False, item)
        xbmcgui.Dialog().ok(args.addonname, args.addon.getLocalizedString(30064))
        return False

    # prepare playback
    item = xbmcgui.ListItem(getattr(args, "title", "Title not provided"), path=stream_info.stream_url)
    item.setMimeType('application/dash+xml')
    item.setContentLookup(False)

    # inputstream adaptive
    from inputstreamhelper import Helper  # noqa

    is_helper = Helper("mpd", 'com.widevine.alpha')
    if is_helper.check_inputstream():
        manifest_headers = OrderedDict([
            ('User-Agent', API.CRUNCHYROLL_UA),
            ('Authorization', "Bearer {}".format(api.account_data.access_token))
        ])

        license_headers = OrderedDict([
            ('User-Agent', API.CRUNCHYROLL_UA),
            ('Content-Type', 'application/octet-stream'),
            ('Origin', 'https://static.crunchyroll.com'),
            ('Authorization', "Bearer {}".format(api.account_data.access_token)),
            ('x-cr-content-id', args.episode_id),
            ('x-cr-video-token', stream_info.token)
        ])

        license_config = OrderedDict([
            ('license_server_url', API.LICENSE_ENDPOINT),
            ('headers', urlencode(license_headers)),
            ('post_data', 'R{SSM}'),
            ('response_data', 'JBlicense')
        ])

        item.setProperty("inputstreamaddon", "inputstream.adaptive")
        item.setProperty("inputstream.adaptive.manifest_type", "mpd")
        item.setProperty("inputstream.adaptive.license_type", "com.widevine.alpha")
        item.setProperty('inputstream.adaptive.stream_headers', urlencode(manifest_headers))
        item.setProperty("inputstream.adaptive.manifest_headers", urlencode(manifest_headers))
        item.setProperty('inputstream.adaptive.license_key', '|'.join(list(license_config.values())))

        # add soft subtitles url for configured language
        if stream_info.subtitle_urls:
            item.setSubtitles(stream_info.subtitle_urls)

        # start playback
        xbmcplugin.setResolvedUrl(int(args.argv[1]), True, item)

        # wait for playback
        if wait_for_playback(10):
            # if successful wait more
            xbmc.sleep(3000)

    # @TODO: fallbacks not tested

    # start fallback
    if not wait_for_playback(2):
        # start without inputstream adaptive
        utils.crunchy_log(args, "Inputstream Adaptive failed, trying directly with kodi", xbmc.LOGDEBUG)
        item.setProperty("inputstreamaddon", "")
        xbmc.Player().play(stream_info.stream_url, item)

    # sync playtime with crunchyroll
    if args.addon.getSetting("sync_playtime") == "true":
        # fetch playhead info from api
        if hasattr(args, 'playhead') is False or args.playhead is None:
            args.playhead = 0

            req_episode_data = api.make_request(
                method="GET",
                url=api.PLAYHEADS_ENDPOINT.format(api.account_data.account_id),
                params={
                    "locale": args.subtitle,
                    "content_ids": args.episode_id
                }
            )

            if req_episode_data and req_episode_data["data"]:
                args.playhead = int(req_episode_data["data"][0]["playhead"])

        # wait for video to begin
        player = xbmc.Player()
        if not wait_for_playback(30):
            utils.crunchy_log(args, "Timeout reached, video did not start in 30 seconds", xbmc.LOGERROR)
            return

        # ask if user want to continue playback
        if args.playhead and args.duration:
            resume = int(int(args.playhead) / float(args.duration) * 100)
            if 5 <= resume <= 90:
                player.pause()
                if xbmcgui.Dialog().yesno(args.addonname, args.addon.getLocalizedString(30065) % int(resume)):
                    player.seekTime(float(args.playhead) - 5)
                player.pause()

        # update playtime at crunchyroll
        try:
            while stream_info.stream_url == player.getPlayingFile():
                # wait 10 seconds
                xbmc.sleep(10000)

                if stream_info.stream_url == player.getPlayingFile():
                    # api request
                    try:
                        api.make_request(
                            method="POST",
                            url=api.PLAYHEADS_ENDPOINT.format(api.account_data.account_id),
                            json={
                                "playhead": int(player.getTime()),
                                "content_id": args.episode_id
                            },
                            headers={
                                'Content-Type': 'application/json'
                            }
                        )
                    except ConnectionError:
                        # catch timeout exception
                        pass
        except RuntimeError:
            utils.crunchy_log(args, "Playback aborted", xbmc.LOGDEBUG)


def wait_for_playback(timeout=30):
    """ function that waits for playback
    """
    timer = time.time() + timeout
    while not xbmc.getCondVisibility("Player.HasMedia"):
        xbmc.sleep(50)
        # timeout to prevent infinite loop
        if time.time() > timer:
            return False

    return True


def add_to_queue(args, api):
    # api request
    req = api.make_request(
        method="POST",
        url=API.WATCHLIST_ADD_ENDPOINT.format(api.account_data.account_id),
        json={
            "content_id": args.content_id
        },
        params={
            "locale": args.subtitle,
            "preferred_audio_language": api.account_data.default_audio_language
        },
        headers={
            'Content-Type': 'application/json'
        }
    )

    # check for error
    if req and "error" in req:
        view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        xbmcgui.Dialog().notification(
            '%s Error' % args.addonname,
            'Failed to add item to watchlist',
            xbmcgui.NOTIFICATION_ERROR,
            3
        )
        return False

    xbmcgui.Dialog().notification(
        args.addonname,
        args.addon.getLocalizedString(30071),
        xbmcgui.NOTIFICATION_INFO,
        2,
        False
    )

    return True


# NOTE: be super careful when moving the content_id to json or params. it might delete the whole playlist! *sadpanda*
def remove_from_queue(args, api):
    # currently disabled
    return False
    #
    # # we absolutely need a content_id, otherwise it will delete the whole playlist!
    # if not args.content_id:
    #     return False
    #
    # # api request
    # req = api.make_request(
    #     method="DELETE",
    #     url=api.WATCHLIST_REMOVE_ENDPOINT.format(api.account_data.account_id, args.content_id, args.content_id),
    # )
    #
    # # check for error - probably does not work
    # if req and "error" in req:
    #     view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
    #     view.end_of_directory(args)
    #     xbmcgui.Dialog().notification(
    #         '%s Error' % args.addonname,
    #         'Failed to remove item from watchlist',
    #         xbmcgui.NOTIFICATION_ERROR,
    #         3
    #     )
    #     return False
    #
    # xbmcgui.Dialog().notification(
    #     '%s Success' % args.addonname,
    #     'Item removed from watchlist',
    #     xbmcgui.NOTIFICATION_INFO,
    #     2
    # )
    #
    # return True
