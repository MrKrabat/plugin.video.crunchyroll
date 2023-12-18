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

import ssl
import time
import inputstreamhelper

try:
    from urllib2 import URLError
except ImportError:
    from urllib.error import URLError

import xbmc
import xbmcgui
import xbmcplugin

from .api import API
from . import view
from . import utils

import json

def show_queue(args, api: API):
    """ shows anime queue/playlist
    """
    # api request
    # payload = {"media_types": "anime|drama",
    #           "fields":      "media.name,media.media_id,media.collection_id,media.collection_name,media.description,media.episode_number,media.created, \
    #                           media.screenshot_image,media.premium_only,media.premium_available,media.available,media.premium_available,media.duration, \
    #                           series.series_id,series.year,series.publisher_name,series.rating,series.genres,series.landscape_image"}
    # req = API.request(args, "queue", payload)

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
    for item in req["items"]:
        # video no longer available
        # @TODO: re-add filtering of non-available items
        # if not ("most_likely_media" in item and "series" in item and item["most_likely_media"]["available"] and item["most_likely_media"]["premium_available"]):
        #    continue

        xbmc.log("CRUNCHYROLL | dumping queue items", xbmc.LOGINFO)
        xbmc.log("%s" % (json.dumps(item, indent=4)), xbmc.LOGINFO)

        meta = item["panel"]["episode_metadata"]

        stream_id = utils.get_stream_id_from_url(item["panel"]["__links__"]["streams"]["href"])
        if stream_id is None:
            xbmc.log(
                "[PLUGIN] Crunchyroll | Error : failed to fetch stream_id for %s" % (meta["series_title"]),
                xbmc.LOGINFO
            )
            continue

        view.add_item(
            args,
            {
                "title": meta["season_title"] + " #" + meta["episode"] + " - " + item["panel"]["title"],
                "tvshowtitle": meta["series_title"],
                "duration": meta["duration_ms"],
                "playcount": 1 if (int(int(item["playhead"]) / (int(meta["duration_ms"]) / 1000) * 100)) > 90 else 0,
                "episode": meta["episode"],
                "episode_id": item["panel"]["id"],  # meta["identifier"],  # ???
                "collection_id": meta["season_id"],
                "series_id": meta["series_id"],
                "plot": item["panel"]["description"],
                "plotoutline": item["panel"]["description"],
                "genre": "",  # no longer available
                "year": meta["episode_air_date"][:10],
                "aired": meta["episode_air_date"][:10],
                "premiered": meta["episode_air_date"][:10],
                "studio": "",  # no longer available
                "rating": 0,  # no longer available
                "thumb": item["panel"]["images"]["thumbnail"][-1][-1]["source"],
                # that's usually 1080p, not sure if too big?
                "fanart": item["panel"]["images"]["thumbnail"][-1][-1]["source"],
                "mode": "videoplay",
                # note that for fetching streams we need a special guid, not the episode_id
                "stream_id": stream_id,
                "playhead": int(item["playhead"])
            },
            is_folder=False
        )

        # add to view
    #        view.add_item(args,
    #                      {"title":         item["most_likely_media"]["collection_name"] + " #" + item["most_likely_media"]["episode_number"] + " - " + item["most_likely_media"]["name"],
    #                       "tvshowtitle":   item["most_likely_media"]["collection_name"],
    #                       "duration":      item["most_likely_media"]["duration"],
    #                       "playcount":     1 if (100/(float(item["most_likely_media"]["duration"])+1))*int(item["playhead"]) > 90 else 0,
    #                       "episode":       item["most_likely_media"]["episode_number"],
    #                       "episode_id":    item["most_likely_media"]["media_id"],
    #                       "collection_id": item["most_likely_media"]["collection_id"],
    #                       "series_id":     item["series"]["series_id"],
    #                       "plot":          item["most_likely_media"]["description"],
    #                       "plotoutline":   item["most_likely_media"]["description"],
    #                       "genre":         ", ".join(item["series"]["genres"]),
    #                       "year":          item["series"]["year"],
    #                       "aired":         item["most_likely_media"]["created"][:10],
    #                       "premiered":     item["most_likely_media"]["created"][:10],
    #                       "studio":        item["series"]["publisher_name"],
    #                       "rating":        int(item["series"]["rating"])/10.0,
    #                       "thumb":         (item["most_likely_media"]["screenshot_image"]["fwidestar_url"] if item["most_likely_media"]["premium_only"] else item["most_likely_media"]["screenshot_image"]["full_url"]) if item["most_likely_media"]["screenshot_image"] else "",
    #                       "fanart":        item["series"]["landscape_image"]["full_url"],
    #                       "mode":          "videoplay"},
    #                      is_folder=False)

    view.end_of_directory(args)
    return True


def search_anime(args, api: API):
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
                    "thumb": item["images"]["poster_tall"][-1][-1]["source"],
                    "fanart": item["images"]["poster_wide"][-1][-1]["source"],
                    "rating": 0,  # that's on the live api only  int(item["rating"]["average"] * 2),  # it's now a 5-star rating, and we use score of 10?
                    "mode": "series"
                },
                is_folder=True
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


