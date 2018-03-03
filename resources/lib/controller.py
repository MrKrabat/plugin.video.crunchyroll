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

import re
import ssl
import sys
import json
import time
import inputstreamhelper

import xbmc
import xbmcgui
import xbmcplugin

from . import api
from . import view


def showQueue(args):
    """ shows anime queue/playlist
    """
    # api request
    payload = {"media_types": "anime|drama",
               "fields":      "media.name,media.media_id,media.collection_id,media.collection_name,media.description,media.episode_number,media.created, \
                               media.screenshot_image,media.premium_only,media.premium_available,media.available,media.premium_available,media.duration, \
                               series.series_id,series.year,series.publisher_name,series.rating,series.genres,series.landscape_image"}
    req = api.request(args, "queue", payload)

    # check for error
    if req["error"]:
        view.add_item(args, {"title": args._addon.getLocalizedString(30061)})
        view.endofdirectory()
        return False

    # display media
    for item in req["data"]:
        # video no longer available
        if not ("most_likely_media" in item and "series" in item and item["most_likely_media"]["available"] and item["most_likely_media"]["premium_available"]):
            continue

        # add to view
        view.add_item(args,
                      {"title":         item["most_likely_media"]["collection_name"] + " #" + item["most_likely_media"]["episode_number"] + " - " + item["most_likely_media"]["name"],
                       "tvshowtitle":   item["most_likely_media"]["collection_name"],
                       "duration":      item["most_likely_media"]["duration"],
                       "playcount":     1 if (100/float(item["most_likely_media"]["duration"]))*int(item["playhead"]) > 90 else 0,
                       "episode":       item["most_likely_media"]["episode_number"],
                       "episode_id":    item["most_likely_media"]["media_id"],
                       "collection_id": item["most_likely_media"]["collection_id"],
                       "series_id":     item["series"]["series_id"],
                       "plot":          item["most_likely_media"]["description"],
                       "plotoutline":   item["most_likely_media"]["description"],
                       "genre":         ", ".join(item["series"]["genres"]),
                       "year":          item["series"]["year"],
                       "aired":         item["most_likely_media"]["created"][:10],
                       "premiered":     item["most_likely_media"]["created"][:10],
                       "studio":        item["series"]["publisher_name"],
                       "rating":        int(item["series"]["rating"])/10.0,
                       "thumb":         item["most_likely_media"]["screenshot_image"]["fwidestar_url"] if item["most_likely_media"]["premium_only"] else item["most_likely_media"]["screenshot_image"]["full_url"],
                       "fanart":        item["series"]["landscape_image"]["full_url"],
                       "mode":          "videoplay"},
                      isFolder=False)

    view.endofdirectory()
    return True


def searchAnime(args):
    """Search for anime
    """
    # ask for search string
    if not hasattr(args, "search"):
        d = xbmcgui.Dialog().input(args._addon.getLocalizedString(30041), type=xbmcgui.INPUT_ALPHANUM)
        if not d:
            return
    else:
        d = args.search

    # api request
    payload = {"media_types": "anime|drama",
               "q":           d,
               "limit":       30,
               "offset":      int(getattr(args, "offset", 0)),
               "fields":      "series.name,series.series_id,series.description,series.year,series.publisher_name, \
                               series.genres,series.portrait_image,series.landscape_image"}
    req = api.request(args, "autocomplete", payload)

    # check for error
    if req["error"]:
        view.add_item(args, {"title": args._addon.getLocalizedString(30061)})
        view.endofdirectory()
        return False

    # display media
    for item in req["data"]:
        # add to view
        view.add_item(args,
                      {"title":       item["name"],
                       "tvshowtitle": item["name"],
                       "series_id":   item["series_id"],
                       "plot":        item["description"],
                       "plotoutline": item["description"],
                       "genre":       ", ".join(item["genres"]),
                       "year":        item["year"],
                       "studio":      item["publisher_name"],
                       "thumb":       item["portrait_image"]["full_url"],
                       "fanart":      item["landscape_image"]["full_url"],
                       "mode":        "series"},
                      isFolder=True)

    # show next page button
    if len(req["data"]) >= 30:
        view.add_item(args,
                      {"title":  args._addon.getLocalizedString(30044),
                       "offset": int(getattr(args, "offset", 0)) + 30,
                       "search": d,
                       "mode":   args.mode},
                      isFolder=True)

    view.endofdirectory()
    return True


