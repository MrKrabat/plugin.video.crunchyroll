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
import asyncio
import datetime
import os
import sys
from typing import Union, Dict, Optional, Any

import requests
import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs

from resources.lib.api import API
from resources.lib.model import Object, Args, CrunchyrollError, PlayableItem
from resources.lib.utils import log_error_with_trace, convert_language_iso_to_string, crunchy_log, \
    get_playheads_from_api, get_cms_object_data_by_ids, get_listables_from_response


class VideoPlayerStreamData(Object):
    """ DTO to hold all relevant data for playback """

    def __init__(self):
        self.stream_url: str | None = None
        self.subtitle_urls: list[str] | None = None
        self.skip_events_data: Dict = {}
        self.playheads_data: Dict = {}
        # PlayableItem which is about to be played, that contains cms object data
        self.playable_item: PlayableItem | None = None
        # PlayableItem which contains cms obj data of playable_item's parent, if exists (Episodes, not Movies). currently not used.
        self.playable_item_parent: PlayableItem | None = None


class VideoStream(Object):
    """ Build a VideoPlayerStreamData DTO using args.stream_id

    Will download stream details from cr api and store the appropriate stream url

    It will then check if soft subs are enabled in settings and if so, manage downloading the required subtitles, which
    are then renamed to make kodi label them in a readable way - this is because kodi uses the filename of the subtitles
    to identify the language and the cr files have cryptic filenames, which will render gibberish to the user on kodi
    instead of a proper label

    Finally, it will download any existing skip info, which can be used to skip intros / credits / summaries
    """

    def __init__(self, args: Args, api: API):
        self.api: API = api
        self.args: Args = args
        self.cache_expiration_time: int = 60 * 60 * 24 * 7  # 7 days
        # cache cleanup
        self._clean_cache_subtitles()

    def get_player_stream_data(self) -> Optional[VideoPlayerStreamData]:
        """ retrieve a VideoPlayerStreamData containing stream url + subtitle urls for playback """

        if not self.args.get_arg('stream_id'):
            return None

        video_player_stream_data = VideoPlayerStreamData()

        crunchy_log(self.args, "VideoStream: Starting to retrieve data async")
        async_data = asyncio.run(self._gather_async_data())
        crunchy_log(self.args, "VideoStream: Finished to retrieve data async")

        api_stream_data = async_data.get('stream_data')
        if not api_stream_data:
            raise CrunchyrollError("Failed to fetch stream data from api")

        video_player_stream_data.stream_url = self._get_stream_url_from_api_data(async_data.get('stream_data'))
        video_player_stream_data.subtitle_urls = self._get_subtitles_from_api_data(async_data.get('stream_data'))
        video_player_stream_data.skip_events_data = async_data.get('skip_events_data')
        video_player_stream_data.playheads_data = async_data.get('playheads_data')
        video_player_stream_data.playable_item = async_data.get('playable_item')
        video_player_stream_data.playable_item_parent = async_data.get('playable_item_parent')

        return video_player_stream_data

    async def _gather_async_data(self) -> Dict[str, Any]:
        """ gather data asynchronously and return them as a dictionary """

        # create threads
        # actually not sure if this works, as the requests lib is not async
        # also not sure if this is thread safe in any way, what if session is timed-out when starting this?
        t_stream_data = asyncio.create_task(self._get_stream_data_from_api())
        t_skip_events_data = asyncio.create_task(self._get_skip_events(self.args.get_arg('episode_id')))
        t_playheads = asyncio.create_task(get_playheads_from_api(self.args, self.api, self.args.get_arg('episode_id')))  # obsolete
        t_item_data = asyncio.create_task(get_cms_object_data_by_ids(self.args, self.api, [self.args.get_arg('episode_id')]))
        #t_item_parent_data = asyncio.create_task(get_cms_object_data_by_ids(self.args, self.api, self.args.get_arg('series_id')))

        # start async requests and fetch results
        results = await asyncio.gather(t_stream_data, t_skip_events_data, t_playheads, t_item_data)

        playable_item = get_listables_from_response(self.args, [results[3].get(self.args.get_arg('episode_id'))]) if results[3] else None

        return {
            'stream_data': results[0] or {},
            'skip_events_data': results[1] or {},
            'playheads_data': results[2] or {}, # obsolete
            'playable_item': playable_item[0] if playable_item else None,
            'playable_item_parent': None # get_listables_from_response(self.args, [results[4]])[0] if results[4] else None
        }

    async def _get_stream_data_from_api(self) -> Union[Dict, bool]:
        """ get json stream data from cr api for given args.stream_id """

        # api request streams
        req = self.api.make_request(
            method="GET",
            url=self.api.STREAMS_ENDPOINT.format(self.api.account_data.cms.bucket, self.args.get_arg('stream_id')),
            params={
                "locale": self.args.subtitle
            }
        )

        # check for error
        if "error" in req or req is None:
            item = xbmcgui.ListItem(self.args.get_arg('title', 'Title not provided'))
            xbmcplugin.setResolvedUrl(int(self.args.argv[1]), False, item)
            xbmcgui.Dialog().ok(self.args.addon_name, self.args.addon.getLocalizedString(30064))
            return False

        return req

    def _get_stream_url_from_api_data(self, api_data: Dict) -> Union[str, None]:
        """ retrieve appropriate stream url from api data """

        try:
            if self.args.addon.getSetting("soft_subtitles") == "false":
                url = api_data["streams"]["adaptive_hls"]
                if self.args.subtitle in url:
                    url = url[self.args.subtitle]["url"]
                elif self.args.subtitle_fallback in url:
                    url = url[self.args.subtitle_fallback]["url"]
                else:
                    url = url[""]["url"]
            else:
                # multitrack_adaptive_hls_v2 includes soft subtitles in the stream
                if "" in api_data["streams"]["multitrack_adaptive_hls_v2"]:
                    url = api_data["streams"]["multitrack_adaptive_hls_v2"][""]["url"]
                # But sometimes, there is no default stream
                elif self.args.subtitle in api_data["streams"]["multitrack_adaptive_hls_v2"]:
                    url = api_data["streams"]["multitrack_adaptive_hls_v2"][self.args.subtitle]["url"]
                elif self.args.subtitle_fallback in api_data["streams"]["multitrack_adaptive_hls_v2"]:
                    url = api_data["streams"]["multitrack_adaptive_hls_v2"][self.args.subtitle_fallback]["url"]
                else:
                    raise CrunchyrollError("No stream URL found")

        except IndexError:
            item = xbmcgui.ListItem(self.args.get_arg('title', 'Title not provided'))
            xbmcplugin.setResolvedUrl(int(self.args.argv[1]), False, item)
            xbmcgui.Dialog().ok(self.args.addon_name, self.args.addon.getLocalizedString(30064))
            return None

        return url

    def _get_subtitles_from_api_data(self, api_stream_data) -> Union[str, None]:
        """ retrieve appropriate subtitle urls from api data, using local caching and renaming """

        # we only need those urls if soft-subs are enabled in addon settings
        if self.args.addon.getSetting("soft_subtitles") == "false":
            return None

        subtitles_data_raw = []
        subtitles_url_cached = []

        if self.args.subtitle in api_stream_data["subtitles"]:
            subtitles_data_raw.append(api_stream_data.get("subtitles").get(self.args.subtitle))

        if self.args.subtitle_fallback and self.args.subtitle_fallback in api_stream_data["subtitles"]:
            subtitles_data_raw.append(api_stream_data.get("subtitles").get(self.args.subtitle_fallback))

        if not subtitles_data_raw:
            return None

        # we need to download the subtitles, cache and rename them to show proper labels in the kodi video player
        for subtitle_data in subtitles_data_raw:
            cache_result = self._get_subtitle_from_cache(
                subtitle_data.get('url', ""),
                subtitle_data.get('locale', ""),
                subtitle_data.get('format', "")
            )

            if cache_result is not None:
                subtitles_url_cached.append(cache_result)

        return subtitles_url_cached if subtitles_url_cached is not None else None

    def _cache_subtitle(self, subtitle_url: str, subtitle_language: str, subtitle_format: str) -> bool:
        """ cache a subtitle from the given url and rename it for kodi to label it correctly """

        try:
            # api request streams
            subtitles_req = self.api.make_request(
                method="GET",
                url=subtitle_url
            )
        except Exception:
            log_error_with_trace(self.args, "error in requesting subtitle data from api")
            raise CrunchyrollError(
                "Failed to download subtitle for language %s from url %s" % (subtitle_language, subtitle_url)
            )

        if not subtitles_req.get('data', None):
            # error
            raise CrunchyrollError("Returned data is not text")

        cache_target = xbmcvfs.translatePath(self.get_cache_path() + self.args.get_arg('stream_id') + '/')
        xbmcvfs.mkdirs(cache_target)

        cache_file = self.get_cache_file_name(subtitle_language, subtitle_format)

        with open(cache_target + cache_file, 'w', encoding='utf-8') as file:
            result = file.write(subtitles_req.get('data'))

        return True if result > 0 else False

    def _get_subtitle_from_cache(
            self,
            subtitle_url: str,
            subtitle_language: str,
            subtitle_format: str
    ) -> Union[str, None]:
        """ try to get a subtitle using its url, language info and format either from cache or api """

        if not subtitle_url or not subtitle_language or not subtitle_format:
            crunchy_log(self.args, "get_subtitle_from_cache: missing argument", xbmc.LOGERROR)
            return None

        # prepare the filename for the subtitles
        cache_file = self.get_cache_file_name(subtitle_language, subtitle_format)

        # build full path to cached file
        cache_target = xbmcvfs.translatePath(self.get_cache_path() + self.args.get_arg('stream_id') + '/') + cache_file

        # check if cached file exists
        if not xbmcvfs.exists(cache_target):
            # download and cache file
            if not self._cache_subtitle(subtitle_url, subtitle_language, subtitle_format):
                # log error
                log_error_with_trace(self.args, "Failed to write subtitle to cache")
                return None

        cache_file_url = ('special://userdata/addon_data/plugin.video.crunchyroll/cache_subtitles/' +
                          self.args.get_arg('stream_id') +
                          '/' + cache_file)

        return cache_file_url

    def _clean_cache_subtitles(self) -> bool:
        """ clean up all cached subtitles """

        expires = datetime.datetime.now() - datetime.timedelta(seconds=self.cache_expiration_time)

        cache_base_dir = self.get_cache_path()
        dirs, files = xbmcvfs.listdir(cache_base_dir)

        for cache_dir in dirs:
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(cache_base_dir, cache_dir)))
            if mtime < expires:
                crunchy_log(
                    self.args,
                    "Cache dir %s is older than 7 days - removing" % os.path.join(cache_base_dir, cache_dir)
                )
                xbmcvfs.rmdir(os.path.join(cache_base_dir, cache_dir) + '/', force=True)

        return True

    def get_cache_path(self) -> str:
        """ return base path for subtitles caching """

        return xbmcvfs.translatePath(self.args.addon.getAddonInfo("profile") + 'cache_subtitles/')

    def get_cache_file_name(self, subtitle_language: str, subtitle_format: str) -> str:
        """ build a file name for the subtitles file that kodi can display with a readable label """

        # kodi ignores the first part of e.g. de-DE - split and use only first part in uppercase
        iso_parts = subtitle_language.split('-')

        filename = xbmcvfs.makeLegalFilename(
            convert_language_iso_to_string(self.args, subtitle_language) +
            '.' + iso_parts[0] +
            '.' + subtitle_format
        )

        # for some reason, makeLegalFilename likes to append a '/' at the end, effectively making the file a directory
        if filename.endswith('/'):
            filename = filename[:-1]

        # have to use filesystemencoding since filename contains non ascii characters in some language (such as french)
        # and kodi file system encoding can be set to ASCII
        return filename.encode(sys.getfilesystemencoding(), "ignore").decode(sys.getfilesystemencoding())

    async def _get_skip_events(self, episode_id) -> Optional[Dict]:
        """ fetch skip events data from api and return a prepared object for supported skip types if data is valid """

        # if none of the skip options are enabled in setting, don't fetch that data
        if (self.args.addon.getSetting("enable_skip_intro") != "true" and
                self.args.addon.getSetting("enable_skip_credits") != "true"):
            return None

        try:
            crunchy_log(self.args, "Requesting skip data from %s" % self.api.SKIP_EVENTS_ENDPOINT.format(episode_id))

            # api request streams
            req = self.api.make_unauthenticated_request(
                method="GET",
                url=self.api.SKIP_EVENTS_ENDPOINT.format(episode_id)
            )
        except (requests.exceptions.RequestException, CrunchyrollError):
            try:
                # Some streams raise a 403 on SKIP_EVENTS endpoint but skip data are available in INTRO_V2 endpoint
                intro_req = self.api.make_unauthenticated_request(
                    method="GET",
                    url=self.api.INTRO_V2_ENDPOINT.format(episode_id)
                )
                req = {"intro": {
                    "start": intro_req.get("startTime"),
                    "end": intro_req.get("endTime"),
                }}
            except (requests.exceptions.RequestException, CrunchyrollError):
                # can be okay for e.g. movies, thus only log error with trace, but don't show notification
                log_error_with_trace(
                    self.args,
                    "_get_skip_events: error in requesting skip events data from api",
                    False
                )
                return None

        if not req or "error" in req:
            crunchy_log(self.args, "_get_skip_events: error in requesting skip events data from api (2)")
            return None

        # prepare the data a bit
        supported_skips = ['intro', 'credits']
        prepared = dict()
        for skip_type in supported_skips:
            if req.get(skip_type) and req.get(skip_type).get('start') is not None and req.get(skip_type).get(
                    'end') is not None:
                prepared.update({
                    skip_type: dict(start=req.get(skip_type).get('start'), end=req.get(skip_type).get('end'))
                })
                crunchy_log(self.args, "_get_skip_events: check for %s PASSED" % skip_type, xbmc.LOGINFO)
            else:
                crunchy_log(self.args, "_get_skip_events: check for %s FAILED" % skip_type, xbmc.LOGINFO)

        return prepared if len(prepared) > 0 else None
