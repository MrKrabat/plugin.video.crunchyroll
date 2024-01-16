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
import asyncio
import re

from resources.lib.api import API
from resources.lib.model import ListableItem, EpisodeData, Args, SeasonData, SeriesData, PlayableItem

try:
    from urllib import quote_plus
except ImportError:
    from urllib.parse import quote_plus

import xbmcvfs
import xbmcgui
import xbmcplugin

from typing import Callable, Optional, List, Dict, Any
from . import router

# keys allowed in setInfo
types = ["count", "size", "date", "genre", "country", "year", "episode", "season", "sortepisode", "top250", "setid",
         "tracknumber", "rating", "userrating", "watched", "playcount", "overlay", "cast", "castandrole", "director",
         "mpaa", "plot", "plotoutline", "title", "originaltitle", "sorttitle", "duration", "studio", "tagline",
         "writer",
         "tvshowtitle", "premiered", "status", "set", "setoverview", "tag", "imdbnumber", "code", "aired", "credits",
         "lastplayed", "album", "artist", "votes", "path", "trailer", "dateadded", "mediatype", "dbid"]


def end_of_directory(args, content_type=None):
    # let xbmc know the items type in current directory
    if content_type is not None:
        xbmcplugin.setContent(int(args.argv[1]), content_type)

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
        callbacks: Optional[List[Callable[[xbmcgui.ListItem], None]]] = None
):
    """ Add item to directory listing.

        This is the old, more verbose approach. Try to use view.add_listables() for adding list items, if possible
    """

    path_params = {}
    path_params.update(args.args)
    path_params.update(info)

    # get url
    u = build_url(args, path_params)

    # create list item
    li = xbmcgui.ListItem(label=info["title"], path=u)

    # get infoLabels
    info_labels = make_info_label(args, info)

    if is_folder:
        # directory
        info_labels["mediatype"] = "tvshow"
        li.setInfo(mediatype, info_labels)
    else:
        # playable video
        info_labels["mediatype"] = "episode"
        li.setInfo(mediatype, info_labels)
        li.setProperty("IsPlayable", "true")

        # add context menu to jump to seasons xor episodes
        # @todo: this only makes sense in some very specific places, we need a way to handle these better.
        cm = []
        if path_params.get("series_id"):
            cm.append((args.addon.getLocalizedString(30045),
                       "Container.Update(%s)" % build_url(args, path_params, "series_view")))
        if path_params.get("collection_id"):
            cm.append((args.addon.getLocalizedString(30046),
                       "Container.Update(%s)" % build_url(args, path_params, "season_view")))

        if len(cm) > 0:
            li.addContextMenuItems(cm)

    # set media image
    li.setArt({"thumb": info.get("thumb", "DefaultFolder.png"),
               "poster": info.get("poster", info.get("thumb", "DefaultFolder.png")),
               "banner": info.get("thumb", "DefaultFolder.png"),
               "fanart": info.get("fanart", xbmcvfs.translatePath(args.addon.getAddonInfo("fanart"))),
               "icon": info.get("thumb", "DefaultFolder.png")})

    if callbacks:
        for cb in callbacks:
            cb(li)

    # add item to list
    xbmcplugin.addDirectoryItem(handle=int(args.argv[1]),
                                url=u,
                                listitem=li,
                                isFolder=is_folder,
                                totalItems=total_items)


OPT_MARK_ON_WATCHLIST = 1  # highlight title if item is on watchlist
OPT_CTX_WATCHLIST = 2  # add context menu to add item to watchlist
OPT_CTX_SEASONS = 4  # add context menu to jump to series
OPT_CTX_EPISODES = 8  # add context menu to jump to episodes


