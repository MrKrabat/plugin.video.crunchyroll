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

import random
import re

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from . import controller
from . import utils
from . import view
from .globals import G
from .model import CrunchyrollError, LoginError


def main(argv):
    """Main function for the addon
    """

    G.init(argv)

    # inputstream adaptive settings
    if G.args.get_arg('mode') == "hls":
        from inputstreamhelper import Helper  # noqa
        is_helper = Helper("hls")
        if is_helper.check_inputstream():
            xbmcaddon.Addon(id="inputstream.adaptive").openSettings()
        return True

    # get account information
    username = G.args.addon.getSetting("crunchyroll_username")
    password = G.args.addon.getSetting("crunchyroll_password")
    G.args._device_id = G.args.addon.getSetting("device_id")
    if not G.args.device_id:
        char_set = "0123456789abcdefghijklmnopqrstuvwxyz0123456789"
        G.args._device_id = (
                "".join(random.sample(char_set, 8)) +
                "-KODI-" +
                "".join(random.sample(char_set, 4)) +
                "-" +
                "".join(random.sample(char_set, 4)) +
                "-" +
                "".join(random.sample(char_set, 12))
        )
        G.args.addon.setSetting("device_id", G.args.device_id)

    # get subtitle language
    G.args._subtitle = G.args.addon.getSetting("subtitle_language")
    G.args._subtitle_fallback = G.args.addon.getSetting("subtitle_language_fallback")  # @todo: test with empty

    # temporary dialog to notify about subtitle settings change
    # @todo: remove eventually
    if G.args.subtitle is int or G.args.subtitle_fallback is int or re.match("^([0-9]+)$", G.args.subtitle):
        xbmcgui.Dialog().notification(
            '%s INFO' % G.args.addon_name,
            'Language settings have changed. Please adjust settings.',
            xbmcgui.NOTIFICATION_INFO,
            10
        )

    if not (username and password):
        # open addon settings
        view.add_item({"title": G.args.addon.getLocalizedString(30062)})
        view.end_of_directory()
        G.args.addon.openSettings()
        return False
    else:
        # login
        try:
            G.api.start()

            # request to select profile if not set already
            if G.api.profile_data.profile_id is None:
                controller.show_profiles()

            # list menu
            xbmcplugin.setContent(int(G.args.argv[1]), "tvshows")

            return check_mode()
        except (LoginError, CrunchyrollError):
            # login failed
            utils.crunchy_log("Login failed", xbmc.LOGERROR)
            view.add_item({"title": G.args.addon.getLocalizedString(30060)})
            view.end_of_directory()
            xbmcgui.Dialog().ok(G.args.addon_name, G.args.addon.getLocalizedString(30060))

            return False


