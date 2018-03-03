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
import random
import inputstreamhelper

import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

from . import api
from . import view
from . import model
from . import controller


def main():
    """Main function for the addon
    """
    args = model.parse()

    # inputstream adaptive settings
    if hasattr(args, "mode") and args.mode == "hls":
        is_helper = inputstreamhelper.Helper("hls")
        if is_helper.check_inputstream():
            xbmcaddon.Addon(id="inputstream.adaptive").openSettings()
        return True

    # get account informations
    username = args._addon.getSetting("crunchyroll_username")
    password = args._addon.getSetting("crunchyroll_password")
    args._session_id = args._addon.getSetting("session_id")
    args._auth_token = args._addon.getSetting("auth_token")
    args._device_id  = args._addon.getSetting("device_id")
    if not args._device_id:
        char_set  = "0123456789abcdefghijklmnopqrstuvwxyz0123456789"
        args._device_id = "".join(random.sample(char_set, 8)) + "-KODI-" + "".join(random.sample(char_set, 4)) + "-" + "".join(random.sample(char_set, 4)) + "-" + "".join(random.sample(char_set, 12))
        args._addon.setSetting("device_id", args._device_id)

    # get subtitle language
    args._subtitle = args._addon.getSetting("subtitle_language")
    if args._subtitle == "0":
        args._subtitle = "enUS"
    elif args._subtitle == "1":
        args._subtitle = "enGB"
    elif args._subtitle == "2":
        args._subtitle = "esLA"
    elif args._subtitle == "3":
        args._subtitle = "esES"
    elif args._subtitle == "4":
        args._subtitle = "ptBR"
    elif args._subtitle == "5":
        args._subtitle = "ptPT"
    elif args._subtitle == "6":
        args._subtitle = "frFR"
    elif args._subtitle == "7":
        args._subtitle = "deDE"
    elif args._subtitle == "8":
        args._subtitle = "arME"
    elif args._subtitle == "9":
        args._subtitle = "itIT"
    elif args._subtitle == "10":
        args._subtitle = "ruRU"
    else:
        args._subtitle = "enUS"

    # get video quality
    args._quality = args._addon.getSetting("video_quality")
    if args._quality == "0":
        args._quality = "adaptive"
    elif args._quality == "1":
        args._quality = 1
    elif args._quality == "2":
        args._quality = 0
    elif args._quality == "3":
        args._quality = 2
    elif args._quality == "4":
        args._quality = 3
    elif args._quality == "5":
        args._quality = 4
    else:
        args._quality = "adaptive"

    if not (username and password):
        # open addon settings
        view.add_item(args, {"title": args._addon.getLocalizedString(30062)})
        view.endofdirectory()
        args._addon.openSettings()
        return False
    else:
        # login
        if api.start(args):
            # list menue
            xbmcplugin.setContent(int(sys.argv[1]), "tvshows")
            check_mode(args)
            api.close(args)
        else:
            # login failed
            xbmc.log("[PLUGIN] %s: Login failed" % args._addonname, xbmc.LOGERROR)
            view.add_item(args, {"title": args._addon.getLocalizedString(30060)})
            view.endofdirectory()
            xbmcgui.Dialog().ok(args._addonname, args._addon.getLocalizedString(30060))
            return False


def check_mode(args):
    """Run mode-specific functions
    """
    if hasattr(args, "mode"):
        mode = args.mode
    elif hasattr(args, "id"):
        # call from other plugin
        mode = "videoplay"
        args.url = "/media-" + args.id
    elif hasattr(args, "url"):
        # call from other plugin
        mode = "videoplay"
        args.url = args.url[26:]
    else:
        mode = None

    if not mode:
        showMainMenue(args)

    elif mode == "queue":
        controller.showQueue(args)
    elif mode == "search":
        controller.searchAnime(args)
    elif mode == "history":
        controller.showHistory(args)
    elif mode == "random":
        controller.showRandom(args)

    elif mode == "anime":
        showMainCategory(args, "anime")
    elif mode == "drama":
        showMainCategory(args, "drama")

    elif mode == "featured":
        controller.listSeries(args, "featured")
    elif mode == "popular":
        controller.listSeries(args, "popular")
    elif mode == "simulcast":
        controller.listSeries(args, "simulcast")
    elif mode == "updated":
        controller.listSeries(args, "updated")
    elif mode == "newest":
        controller.listSeries(args, "newest")
    elif mode == "alpha":
        controller.listSeries(args, "alpha")
    elif mode == "season":
        controller.listFilter(args, "season")
    elif mode == "genre":
        controller.listFilter(args, "genre")

    elif mode == "series":
        controller.viewSeries(args)
    elif mode == "episodes":
        controller.viewEpisodes(args)
    elif mode == "videoplay":
        controller.startplayback(args)
    else:
        # unkown mode
        xbmc.log("[PLUGIN] %s: Failed in check_mode '%s'" % (args._addonname, str(mode)), xbmc.LOGERROR)
        xbmcgui.Dialog().notification(args._addonname, args._addon.getLocalizedString(30061), xbmcgui.NOTIFICATION_ERROR)
        showMainMenue(args)


def showMainMenue(args):
    """Show main menu
    """
    view.add_item(args,
                  {"title": args._addon.getLocalizedString(30040),
                   "mode":  "queue"})
    view.add_item(args,
                  {"title": args._addon.getLocalizedString(30041),
                   "mode":  "search"})
    view.add_item(args,
                  {"title": args._addon.getLocalizedString(30042),
                   "mode":  "history"})
    #view.add_item(args,
    #              {"title": args._addon.getLocalizedString(30043),
    #               "mode":  "random"})
    view.add_item(args,
                  {"title": args._addon.getLocalizedString(30050),
                   "mode":  "anime"})
    view.add_item(args,
                  {"title": args._addon.getLocalizedString(30051),
                   "mode":  "drama"})
    view.endofdirectory()


def showMainCategory(args, genre):
    """Show main category
    """
    view.add_item(args,
                  {"title": args._addon.getLocalizedString(30058),
                   "mode":  "featured",
                   "genre": genre})
    view.add_item(args,
                  {"title": args._addon.getLocalizedString(30052),
                   "mode":  "popular",
                   "genre": genre})
    view.add_item(args,
                  {"title": args._addon.getLocalizedString(30053),
                   "mode":  "simulcast",
                   "genre": genre})
    view.add_item(args,
                  {"title": args._addon.getLocalizedString(30054),
                   "mode":  "updated",
                   "genre": genre})
    view.add_item(args,
                  {"title": args._addon.getLocalizedString(30059),
                   "mode":  "newest",
                   "genre": genre})
    view.add_item(args,
                  {"title": args._addon.getLocalizedString(30055),
                   "mode":  "alpha",
                   "genre": genre})
    view.add_item(args,
                  {"title": args._addon.getLocalizedString(30057),
                   "mode":  "season",
                   "genre": genre})
    view.add_item(args,
                  {"title": args._addon.getLocalizedString(30056),
                   "mode":  "genre",
                   "genre": genre})
    view.endofdirectory()