def showHistory(args, api: API):
    """ shows history of watched anime
    """

    # @TODO: update
    #
    # # api request
    # payload = {"media_types": "anime|drama",
    #            "limit": 30,
    #            "offset": int(getattr(args, "offset", 0)),
    #            "fields": "media.name,media.media_id,media.collection_id,media.collection_name,media.description,media.episode_number,media.created, \
    #                            media.screenshot_image,media.premium_only,media.premium_available,media.available,media.premium_available,media.duration,media.playhead, \
    #                            series.series_id,series.year,series.publisher_name,series.rating,series.genres,series.landscape_image"}
    # req = api.request(args, "recently_watched", payload)
    #
    # # check for error
    # if "error" in req:
    #     view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
    #     view.endofdirectory(args)
    #     return False
    #
    # # display media
    # for item in req["data"]:
    #     # video no longer available
    #     if not ("media" in item and "series" in item and item["media"]["available"] and item["media"][
    #         "premium_available"]):
    #         continue
    #
    #     # add to view
    #     view.add_item(args,
    #                   {"title": item["media"]["collection_name"] + " #" + item["media"]["episode_number"] + " - " +
    #                             item["media"]["name"],
    #                    "tvshowtitle": item["media"]["collection_name"],
    #                    "duration": item["media"]["duration"],
    #                    "playcount": 1 if (100 / (float(item["media"]["duration"]) + 1)) * int(
    #                        item["media"]["playhead"]) > 90 else 0,
    #                    "episode": item["media"]["episode_number"],
    #                    "episode_id": item["media"]["media_id"],
    #                    "collection_id": item["media"]["collection_id"],
    #                    "series_id": item["series"]["series_id"],
    #                    "plot": item["media"]["description"],
    #                    "plotoutline": item["media"]["description"],
    #                    "genre": ", ".join(item["series"]["genres"]),
    #                    "year": item["series"]["year"],
    #                    "aired": item["media"]["created"][:10],
    #                    "premiered": item["media"]["created"][:10],
    #                    "studio": item["series"]["publisher_name"],
    #                    "rating": int(item["series"]["rating"]) / 10.0,
    #                    "thumb": (
    #                        item["media"]["screenshot_image"]["fwidestar_url"] if item["media"]["premium_only"] else
    #                        item["media"]["screenshot_image"]["full_url"]) if item["media"]["screenshot_image"] else "",
    #                    "fanart": item["series"]["landscape_image"]["full_url"],
    #                    "mode": "videoplay"},
    #                   is_folder=False)
    #
    # # show next page button
    # if len(req["data"]) >= 30:
    #     view.add_item(args,
    #                   {"title": args.addon.getLocalizedString(30044),
    #                    "offset": int(getattr(args, "offset", 0)) + 30,
    #                    "mode": args.mode},
    #                   is_folder=True)
    #
    # view.endofdirectory(args)
    return True


def listSeries(args, mode, api: API):
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


def listFilter(args, mode, api: API):
    """ view all anime from selected mode
    """

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


def viewSeries(args, api: API):
    """ view all seasons/arcs of an anime
    """
    # api request
    #    payload = {"series_id": args.series_id,
    #               "fields":    "collection.name,collection.collection_id,collection.description,collection.media_type,collection.created, \
    #                             collection.season,collection.complete,collection.portrait_image,collection.landscape_image"}
    #    req = api.request(args, "list_collections", payload)

    req = api.make_request(
        method="GET",
        url=api.SEASONS_ENDPOINT.format(api.account_data.cms.bucket),
        params={
            "locale": args.subtitle,
            "series_id": args.series_id
        }
    )

    # check for error
    if "error" in req:
        view.add_item(args, {"title": args.addon.getLocalizedString(30061)})
        view.end_of_directory(args)
        return False

    # display media
    for item in req["items"]:
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
                "genre": "",  # item["media_type"],
                "aired": "",  # item["created"][:10],
                "premiered": "",  # item["created"][:10],
                "status": u"Completed" if item["is_complete"] else u"Continuing",
                "thumb": args.thumb,
                "fanart": args.fanart,
                "mode": "episodes"
            },
            is_folder=True
        )

    view.end_of_directory(args)
    return True


