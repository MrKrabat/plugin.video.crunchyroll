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

import sys
import time

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
               "fields":      "media.name,media.media_id,media.description,media.episode_number,media.created,media.media_type,media.screenshot_image, \
                               media.premium_only,media.premium_available,media.available,media.premium_available,media.duration, \
                               series.name,series.series_id,series.year,series.publisher_name,series.rating,series.portrait_image"}
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

        view.add_item(args,
                      {"title":       item["series"]["name"] + " #" + item["most_likely_media"]["episode_number"] + " - " + item["most_likely_media"]["name"],
                       "tvshowtitle": item["series"]["name"],
                       "duration":    item["most_likely_media"]["duration"],
                       "playcount":   1 if (100/int(item["most_likely_media"]["duration"]))*int(item["playhead"]) > 90 else 0,
                       "episode":     item["most_likely_media"]["episode_number"],
                       "episode_id":  item["most_likely_media"]["media_id"],
                       "series_id":   item["series"]["series_id"],
                       "plot":        item["most_likely_media"]["description"],
                       "plotoutline": item["most_likely_media"]["description"],
                       "genre":       item["most_likely_media"]["media_type"],
                       "year":        item["series"]["year"],
                       "aired":       item["most_likely_media"]["created"][:10],
                       "premiered":   item["most_likely_media"]["created"][:10],
                       "studio":      item["series"]["publisher_name"],
                       "rating":      int(item["series"]["rating"])/10.0,
                       "thumb":       item["most_likely_media"]["screenshot_image"]["fwidestar_url"] if item["most_likely_media"]["premium_only"] else item["most_likely_media"]["screenshot_image"]["full_url"],
                       "fanart":      item["series"]["portrait_image"]["full_url"],
                       "mode":        "videoplay"},
                      isFolder=False)

    view.endofdirectory()
    return True


def showHistory(args):
    """ shows history of watched animes
    """
    # api request
    payload = {"media_types": "anime|drama",
               "fields":      "media.name,media.media_id,media.description,media.episode_number,media.created,media.media_type,media.screenshot_image, \
                               media.premium_only,media.premium_available,media.available,media.premium_available,media.duration, \
                               series.name,series.series_id,series.year,series.publisher_name,series.rating,series.portrait_image"}
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

        view.add_item(args,
                      {"title":       item["series"]["name"] + " #" + item["media"]["episode_number"] + " - " + item["media"]["name"],
                       "tvshowtitle": item["series"]["name"],
                       "duration":    item["media"]["duration"],
                       "playcount":   1 if (100/int(item["media"]["duration"]))*int(item["playhead"]) > 90 else 0,
                       "episode":     item["media"]["episode_number"],
                       "episode_id":  item["media"]["media_id"],
                       "series_id":   item["series"]["series_id"],
                       "plot":        item["media"]["description"],
                       "plotoutline": item["media"]["description"],
                       "genre":       item["media"]["media_type"],
                       "year":        item["series"]["year"],
                       "aired":       item["media"]["created"][:10],
                       "premiered":   item["media"]["created"][:10],
                       "studio":      item["series"]["publisher_name"],
                       "rating":      int(item["series"]["rating"])/10.0,
                       "thumb":       item["media"]["screenshot_image"]["fwidestar_url"] if item["media"]["premium_only"] else item["media"]["screenshot_image"]["full_url"],
                       "fanart":      item["series"]["portrait_image"]["full_url"],
                       "mode":        "videoplay"},
                      isFolder=False)

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
    for stream in req["data"]["stream_data"]["streams"]:
        # TODO: get user selected quality
        url = stream["url"]
        break

    # start playback
    item = xbmcgui.ListItem(getattr(args, "title", "Title not provided"), path=url)
    item.setMimeType("application/vnd.apple.mpegurl")
    item.setContentLookup(False)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)

    if args._addon.getSetting("sync_playtime") == "true":
        # wait for video to begin
        player = xbmc.Player()
        timeout = time.time() + 20
        while not xbmc.getCondVisibility("Player.IsInternetStream"):
            xbmc.sleep(50)
            # timeout to prevent infinite loop
            if time.time() > timeout:
                xbmc.log("[PLUGIN] %s: Timeout reached, video did not start in 20 seconds" % args._addonname, xbmc.LOGERROR)
                return

        # ask if user want to continue playback
        resume = (100/int(req["data"]["duration"])) * int(req["data"]["playhead"])
        if resume >= 5 and resume <= 90:
            player.pause()
            if xbmcgui.Dialog().yesno(args._addonname, args._addon.getLocalizedString(30065) % resume):
                player.seekTime(int(req["data"]["playhead"]) - 5)
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
                    api.request(args, "log", payload)
        except RuntimeError:
            xbmc.log("[PLUGIN] %s: Playback aborted" % args._addonname, xbmc.LOGDEBUG)