def showHistory(args):
    """ shows history of watched anime
    """
    # api request
    payload = {"media_types": "anime|drama",
               "limit":       30,
               "offset":      int(getattr(args, "offset", 0)),
               "fields":      "media.name,media.media_id,media.collection_id,media.collection_name,media.description,media.episode_number,media.created, \
                               media.screenshot_image,media.premium_only,media.premium_available,media.available,media.premium_available,media.duration,media.playhead, \
                               series.series_id,series.year,series.publisher_name,series.rating,series.genres,series.landscape_image"}
    req = api.request(args, "recently_watched", payload)

    # check for error
    if req["error"]:
        view.add_item(args, {"title": args._addon.getLocalizedString(30061)})
        view.endofdirectory()
        return False

    # display media
    for item in req["data"]:
        # video no longer available
        if not ("media" in item and "series" in item and item["media"]["available"] and item["media"]["premium_available"]):
            continue

        # add to view
        view.add_item(args,
                      {"title":         item["media"]["collection_name"] + " #" + item["media"]["episode_number"] + " - " + item["media"]["name"],
                       "tvshowtitle":   item["media"]["collection_name"],
                       "duration":      item["media"]["duration"],
                       "playcount":     1 if (100/float(item["media"]["duration"]))*int(item["media"]["playhead"]) > 90 else 0,
                       "episode":       item["media"]["episode_number"],
                       "episode_id":    item["media"]["media_id"],
                       "collection_id": item["media"]["collection_id"],
                       "series_id":     item["series"]["series_id"],
                       "plot":          item["media"]["description"],
                       "plotoutline":   item["media"]["description"],
                       "genre":         ", ".join(item["series"]["genres"]),
                       "year":          item["series"]["year"],
                       "aired":         item["media"]["created"][:10],
                       "premiered":     item["media"]["created"][:10],
                       "studio":        item["series"]["publisher_name"],
                       "rating":        int(item["series"]["rating"])/10.0,
                       "thumb":         item["media"]["screenshot_image"]["fwidestar_url"] if item["media"]["premium_only"] else item["media"]["screenshot_image"]["full_url"],
                       "fanart":        item["series"]["landscape_image"]["full_url"],
                       "mode":          "videoplay"},
                      isFolder=False)

    # show next page button
    if len(req["data"]) >= 30:
        view.add_item(args,
                      {"title":  args._addon.getLocalizedString(30044),
                       "offset": int(getattr(args, "offset", 0)) + 30,
                       "mode":   args.mode},
                      isFolder=True)

    view.endofdirectory()
    return True


def listSeries(args, mode):
    """ view all anime from selected mode
    """
    # api request
    payload = {"media_type": args.genre,
               "filter":     mode,
               "limit":      30,
               "offset":     int(getattr(args, "offset", 0)),
               "fields":     "series.name,series.series_id,series.description,series.year,series.publisher_name, \
                              series.genres,series.portrait_image,series.landscape_image"}
    req = api.request(args, "list_series", payload)

    # check for error
    if req["error"]:
        view.add_item(args, {"title": args._addon.getLocalizedString(30061)})
        view.endofdirectory()
        return False

    # display media
    for item in req["data"]:
        # add to view
        view.add_item(args,
                      {"title":       item["name"],
                       "tvshowtitle": item["name"],
                       "series_id":   item["series_id"],
                       "plot":        item["description"],
                       "plotoutline": item["description"],
                       "genre":       ", ".join(item["genres"]),
                       "year":        item["year"],
                       "studio":      item["publisher_name"],
                       "thumb":       item["portrait_image"]["full_url"],
                       "fanart":      item["landscape_image"]["full_url"],
                       "mode":        "series"},
                      isFolder=True)

    # show next page button
    if len(req["data"]) >= 30:
        view.add_item(args,
                      {"title":  args._addon.getLocalizedString(30044),
                       "offset": int(getattr(args, "offset", 0)) + 30,
                       "search": getattr(args, "search", ""),
                       "mode":   args.mode},
                      isFolder=True)

    view.endofdirectory()
    return True