def check_mode():
    """Run mode-specific functions
    """
    if G.args.get_arg('mode'):
        mode = G.args.get_arg('mode')
    elif G.args.get_arg('id'):
        # call from other plugin
        mode = "videoplay"
        G.args.set_arg('url', "/media-" + G.args.get_arg('id'))
    elif G.args.get_arg('url'):
        # call from other plugin
        mode = "videoplay"
        G.args.set_arg('url', G.args.get_arg('url')[26:])  # @todo: does this actually work? truncated?
    else:
        mode = None

    if not mode:
        show_main_menu()

    elif mode == "queue":
        controller.show_queue()
    elif mode == "search":
        controller.search_anime()
    elif mode == "history":
        controller.show_history()
    elif mode == "resume":
        controller.show_resume_episodes()
    # elif mode == "random":
    #     controller.showRandom()

    elif mode == "anime":
        show_main_category("anime")
    elif mode == "drama":
        show_main_category("drama")

    # elif mode == "featured":  # https://www.crunchyroll.com/content/v2/discover/account_id/home_feed -> hero_carousel ?
    #     controller.list_series("featured", api)
    elif mode == "popular":  # DONE
        controller.list_filter()
    # elif mode == "simulcast":  # https://www.crunchyroll.com/de/simulcasts/seasons/fall-2023 ???
    #     controller.listSeries("simulcast", api)
    # elif mode == "updated":
    #    controller.listSeries("updated", api)
    elif mode == "newest":
        controller.list_filter()
    elif mode == "alpha":
        controller.list_filter()
    elif mode == "season":  # DONE
        controller.list_anime_seasons()
    elif mode == "genre":  # DONE
        controller.list_filter()

    elif mode == "seasons":
        controller.view_season()
    elif mode == "episodes":
        controller.view_episodes()
    elif mode == "videoplay":
        controller.start_playback()
    elif mode == "add_to_queue":
        controller.add_to_queue()
    # elif mode == "remove_from_queue":
    #     controller.remove_from_queue()
    elif mode == "crunchylists_lists":
        controller.crunchylists_lists()
    elif mode == 'crunchylists_item':
        controller.crunchylists_item()
    elif mode == 'profiles_list':
        controller.show_profiles()
    else:
        # unknown mode
        utils.crunchy_log("Failed in check_mode '%s'" % str(mode), xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            G.args.addon_name,
            G.args.addon.getLocalizedString(30061),
            xbmcgui.NOTIFICATION_ERROR
        )
        show_main_menu()


def show_main_menu():
    """Show main menu
    """
    view.add_item({"title": G.args.addon.getLocalizedString(30040),
                   "mode": "queue"})
    view.add_item({"title": G.args.addon.getLocalizedString(30047),
                   "mode": "resume"})
    view.add_item({"title": G.args.addon.getLocalizedString(30041),
                   "mode": "search"})
    view.add_item({"title": G.args.addon.getLocalizedString(30042),
                   "mode": "history"})
    # #view.add_item(args,
    # #              {"title": G.args.addon.getLocalizedString(30043),
    # #               "mode":  "random"})
    view.add_item({"title": G.args.addon.getLocalizedString(30050),
                   "mode": "anime"})
    view.add_item({"title": G.args.addon.getLocalizedString(30049),
                   "mode": "crunchylists_lists"})
    view.add_item({"title": G.addon.getLocalizedString(30072) % str(G.api.profile_data.username),
                   "mode": "profiles_list", "thumb": utils.get_img_from_static(G.api.profile_data.avatar)})
    # @TODO: i think there are no longer dramas. should we add music videos and movies?
    # view.add_item(args,
    #              {"title": G.args.addon.getLocalizedString(30051),
    #               "mode":  "drama"})
    view.end_of_directory(update_listing=True, cache_to_disc=False)


def show_main_category(genre):
    """Show main category
    """
    # view.add_item(args,
    #               {"title": G.args.addon.getLocalizedString(30058),
    #                "mode": "featured",
    #                "category_filter": "popular",
    #                "genre": genre})
    view.add_item({"title": G.args.addon.getLocalizedString(30052),
                   "category_filter": "popularity",
                   "mode": "popular",
                   "genre": genre})
    # view.add_item(args,
    #               {"title": "TODO | " + G.args.addon.getLocalizedString(30053),
    #                "mode": "simulcast",
    #                "genre": genre})
    # view.add_item(args,
    #               {"title": "TODO | " + G.args.addon.getLocalizedString(30054),
    #                "mode": "updated",
    #                "genre": genre})
    view.add_item({"title": G.args.addon.getLocalizedString(30059),
                   "category_filter": "newly_added",
                   "mode": "newest",
                   "genre": genre})
    view.add_item({"title": G.args.addon.getLocalizedString(30055),
                   "category_filter": "alphabetical",
                   "items_per_page": 100,
                   "mode": "alpha",
                   "genre": genre})
    view.add_item({"title": G.args.addon.getLocalizedString(30057),
                   "mode": "season",
                   "genre": genre})
    view.add_item({"title": G.args.addon.getLocalizedString(30056),
                   "mode": "genre",
                   "genre": genre})
    view.end_of_directory()