# actually not sure if this works, as the requests lib is not async
# also not sure if this is thread safe in any way, what if session is timed-out when starting this?
async def complement_listables(
        args: Args,
        api: API,
        listables: List[ListableItem]
) -> Dict[str, Dict[str, Any]]:
    # for all playable items fetch playhead data from api, as sometimes we already have them, sometimes not
    from .utils import get_playheads_from_api, get_cms_object_data_by_ids, get_watchlist_status_from_api, \
        get_img_from_struct

    # playheads
    ids_playhead = [listable.id for listable in listables if
                    isinstance(listable, PlayableItem) and listable.playhead == 0]

    # object data for e.g. poster images
    # for now we use the objects to fetch the series data only, to fetch its images and its rating
    ids_objects_seasons = [listable.series_id for listable in listables if
                           isinstance(listable, (SeasonData, EpisodeData, SeriesData))]
    # ids_objects_other = [listable.id for listable in listables if
    #                      isinstance(listable, (EpisodeData, MovieData, SeriesData))]
    # ids_objects = ids_objects_seasons + ids_objects_other
    ids_objects = list(set(ids_objects_seasons))  # make the ids unique, as there can be duplicates

    # watchlist info for series
    ids_watchlist = [listable.id for listable in listables if isinstance(listable, SeriesData)]

    # prepare async requests
    tasks_added = []
    tasks = []
    if ids_playhead:
        tasks.append(asyncio.create_task(get_playheads_from_api(args, api, ids_playhead)))
        tasks_added.append('playheads')
    # @todo: for some reason objects endpoint stopped to deliver anything but thumbs in terms of images,
    #        but the sole reason for calling it are the additional images...
    #        for now we use the objects to fetch the series data only, to fetch its images and its rating
    if ids_objects:
        tasks.append(asyncio.create_task(get_cms_object_data_by_ids(args, api, ids_objects)))
        tasks_added.append('objects')
    if ids_watchlist:
        tasks.append(asyncio.create_task(get_watchlist_status_from_api(args, api, ids_watchlist)))
        tasks_added.append('watchlist')

    # start async requests and fetch results
    results = await asyncio.gather(*tasks)

    result_obj = {
        'playheads': {},
        'objects': {},
        'watchlist': {}
    }
    for idx, task in enumerate(tasks_added):
        result_obj[task] = results[idx]

    # crunchy_log(args, "Retrieved data for playheads:")
    # dump(result_obj.get('playheads'))

    # crunchy_log(args, "Retrieved data for objects:")
    # dump(result_obj.get('objects'))
    # crunchy_log(args, "Retrieved data for watchlist:")
    # dump(result_obj.get('watchlist'))

    # add some of the info to the listables
    for listable in listables:
        # update playcount data, which might be missing
        if listable.id in result_obj.get('playheads'):
            listable.update_playcount_from_playhead(result_obj.get('playheads').get(listable.id))

        # update images for SeasonData, as they come with none by default
        if isinstance(listable, (SeriesData, SeasonData)) and listable.series_id in result_obj.get('objects'):
            setattr(listable, 'thumb',
                    get_img_from_struct(result_obj.get('objects').get(listable.series_id), "poster_tall",
                                        2) or listable.thumb)
            setattr(listable, 'fanart',
                    get_img_from_struct(result_obj.get('objects').get(listable.series_id), "poster_wide",
                                        2) or listable.fanart)
            setattr(listable, 'poster',
                    get_img_from_struct(result_obj.get('objects').get(listable.series_id), "poster_tall",
                                        2) or listable.poster)

        elif isinstance(listable, EpisodeData) and listable.series_id in result_obj.get('objects'):
            # for others, only set the thumb image to a nicer one
            setattr(listable, 'thumb',
                    get_img_from_struct(result_obj.get('objects').get(listable.series_id), "poster_tall",
                                        2) or listable.thumb)
            setattr(listable, 'poster',
                    get_img_from_struct(result_obj.get('objects').get(listable.series_id), "poster_tall",
                                        2) or listable.poster)
            # setattr(listable, 'fanart',
            #         get_image_from_struct(result_obj.get('objects').get(listable.id), "poster_wide", 2) or listable.fanart)

        if listable.id in result_obj.get('objects') and result_obj.get('objects').get(listable.id).get(
                'rating') and hasattr(listable, 'rating'):
            if result_obj.get('objects').get(listable.id).get('rating').get('average'):
                listable.rating = float(result_obj.get('objects').get(listable.id).get('rating').get('average')) * 2.0
            elif result_obj.get('objects').get(listable.id).get('rating').get('up') and result_obj.get('objects').get(
                    listable.id).get('rating').get('down'):
                # these are user ratings and they are pretty weird (overly positive)
                ups_obj = result_obj.get('objects').get(listable.id).get('rating').get('up')
                downs_obj = result_obj.get('objects').get(listable.id).get('rating').get('down')
                ups = float(ups_obj.get('displayed'))
                downs = float(downs_obj.get('displayed'))

                if ups_obj.get('unit') == 'K':
                    ups *= 1000.0
                elif ups_obj.get('unit') == 'M':
                    ups *= 1000000.0  # not sure if that works or if there are ever that many votes

                if downs_obj.get('unit') == 'K':
                    downs *= 1000.0
                elif downs_obj.get('unit') == 'M':
                    downs *= 1000000.0  # not sure if that works or if there are ever that many votes

                listable.rating = float((ups / (ups + downs)) * 10.0)

    # return collected data for further usage
    return result_obj