def listFilter(args, mode):
    """ view all anime from selected mode
    """
    # test if filter is selected
    if hasattr(args, "search"):
        return listSeries(args, "tag:" + args.search)

    # api request
    payload = {"media_type": args.genre}
    req = api.request(args, "categories", payload)

    # check for error
    if req["error"]:
        view.add_item(args, {"title": args._addon.getLocalizedString(30061)})
        view.endofdirectory()
        return False

    # display media
    for item in req["data"][mode]:
        # add to view
        view.add_item(args,
                      {"title":  item["label"],
                       "search": item["tag"],
                       "mode":   args.mode},
                      isFolder=True)

    view.endofdirectory()
    return True


def viewSeries(args):
    """ view all seasons/arcs of an anime
    """
    # api request
    payload = {"series_id": args.series_id,
               "fields":    "collection.name,collection.collection_id,collection.description,collection.media_type,collection.created, \
                             collection.season,collection.complete,collection.portrait_image,collection.landscape_image"}
    req = api.request(args, "list_collections", payload)

    # check for error
    if req["error"]:
        view.add_item(args, {"title": args._addon.getLocalizedString(30061)})
        view.endofdirectory()
        return False

    # display media
    for item in req["data"]:
        # add to view
        view.add_item(args,
                      {"title":         item["name"],
                       "tvshowtitle":   item["name"],
                       "season":        item["season"],
                       "collection_id": item["collection_id"],
                       "series_id":     args.series_id,
                       "plot":          item["description"],
                       "plotoutline":   item["description"],
                       "genre":         item["media_type"],
                       "aired":         item["created"][:10],
                       "premiered":     item["created"][:10],
                       "status":        u"Completed" if item["complete"] else u"Continuing",
                       "thumb":         item["portrait_image"]["full_url"] if item["portrait_image"] else args.thumb,
                       "fanart":        item["landscape_image"]["full_url"] if item["landscape_image"] else args.fanart,
                       "mode":          "episodes"},
                      isFolder=True)

    view.endofdirectory()
    return True


def viewEpisodes(args):
    """ view all episodes of season
    """
    # api request
    payload = {"collection_id": args.collection_id,
               "limit":         30,
               "offset":        int(getattr(args, "offset", 0)),
               "fields":        "media.name,media.media_id,media.collection_id,media.collection_name,media.description,media.episode_number,media.created,media.series_id, \
                                 media.screenshot_image,media.premium_only,media.premium_available,media.available,media.premium_available,media.duration,media.playhead"}
    req = api.request(args, "list_media", payload)

    # check for error
    if req["error"]:
        view.add_item(args, {"title": args._addon.getLocalizedString(30061)})
        view.endofdirectory()
        return False

    # display media
    for item in req["data"]:
        # add to view
        view.add_item(args,
                      {"title":         item["collection_name"] + " #" + item["episode_number"] + " - " + item["name"],
                       "tvshowtitle":   item["collection_name"],
                       "duration":      item["duration"],
                       "playcount":     1 if (100/float(item["duration"]))*int(item["playhead"]) > 90 else 0,
                       "episode":       item["episode_number"],
                       "episode_id":    item["media_id"],
                       "collection_id": args.collection_id,
                       "series_id":     item["series_id"],
                       "plot":          item["description"],
                       "plotoutline":   item["description"],
                       "aired":         item["created"][:10],
                       "premiered":     item["created"][:10],
                       "thumb":         item["screenshot_image"]["fwidestar_url"] if item["premium_only"] else item["screenshot_image"]["full_url"],
                       "fanart":        args.fanart,
                       "mode":          "videoplay"},
                      isFolder=False)

    # show next page button
    if len(req["data"]) >= 30:
        view.add_item(args,
                      {"title":         args._addon.getLocalizedString(30044),
                       "collection_id": args.collection_id,
                       "offset":        int(getattr(args, "offset", 0)) + 30,
                       "thumb":         args.thumb,
                       "fanart":        args.fanart,
                       "mode":          args.mode},
                      isFolder=True)

    view.endofdirectory()
    return True