def viewEpisodes(args, api: API):
    """ view all episodes of season
    """
    # api request
    # payload = {"collection_id": args.collection_id,
    # "limit":         30,
    # "offset":        int(getattr(args, "offset", 0)),
    # "fields":        "media.name,media.media_id,media.collection_id,media.collection_name,media.description,media.episode_number,media.created,media.series_id, \
    # media.screenshot_image,media.premium_only,media.premium_available,media.available,media.premium_available,media.duration,media.playhead"}
    # req = api.request(args, "list_media", payload)

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
        episode_ids.append(item["id"])

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
        stream_id = utils.get_stream_id_from_url(item["__links__"]["streams"]["href"])
        if stream_id is None:
            xbmc.log(
                "[PLUGIN] Crunchyroll | Error : failed to fetch stream_id for %s" % (item["series_title"]),
                xbmc.LOGINFO
            )
            continue

        # add to view
        view.add_item(
            args,
            {
                "title": item["series_title"] + " #" + str(item["episode_number"]) + " - " + item["title"],
                "tvshowtitle": item["series_title"],
                "duration": item["duration_ms"],
                "playcount": utils.get_watched_status_from_playheads_data(req_playheads, item["id"]),
                "episode": item["episode_number"],
                "episode_id": item["id"],
                "collection_id": args.collection_id,
                "series_id": item["series_id"],
                "plot": item["description"],
                "plotoutline": item["description"],
                "aired": item["episode_air_date"][:10],
                "premiered": item["availability_starts"][:10],  # ???
                "thumb": item["images"]["thumbnail"][-1][-1]["source"],  # that's usually 1080p, which could be improved
                "fanart": args.fanart,
                "mode": "videoplay",
                # note that for fetching streams we need a special guid, not the episode_id
                "stream_id": stream_id,
                "playhead": None
            },
            is_folder=False
        )

    # @todo: do we really need this?
    # show next page button
    # if len(req["data"]) >= 30:
    #    view.add_item(args,
    #                  {"title":         args.addon.getLocalizedString(30044),
    #                   "collection_id": args.collection_id,
    #                   "offset":        int(getattr(args, "offset", 0)) + 30,
    #                   "thumb":         args.thumb,
    #                   "fanart":        args.fanart,
    #                   "mode":          args.mode},
    #                  is_folder=True)

    view.end_of_directory(args)
    return True


def startplayback(args, api: API):
    """ plays an episode
    """
    # api request streams
    req = api.make_request(
        method="GET",
        url=api.STREAMS_ENDPOINT.format(api.account_data.cms.bucket, args.stream_id),
        params={
            "locale": args.subtitle
        }
    )

    # check for error
    if "error" in req:
        item = xbmcgui.ListItem(getattr(args, "title", "Title not provided"))
        xbmcplugin.setResolvedUrl(int(args.argv[1]), False, item)
        xbmcgui.Dialog().ok(args.addonname, args.addon.getLocalizedString(30064))
        return False

    ##############################
    # get stream url
    ##############################

    # @TODO: there are tons of different stream types. not sure which one to pick...
    # adaptive_dash
    # adaptive_hls - i chose this, which works for me
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

    try:
        url = req["streams"]["adaptive_hls"][args.subtitle]["url"]
    except IndexError:
        item = xbmcgui.ListItem(getattr(args, "title", "Title not provided"))
        xbmcplugin.setResolvedUrl(int(args.argv[1]), False, item)
        xbmcgui.Dialog().ok(args.addonname, args.addon.getLocalizedString(30064))
        return False

    # prepare playback
    item = xbmcgui.ListItem(getattr(args, "title", "Title not provided"), path=url)
    item.setMimeType("application/vnd.apple.mpegurl")
    item.setContentLookup(False)

    # inputstream adaptive
    is_helper = inputstreamhelper.Helper("hls")
    if is_helper.check_inputstream():
        item.setProperty("inputstream", "inputstream.adaptive")
        item.setProperty("inputstream.adaptive.manifest_type", "hls")
        # start playback
        xbmcplugin.setResolvedUrl(int(args.argv[1]), True, item)

        # wait for playback
        # xbmcgui.Dialog().notification(args.addonname, args.addon.getLocalizedString(30066), xbmcgui.NOTIFICATION_INFO)
        if wait_for_playback(10):
            # if successful wait more
            xbmc.sleep(3000)

    # @TODO: fallbacks not tested

    # start fallback
    if not wait_for_playback(2):
        # start without inputstream adaptive
        xbmc.log("[PLUGIN] %s: Inputstream Adaptive failed, trying directly with kodi" % args.addonname, xbmc.LOGDEBUG)
        item.setProperty("inputstream", "")
        xbmc.Player().play(url, item)

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
            xbmc.log("[PLUGIN] %s: Timeout reached, video did not start in 30 seconds" % args.addonname, xbmc.LOGERROR)
            # xbmcgui.Dialog().ok(args.addonname, args.addon.getLocalizedString(30064))
            return

        # ask if user want to continue playback
        if args.playhead and args.duration:
            resume = int(int(args.playhead) / (int(args.duration) / 1000) * 100)
            if 5 <= resume <= 90:
                player.pause()
                if xbmcgui.Dialog().yesno(args.addonname, args.addon.getLocalizedString(30065) % int(resume)):
                    player.seekTime(float(args.playhead) - 5)
                player.pause()

        # update playtime at crunchyroll
        try:
            while url == player.getPlayingFile():
                # wait 10 seconds
                xbmc.sleep(10000)

                if url == player.getPlayingFile():
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
                    except (ssl.SSLError, URLError):
                        # catch timeout exception
                        pass
        except RuntimeError:
            xbmc.log("[PLUGIN] %s: Playback aborted" % args.addonname, xbmc.LOGDEBUG)


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