def add_listables(
        args: Args,
        api: API,
        listables: List[ListableItem],
        is_folder=True,
        options: int = 0,
        callbacks: Optional[List[Callable[[xbmcgui.ListItem, ListableItem], None]]] = None
):
    from .utils import highlight_list_item_title, crunchy_log

    crunchy_log(args, "add_listables: Starting to retrieve data async")
    complement_data = asyncio.run(complement_listables(args, api, listables))
    crunchy_log(args, "add_listables: Finished to retrieve data async")

    # add listable items to kodi
    for listable in listables:
        # get url
        u = build_url(args, listable.get_info(args))

        # get xbmc list item
        list_item = listable.to_item(args)

        # call any callbacks
        if callbacks:
            for cb in callbacks:
                cb(list_item, listable)

        # process options

        if options & OPT_MARK_ON_WATCHLIST:
            highlight_list_item_title(list_item) if listable.id in complement_data.get('watchlist') else None

        cm = []
        if options & OPT_CTX_WATCHLIST and listable.id not in complement_data.get('watchlist'):
            cm.append((
                args.addon.getLocalizedString(30067),
                'RunPlugin(%s?mode=add_to_queue&content_id=%s&session_restart=True)' % (args.argv[0], listable.id)
            ))

        if options & OPT_CTX_SEASONS and hasattr(listable, 'series_id') and getattr(listable, 'series_id') is not None:
            cm.append((
                args.addon.getLocalizedString(30045),
                "Container.Update(%s)" % re.sub(r"(?<=mode=)[^&]*", "seasons", u)
            ))

        if options & OPT_CTX_EPISODES and hasattr(listable, 'season_id') and getattr(listable, 'season_id') is not None:
            cm.append((
                args.addon.getLocalizedString(30046),
                "Container.Update(%s)" % re.sub(r"(?<=mode=)[^&]*", "episodes", u)
            ))

        if len(cm) > 0:
            list_item.addContextMenuItems(cm)

        # add item to list
        xbmcplugin.addDirectoryItem(
            handle=int(args.argv[1]),
            url=u,
            listitem=list_item,
            isFolder=is_folder
        )


def quote_value(value) -> str:
    """Quote value depending on python
    """
    if not isinstance(value, str):
        value = str(value)
    return quote_plus(value)


# Those parameters will be bypassed to URL as additional query_parameters if found in build_url path_params
# @todo: in theory it is no longer needed, test that
whitelist_url_args = ["duration", "playhead"]


def build_url(args, path_params: dict, route_name: str = None) -> str:
    """Create url
    """

    # Get base route
    if route_name is None:
        path = router.build_path(path_params)
    else:
        path = router.create_path_from_route(route_name, path_params)
    if path is None:
        path = "/"

    s = ""
    # Add whitelisted parameters
    for key, value in path_params.items():
        if key in whitelist_url_args and value:
            s = s + "&" + key + "=" + quote_value(value)
    if len(s) > 0:
        s = "?" + s[1:]

    result = args.addonurl + path + s

    return result


def make_info_label(args, info) -> dict:
    """Generate info_labels from existing dict
    """
    info_labels = {}
    # step 1 copy new information from info
    for key, value in list(info.items()):
        if value and key in types:
            info_labels[key] = value

    # step 2 copy old information from args, but don't overwrite
    for key, value in list(args.args.items()):
        if value and key in types and key not in info_labels:
            info_labels[key] = value

    return info_labels
