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

import inputstreamhelper # noqa
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from . import controller
from . import utils
from . import view
from .api import API


def main(argv):
    """Main function for the addon
    """
    args = utils.parse(argv)

    # inputstream adaptive settings
    if args.get_arg('mode') == "hls":
        is_helper = inputstreamhelper.Helper("hls")
        if is_helper.check_inputstream():
            xbmcaddon.Addon(id="inputstream.adaptive").openSettings()
        return True

    # get account information
    username = args.addon.getSetting("crunchyroll_username")
    password = args.addon.getSetting("crunchyroll_password")
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
    args._subtitle = utils.convert_subtitle_index_to_string(args.addon.getSetting("subtitle_language"))
    args._subtitle_fallback = utils.convert_subtitle_index_to_string(
        args.addon.getSetting("subtitle_language_fallback"))

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
            return check_mode(args, api)
        else:
            # login failed
            utils.crunchy_log(args, "Login failed", xbmc.LOGERROR)
            view.add_item(args, {"title": args.addon.getLocalizedString(30060)})
            view.end_of_directory(args)
            xbmcgui.Dialog().ok(args.addon_name, args.addon.getLocalizedString(30060))
            return False


def check_mode(args, api: API):
    """Run mode-specific functions
    """
    if args.get_arg('mode'):
        mode = args.get_arg('mode')
    elif args.get_arg('id'):
        # call from other plugin
        mode = "videoplay"
        args.set_arg('url', "/media-" + args.get_arg('id'))
    elif args.get_arg('url'):
        # call from other plugin
        mode = "videoplay"
        args.set_arg('url', args.get_arg('url')[26:])  # @todo: does this actually work? truncated?
    else:
        mode = None

    if not mode:
        show_main_menu(args)

    elif mode == "queue":
        controller.show_queue(args, api)
    elif mode == "search":
        controller.search_anime(args, api)
    elif mode == "history":
        controller.show_history(args, api)
    elif mode == "resume":
        controller.show_resume_episodes(args, api)
    # elif mode == "random":
    #     controller.showRandom(args, api)

    elif mode == "anime":
        show_main_category(args, "anime")
    elif mode == "drama":
        show_main_category(args, "drama")

    # elif mode == "featured":  # https://www.crunchyroll.com/content/v2/discover/account_id/home_feed -> hero_carousel ?
    #     controller.list_series(args, "featured", api)
    elif mode == "popular":  # DONE
        controller.list_filter(args, api)
    # elif mode == "simulcast":  # https://www.crunchyroll.com/de/simulcasts/seasons/fall-2023 ???
    #     controller.listSeries(args, "simulcast", api)
    # elif mode == "updated":
    #    controller.listSeries(args, "updated", api)
    elif mode == "newest":
        controller.list_filter(args, api)
    elif mode == "alpha":
        controller.list_filter(args, api)
    elif mode == "season":  # DONE
        controller.list_anime_seasons(args, api)
    elif mode == "genre":  # DONE
        controller.list_filter(args, api)

    elif mode == "seasons":
        controller.view_season(args, api)
    elif mode == "episodes":
        controller.view_episodes(args, api)
    elif mode == "videoplay":
        controller.start_playback(args, api)
    elif mode == "add_to_queue":
        controller.add_to_queue(args, api)
    # elif mode == "remove_from_queue":
    #     controller.remove_from_queue(args, api)
    elif mode == "crunchylists_lists":
        controller.crunchylists_lists(args, api)
    elif mode == 'crunchylists_item':
        controller.crunchylists_item(args, api)
    else:
        # unknown mode
        utils.crunchy_log(args, "Failed in check_mode '%s'" % str(mode), xbmc.LOGERROR)
        xbmcgui.Dialog().notification(args.addon_name, args.addon.getLocalizedString(30061), xbmcgui.NOTIFICATION_ERROR)
        show_main_menu(args)


def show_main_menu(args):
    """Show main menu
    """
    view.add_item(args,
                  {"title": args.addon.getLocalizedString(30040),
                   "mode": "queue"})
    view.add_item(args,
                  {"title": args.addon.getLocalizedString(30047),
                   "mode": "resume"})
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
    view.add_item(args,
                  {"title": args.addon.getLocalizedString(30049),
                   "mode": "crunchylists_lists"})
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
    view.add_item(args,
                  {"title": args.addon.getLocalizedString(30055),
                   "category_filter": "alphabetical",
                   "items_per_page": 100,
                   "mode": "alpha",
                   "genre": genre})
    view.add_item(args,
                  {"title": args.addon.getLocalizedString(30057),
                   "mode": "season",
                   "genre": genre})
    view.add_item(args,
                  {"title": args.addon.getLocalizedString(30056),
                   "mode": "genre",
                   "genre": genre})
    view.end_of_directory(args)
