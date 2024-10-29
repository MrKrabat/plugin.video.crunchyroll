# -*- coding: utf-8 -*-
# Crunchyroll
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
import json
import re
from datetime import datetime
from json import dumps
from typing import Dict, Union, List, Optional

import requests
import xbmc
import xbmcgui

from .globals import G
from .model import CrunchyrollError, ListableItem, EpisodeData, MovieData, SeriesData, SeasonData


# @todo we could change the return type and along with the listables return additional data that we preload
#       like info what is on watchlist, artwork, playhead, ...
#       for that we should use async requests (asyncio)
def get_listables_from_response(data: List[dict]) -> List[ListableItem]:
    """ takes an API response object, determines type of its contents and creates DTOs for further processing """

    listable_items = []

    for item in data:
        # fetch type, which is always somewhere else, depending on api endpoint *sighs*
        item_type = item.get('panel', {}).get('type') or item.get('type') or item.get('__class__')
        if not item_type:
            crunchy_log(
                "get_listables_from_response | failed to determine type for response item %s" % (
                    json.dumps(item, indent=4)),
                xbmc.LOGERROR
            )
            continue

        if item_type == 'series':
            if not filter_series(item):
                continue
            listable_items.append(SeriesData(item))
        elif item_type == 'season':
            # filter series items based on language settings
            if not filter_seasons(item):
                continue
            listable_items.append(SeasonData(item))
        elif item_type == 'episode':
            listable_items.append(EpisodeData(item))
        elif item_type == 'movie':
            listable_items.append(MovieData(item))
        else:
            crunchy_log(
                "get_listables_from_response | unhandled index for metadata. %s" % (json.dumps(item, indent=4)),
                xbmc.LOGERROR
            )
            continue

    return listable_items


async def get_cms_object_data_by_ids(ids: list) -> dict:
    """ fetch info from api object endpoint for given ids. Useful to complement missing data """

    # filter out entries with no value
    ids_filtered = [item for item in ids if item != 0 and item is not None]
    if len(ids_filtered) == 0:
        return {}

    try:
        req = G.api.make_request(
            method='GET',
            url=G.api.OBJECTS_BY_ID_LIST_ENDPOINT.format(','.join(ids_filtered)),
            params={
                'locale': G.args.subtitle,
                'ratings': 'true'
                # "preferred_audio_language": ""
            }
        )
    except (CrunchyrollError, requests.exceptions.RequestException):
        crunchy_log("get_cms_object_data_by_ids: failed to load for: %s" % ",".join(ids_filtered))
        return {}

    if not req or 'error' in req:
        return {}

    return {item.get('id'): item for item in req.get('data')}


def get_stream_id_from_item(item: Dict) -> Union[str, None]:
    """ takes a URL string and extracts the stream ID from it """

    pattern = '/videos/([^/]+)/streams'
    stream_id = re.search(pattern, item.get('__links__', {}).get('streams', {}).get('href', ''))
    # history data has the stream_id at a different location
    if not stream_id:
        stream_id = re.search(pattern, item.get('streams_link', ''))

    if not stream_id:
        raise CrunchyrollError('Failed to get stream id')

    return stream_id[1]


async def get_playheads_from_api(episode_ids: Union[str, list]) -> Dict:
    """ Retrieve playhead data from API for given episode / movie ids """

    if isinstance(episode_ids, str):
        episode_ids = [episode_ids]

    response = G.api.make_request(
        method='GET',
        url=G.api.PLAYHEADS_ENDPOINT.format(G.api.account_data.account_id),
        params={
            'locale': G.args.subtitle,
            'content_ids': ','.join(episode_ids)
        }
    )

    out = {}

    if not response:
        return out

    # prepare by id
    for item in response.get('data'):
        out[item.get('content_id')] = {
            'playhead': item.get('playhead'),
            'fully_watched': item.get('fully_watched')
        }

    return out


async def get_watchlist_status_from_api(ids: list) -> list:
    """ retrieve watchlist status for given media ids """

    req = G.api.make_request(
        method="GET",
        url=G.api.WATCHLIST_V2_ENDPOINT.format(G.api.account_data.account_id),
        params={
            "content_ids": ','.join(ids),
            "locale": G.args.subtitle
        }
    )

    if not req or req.get("error") is not None:
        crunchy_log("get_in_queue: Failed to retrieve data", xbmc.LOGERROR)
        return []

    if not req.get('data'):
        return []

    return [item.get('id') for item in req.get('data')]


def get_img_from_static(image, image_type='normal') -> Optional[str]:
    if image is None:
        return None

    path = G.api.STATIC_IMG_PROFILE

    if image_type == "wallpaper":
        path = G.api.STATIC_WALLPAPER_PROFILE

    return path + image


def get_img_from_struct(item: Dict, image_type: str, depth: int = 2) -> Union[str, None]:
    """ dive into API info structure and extract requested image from its struct """

    # @todo: add option to specify quality / max size
    if item.get("images") and item.get("images").get(image_type):
        src = item.get("images").get(image_type)
        for i in range(0, depth):
            if src[-1]:
                src = src[-1]
            else:
                return None
        if src.get('source'):
            return src.get('source')

    return None


def dump(data) -> None:
    xbmc.log(dumps(data, indent=4), xbmc.LOGINFO)


def log(message) -> None:
    xbmc.log(message, xbmc.LOGINFO)


