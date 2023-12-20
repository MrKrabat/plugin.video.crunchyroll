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

import random
import inputstreamhelper

import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

from .api import API
from . import view
from . import utils
from . import controller


def main(argv):
    """Main function for the addon
    """
    args = utils.parse(argv)

    # inputstream adaptive settings
    if hasattr(args, "mode") and args.mode == "hls":
        is_helper = inputstreamhelper.Helper("hls")
        if is_helper.check_inputstream():
            xbmcaddon.Addon(id="inputstream.adaptive").openSettings()
        return True

    # get account information
    username = args.addon.getSetting("crunchyroll_username")
    password = args.addon.getSetting("crunchyroll_password")
    # args._session_id = args.addon.getSetting("session_id")
    # args._auth_token = args.addon.getSetting("auth_token")
    args._device_id = args.addon.getSetting("device_id")
    if not args.device_id:
        char_set = "0123456789abcdefghijklmnopqrstuvwxyz0123456789"
        args._device_id = (
                "".join(random.sample(char_set, 8)) +
                "-KODI-" +
                "".join(random.sample(char_set, 4)) +
                "-" +
                "".join(random.sample(char_set, 4)) +
                "-" +
                "".join(random.sample(char_set, 12))
        )
        args.addon.setSetting("device_id", args.device_id)

    # get subtitle language
    args._subtitle = args.addon.getSetting("subtitle_language")
    if args.subtitle == "0":
        args._subtitle = "en-US"
    elif args.subtitle == "1":
        args._subtitle = "en-GB"
    elif args.subtitle == "2":
        args._subtitle = "es-LA"
    elif args.subtitle == "3":
        args._subtitle = "es-ES"
    elif args.subtitle == "4":
        args._subtitle = "pt-BR"
    elif args.subtitle == "5":
        args._subtitle = "pt-PT"
    elif args.subtitle == "6":
        args._subtitle = "fr-FR"
    elif args.subtitle == "7":
        args._subtitle = "de-DE"
    elif args.subtitle == "8":
        args._subtitle = "ar-ME"
    elif args.subtitle == "9":
        args._subtitle = "it-IT"
    elif args.subtitle == "10":
        args._subtitle = "ru-RU"
    else:
        args._subtitle = "en-US"

    api = API(
        args=args,
        locale=args.subtitle
    )

    if not (username and password):
        # open addon settings
        view.add_item(args, {"title": args.addon.getLocalizedString(30062)})
        view.end_of_directory(args)
        args.addon.openSettings()
        return False
    else:
        # login
        if api.start():
            # list menu
            xbmcplugin.setContent(int(args.argv[1]), "tvshows")
            check_mode(args, api)
            api.close()
        else:
            # login failed
            xbmc.log("[PLUGIN] %s: Login failed" % args.addonname, xbmc.LOGERROR)
            view.add_item(args, {"title": args.addon.getLocalizedString(30060)})
            view.end_of_directory(args)
            xbmcgui.Dialog().ok(args.addonname, args.addon.getLocalizedString(30060))
            return False


def check_mode(args, api: API):
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
        controller.show_queue(args, api)
    elif mode == "search":
        controller.search_anime(args, api)
    elif mode == "history":
        controller.show_history(args, api)
    # elif mode == "random":
    #     controller.showRandom(args, api)

    elif mode == "anime":
        show_main_category(args, "anime")
    elif mode == "drama":
        show_main_category(args, "drama")

    elif mode == "featured":  # https://www.crunchyroll.com/content/v2/discover/account_id/home_feed -> hero_carousel ?
        controller.listSeries(args, "featured", api)
    elif mode == "popular":  # DONE
       # setattr(args, "category_filter", "popular")  # @todo: can this be done better? :o)
        controller.list_filter(args, "popular", api)
    #elif mode == "simulcast":  # https://www.crunchyroll.com/de/simulcasts/seasons/fall-2023 ???
    #    controller.listSeries(args, "simulcast", api)
    #elif mode == "updated":
    #    controller.listSeries(args, "updated", api)
    elif mode == "newest":
       # setattr(args, "category_filter", "newly_added")  # @todo: can this be done better? :o)
        controller.list_filter(args, "newest", api)
    #elif mode == "alpha":
    #    controller.listSeries(args, "alpha", api)
    elif mode == "season":  # DONE
        controller.list_seasons(args, "season", api)
    elif mode == "genre":  # DONE
        controller.list_filter(args, "genre", api)

    elif mode == "series":
        controller.view_series(args, api)
    elif mode == "episodes":
        controller.view_episodes(args, api)
    elif mode == "videoplay":
        controller.start_playback(args, api)
    else:
        # unknown mode
        xbmc.log("[PLUGIN] %s: Failed in check_mode '%s'" % (args.addonname, str(mode)), xbmc.LOGERROR)
        xbmcgui.Dialog().notification(args.addonname, args.addon.getLocalizedString(30061), xbmcgui.NOTIFICATION_ERROR)
        showMainMenue(args)


def showMainMenue(args):
    """Show main menu
    """
    view.add_item(args,
                  {"title": args.addon.getLocalizedString(30040),
                   "mode": "queue"})
    view.add_item(args,
                  {"title": args.addon.getLocalizedString(30041),
                   "mode": "search"})
    view.add_item(args,
                  {"title": args.addon.getLocalizedString(30042),
                   "mode": "history"})
    # #view.add_item(args,
    # #              {"title": args.addon.getLocalizedString(30043),
    # #               "mode":  "random"})
    view.add_item(args,
                  {"title": args.addon.getLocalizedString(30050),
                   "mode": "anime"})
    # @TODO: i think there are no longer dramas. should we add music videos and movies?
    # view.add_item(args,
    #              {"title": args.addon.getLocalizedString(30051),
    #               "mode":  "drama"})
    view.end_of_directory(args)


def show_main_category(args, genre):
    """Show main category
    """
    # view.add_item(args,
    #               {"title": args.addon.getLocalizedString(30058),
    #                "mode": "featured",
    #                "category_filter": "popular",
    #                "genre": genre})
    view.add_item(args,
                  {"title": args.addon.getLocalizedString(30052),
                   "category_filter": "popularity",
                   "mode": "popular",
                   "genre": genre})
    # view.add_item(args,
    #               {"title": "TODO | " + args.addon.getLocalizedString(30053),
    #                "mode": "simulcast",
    #                "genre": genre})
    # view.add_item(args,
    #               {"title": "TODO | " + args.addon.getLocalizedString(30054),
    #                "mode": "updated",
    #                "genre": genre})
    view.add_item(args,
                  {"title": args.addon.getLocalizedString(30059),
                   "category_filter": "newly_added",
                   "mode": "newest",
                   "genre": genre})
    # view.add_item(args,
    #               {"title": "TODO | " + args.addon.getLocalizedString(30055),
    #                "mode": "alpha",
    #                "genre": genre})
    view.add_item(args,
                  {"title": args.addon.getLocalizedString(30057),
                   "mode": "season",
                   "genre": genre})
    view.add_item(args,
                  {"title": args.addon.getLocalizedString(30056),
                   "mode": "genre",
                   "genre": genre})
    view.end_of_directory(args)