def startplayback(args):
    """ plays an episode
    """
    # api request
    payload = {"media_id": args.episode_id,
               "fields":   "media.duration,media.playhead,media.stream_data"}
    req = api.request(args, "info", payload)

    # check for error
    if req["error"]:
        item = xbmcgui.ListItem(getattr(args, "title", "Title not provided"))
        xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, item)
        return False

    # get stream url
    url = req["data"]["stream_data"]["streams"][0]["url"]
    if not args._quality == "adaptive":
        matches = re.findall(r",([0-9]+\.mp4)", url)
        url = re.sub(r"(,[0-9]+\.mp4){5}", "," + matches[args._quality], url)

    # prepare playback
    item = xbmcgui.ListItem(getattr(args, "title", "Title not provided"), path=url)
    item.setMimeType("application/vnd.apple.mpegurl")
    item.setContentLookup(False)

    # inputstream adaptive
    is_helper = inputstreamhelper.Helper("hls")
    if is_helper.check_inputstream():
        item.setProperty("inputstreamaddon", "inputstream.adaptive")
        item.setProperty("inputstream.adaptive.manifest_type", "hls")
        # start playback
        xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)

        # wait for playback
        #xbmcgui.Dialog().notification(args._addonname, args._addon.getLocalizedString(30066), xbmcgui.NOTIFICATION_INFO)
        if waitForPlayback(10):
            # if successful wait more
            xbmc.sleep(3000)

    # start fallback
    if not waitForPlayback(2):
        # start without inputstream adaptive
        xbmc.log("[PLUGIN] %s: Inputstream Adaptive failed, trying directly with kodi" % args._addonname, xbmc.LOGDEBUG)
        item.setProperty("inputstreamaddon", "")
        xbmc.Player().play(url, item)

    # sync playtime with crunchyroll
    if args._addon.getSetting("sync_playtime") == "true":
        # wait for video to begin
        player = xbmc.Player()
        if not waitForPlayback(30):
            xbmc.log("[PLUGIN] %s: Timeout reached, video did not start in 30 seconds" % args._addonname, xbmc.LOGERROR)
            return

        # ask if user want to continue playback
        resume = (100/float(req["data"]["duration"])) * int(req["data"]["playhead"])
        if resume >= 5 and resume <= 90:
            player.pause()
            if xbmcgui.Dialog().yesno(args._addonname, args._addon.getLocalizedString(30065) % int(resume)):
                player.seekTime(float(req["data"]["playhead"]) - 5)
            player.pause()

        # update playtime at crunchyroll
        try:
            while url == player.getPlayingFile():
                # wait 10 seconds
                xbmc.sleep(10000)

                if url == player.getPlayingFile():
                    # api request
                    payload = {"event":    "playback_status",
                               "media_id": args.episode_id,
                               "playhead": int(player.getTime())}
                    try:
                        api.request(args, "log", payload)
                    except ssl.SSLError:
                        # catch timeout exception
                        pass
        except RuntimeError:
            xbmc.log("[PLUGIN] %s: Playback aborted" % args._addonname, xbmc.LOGDEBUG)


def waitForPlayback(timeout=30):
    """ function that waits for playback
    """
    timer = time.time() + timeout
    while not xbmc.getCondVisibility("Player.IsInternetStream"):
        xbmc.sleep(50)
        # timeout to prevent infinite loop
        if time.time() > timer:
            return False

    return True