def crunchy_log(message, loglevel=xbmc.LOGINFO) -> None:
    addon_name = G.args.addon_name if G.args is not None and hasattr(G.args, 'addon_name') else "Crunchyroll"
    xbmc.log("[PLUGIN] %s: %s" % (addon_name, str(message)), loglevel)


def log_error_with_trace(message, show_notification: bool = True) -> None:
    import sys
    import traceback

    # Get current system exception
    ex_type, ex_value, ex_traceback = sys.exc_info()

    # Extract unformatter stack traces as tuples
    trace_back = traceback.extract_tb(ex_traceback)

    # Format stacktrace
    stack_trace = list()

    for trace in trace_back:
        stack_trace.append(
            "File : %s , Line : %d, Func.Name : %s, Message : %s" % (trace[0], trace[1], trace[2], trace[3]))

    addon_name = G.args.addon_name if G.args is not None and hasattr(G.args, 'addon_name') else "Crunchyroll"

    xbmc.log("[PLUGIN] %s: %s" % (addon_name, str(message)), xbmc.LOGERROR)
    xbmc.log("[PLUGIN] %s: %s %s\n%s" % (addon_name, ex_type.__name__, ex_value, "\n".join(stack_trace)), xbmc.LOGERROR)

    if show_notification:
        xbmcgui.Dialog().notification(
            '%s Error' % addon_name,
            'Please check logs for details',
            xbmcgui.NOTIFICATION_ERROR,
            5
        )

def filter_series(seriesItem: Dict) -> bool:
    """ takes an API info struct and returns if it matches user language settings """

    if G.args.addon.getSetting("filter_dubs_by_language") != "true":
        return True

    panel = seriesItem.get('panel') or seriesItem
    item = panel.get("series_metadata") or panel

    # is it a dub in my main language?
    if G.args.addon.getSetting("show_dubs_by_language") == "true":
        if G.args.subtitle in item.get('audio_locales', []):
            return True

    # is it a dub in my alternate language?
    if G.args.addon.getSetting("show_dubs_by_language_fallback") == "true" and G.args.subtitle_fallback and G.args.subtitle_fallback in item.get('audio_locales', []):
        return True

    if G.args.addon.getSetting("show_subs_by_language") == "true":
        # is it japanese audio, but there are subtitles in my main language?
        #
        # edge case for chinese only anime where there is no japanese dub
        # @see: https://github.com/smirgol/plugin.video.crunchyroll/issues/51
        if "ja-JP" in item.get("audio_locales", []) or "zh-CN" in item.get("audio_locales", []):
            # fix for missing subtitles in data
            if item.get("subtitle_locales", []) == [] and item.get('is_subbed', False) is True:
                return True

            if G.args.subtitle in item.get("subtitle_locales", []):
                return True

            if G.args.subtitle_fallback and G.args.subtitle_fallback in item.get("subtitle_locales", []):
                return True

    return False

def filter_seasons(item: Dict) -> bool:
    """ takes an API info struct and returns if it matches user language settings """

    if G.args.addon.getSetting("filter_dubs_by_language") != "true":
        return True

    # is it a dub in my main language?
    if G.args.addon.getSetting("show_dubs_by_language") == "true":
        if G.args.subtitle == item.get('audio_locale', ""):
            return True

    # is it a dub in my alternate language?
    if G.args.addon.getSetting("show_dubs_by_language_fallback") == "true" and G.args.subtitle_fallback and G.args.subtitle_fallback == item.get('audio_locale', ""):
        return True

    if G.args.addon.getSetting("show_subs_by_language") == "true":
        # is it japanese audio, but there are subtitles in my main language?
        #
        # edge case for chinese only anime where there is no japanese dub
        # @see: https://github.com/smirgol/plugin.video.crunchyroll/issues/51
        if item.get("audio_locale") == "ja-JP" or item.get("audio_locale") == "zh-CN":
            # fix for missing subtitles in data
            if item.get("subtitle_locales", []) == [] and item.get('is_subbed', False) is True:
                return True

            if G.args.subtitle in item.get("subtitle_locales", []):
                return True

            if G.args.subtitle_fallback and G.args.subtitle_fallback in item.get("subtitle_locales", []):
                return True

    return False


def format_long_episode_title(season_title: str, episode_number: int, title: str):
    return season_title + " #" + str(episode_number) + " - " + title


def format_short_episode_title(episode_number: int, title: str):
    return two_digits(episode_number) + " - " + title


def two_digits(n: int) -> str:
    if not n:
        return "00"
    if n < 10:
        return "0" + str(n)
    return str(n)


def highlight_list_item_title(list_item: xbmcgui.ListItem):
    """ Highlight title

        Used to highlight that item is already on watchlist
    """
    list_item.setInfo('video', {'title': '[COLOR orange]' + list_item.getLabel() + '[/COLOR]'})


def convert_text_to_date(date_str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d")


def sort_episodes(listables: List[ListableItem]) -> List[ListableItem]:
    """ Sort episodes list to move all unwatched episodes to top """

    watched = []
    unwatched = []

    # split in watched and unwatched
    for listable in listables:
        if not isinstance(listable, EpisodeData) and not isinstance(listable, MovieData):
            crunchy_log('Error sorting episodes. Not an episode nor movie')
            continue

        if listable.playcount == 1:
            watched.append(listable)
        else:
            unwatched.append(listable)

    # sort both lists by aired:
    watched.sort(key=lambda obj: convert_text_to_date(obj.aired), reverse=True)
    unwatched.sort(key=lambda obj: convert_text_to_date(obj.aired), reverse=True)

    return unwatched + watched
