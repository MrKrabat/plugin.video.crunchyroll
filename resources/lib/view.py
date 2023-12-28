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

try:
    from urllib import quote_plus
except ImportError:
    from urllib.parse import quote_plus

import xbmcvfs
import xbmcgui
import xbmcplugin

from typing import Callable

# keys allowed in setInfo
types = ["count", "size", "date", "genre", "country", "year", "episode", "season", "sortepisode", "top250", "setid",
         "tracknumber", "rating", "userrating", "watched", "playcount", "overlay", "cast", "castandrole", "director",
         "mpaa", "plot", "plotoutline", "title", "originaltitle", "sorttitle", "duration", "studio", "tagline",
         "writer",
         "tvshowtitle", "premiered", "status", "set", "setoverview", "tag", "imdbnumber", "code", "aired", "credits",
         "lastplayed", "album", "artist", "votes", "path", "trailer", "dateadded", "mediatype", "dbid"]


def end_of_directory(args, content_type = None):
    # let xbmc know the items type in current directory
    if content_type is not None:
        xbmcplugin.setContent(int(args._argv[1]), content_type)

    # sort methods are required in library mode
    xbmcplugin.addSortMethod(int(args.argv[1]), xbmcplugin.SORT_METHOD_NONE)

    # let xbmc know the script is done adding items to the list
    xbmcplugin.endOfDirectory(handle=int(args.argv[1]))


def add_item(
        args,
        info,
        is_folder=True,
        total_items=0,
        mediatype="video",
        callback: Callable[[xbmcgui.ListItem], None] = None
):
    """Add item to directory listing.
    """

    # create list item
    li = xbmcgui.ListItem(label=info["title"])

    # get infoLabels
    info_labels = make_info_label(args, info)

    # get url
    u = build_url(args, info)

    if is_folder:
        # directory
        info_labels["mediatype"] = "tvshow"
        li.setInfo(mediatype, info_labels)
    else:
        # playable video
        info_labels["mediatype"] = "episode"
        li.setInfo(mediatype, info_labels)
        li.setProperty("IsPlayable", "true")

        # add context menu
        cm = []
        if u"series_id" in u:
            cm.append((args.addon.getLocalizedString(30045),
                       "Container.Update(%s)" % re.sub(r"(?<=mode=)[^&]*", "series", u)))
        if u"collection_id" in u:
            cm.append((args.addon.getLocalizedString(30046),
                       "Container.Update(%s)" % re.sub(r"(?<=mode=)[^&]*", "episodes", u)))
        if len(cm) > 0:
            li.addContextMenuItems(cm)

    # set media image
    li.setArt({"thumb": info.get("thumb", "DefaultFolder.png"),
               "poster": info.get("thumb", "DefaultFolder.png"),
               "banner": info.get("thumb", "DefaultFolder.png"),
               "fanart": info.get("fanart", xbmcvfs.translatePath(args.addon.getAddonInfo("fanart"))),
               "icon": info.get("thumb", "DefaultFolder.png")})

    if callback:
        callback(li)

    # add item to list
    xbmcplugin.addDirectoryItem(handle=int(args.argv[1]),
                                url=u,
                                listitem=li,
                                isFolder=is_folder,
                                totalItems=total_items)


def quote_value(value):
    """Quote value depending on python
    """
    if not isinstance(value, str):
        value = str(value)
    return quote_plus(value)


def build_url(args, info):
    """Create url
    """
    s = ""
    # step 1 copy new information from info
    for key, value in list(info.items()):
        if value:
            s = s + "&" + key + "=" + quote_value(value)

    # step 2 copy old information from args, but don't append twice
    for key, value in list(args.__dict__.items()):
        if value and key in types and not "&" + str(key) + "=" in s:
            s = s + "&" + key + "=" + quote_value(value)

    return args.argv[0] + "?" + s[1:]


def make_info_label(args, info):
    """Generate info_labels from existing dict
    """
    info_labels = {}
    # step 1 copy new information from info
    for key, value in list(info.items()):
        if value and key in types:
            info_labels[key] = value

    # step 2 copy old information from args, but don't overwrite
    for key, value in list(args.__dict__.items()):
        if value and key in types and key not in info_labels:
            info_labels[key] = value

    return info_labels
