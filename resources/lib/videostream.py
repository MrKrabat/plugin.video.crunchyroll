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

import os

import datetime
import xbmcgui
import xbmcplugin
import xbmcvfs
import xbmc
import codecs

from resources.lib.model import Object, CrunchyrollError
from resources.lib.utils import log_error_with_trace, convert_language_iso_to_string, crunchy_log


class VideoPlayerStreamData(Object):
    """ DTO to hold all relevant data for playback """

    def __init__(self):
        Object.__init__(self)
        self.stream_url = None
        self.subtitle_urls = None


class VideoStream(Object):
    """
    Build a VideoPlayerStream DTO using args.steam_id

    Will download stream details from cr api and store the appropriate stream url

    It will then check if soft subs are enabled in settings and if so, manage downloading the required subtitles, which
    are then renamed to make kodi label them in a readable way - this is because kodi uses the filename of the subtitles
    to identify the language and the cr files have cryptic filenames, which will render gibberish to the user on kodi
    instead of a proper label
    """

    def __init__(self, args, api):
        Object.__init__(self)
        self.api = api
        self.args = args
        self.cache_expiration_time = 60 * 60 * 24 * 7  # 7 days
        # cache cleanup
        self._clean_cache_subtitles()

    def get_player_stream_data(self):
        """ retrieve a VideoPlayerStreamData containing stream url + subtitle urls for playback """

        if not hasattr(self.args, 'stream_id') or not self.args.stream_id:
            return None

        video_player_stream_data = VideoPlayerStreamData()

        api_stream_data = self._get_stream_data_from_api()
        if api_stream_data is False:
            raise CrunchyrollError("Failed to fetch stream data from api")

        video_player_stream_data.stream_url = self._get_stream_url_from_api_data(api_stream_data)
        video_player_stream_data.subtitle_urls = self._get_subtitles_from_api_data(api_stream_data)

        return video_player_stream_data

    def _get_stream_data_from_api(self):
        """ get json stream data from cr api for given args.stream_id """

        # api request streams
        req = self.api.make_request(
            method="GET",
            url=self.api.STREAMS_ENDPOINT.format(self.api.account_data.cms.bucket, self.args.stream_id),
            params={
                "locale": self.args.subtitle
            }
        )

        # check for error
        if "error" in req or req is None:
            item = xbmcgui.ListItem(getattr(self.args, "title", "Title not provided"))
            xbmcplugin.setResolvedUrl(int(self.args.argv[1]), False, item)
            xbmcgui.Dialog().ok(self.args.addonname, self.args.addon.getLocalizedString(30064))
            return False

        return req

    def _get_stream_url_from_api_data(self, api_data):
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
                url = api_data["streams"]["multitrack_adaptive_hls_v2"][""]["url"]

        except IndexError:
            item = xbmcgui.ListItem(getattr(self.args, "title", "Title not provided"))
            xbmcplugin.setResolvedUrl(int(self.args.argv[1]), False, item)
            xbmcgui.Dialog().ok(self.args.addonname, self.args.addon.getLocalizedString(30064))
            return None

        return url

    def _get_subtitles_from_api_data(self, api_stream_data):
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

    def _cache_subtitle(self, subtitle_url, subtitle_language, subtitle_format):
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

        cache_target = xbmc.translatePath(self.get_cache_path() + self.args.stream_id + '/')
        xbmcvfs.mkdirs(cache_target)

        cache_file = self.get_cache_file_name(subtitle_language, subtitle_format)

        try:
            with codecs.open(cache_target + cache_file, 'wb', encoding='utf-8') as f:
                try:
                    f.write(subtitles_req.get('data'))
                    return True
                except UnicodeEncodeError:
                    log_error_with_trace(self.args, "UnicodeEncodeError: Failed to write data to cache file")
                    return False
        except Exception as e:
            log_error_with_trace(self.args, "Failed to open cache file: {}".format(e))
            return False

    """ try to get a subtitle using it's url, language info and format. may call _cache_subtitle if it doesn't exist """

    def _get_subtitle_from_cache(self, subtitle_url, subtitle_language, subtitle_format):
        """ try to get a subtitle using its url, language info and format either from cache or api """

        if not subtitle_url or not subtitle_language or not subtitle_format:
            crunchy_log(self.args, "get_subtitle_from_cache: missing argument", xbmc.LOGERROR)
            return None

        # prepare the filename for the subtitles
        cache_file = self.get_cache_file_name(subtitle_language, subtitle_format)

        # build full path to cached file
        cache_target = xbmc.translatePath(self.get_cache_path() + self.args.stream_id + '/') + cache_file

        # check if cached file exists
        if not xbmcvfs.exists(cache_target):
            # download and cache file
            if not self._cache_subtitle(subtitle_url, subtitle_language, subtitle_format):
                # log error
                log_error_with_trace(self.args, "Failed to write subtitle to cache")
                return None

        cache_file_url = ('special://userdata/addon_data/plugin.video.crunchyroll/cache_subtitles/' +
                          self.args.stream_id +
                          '/' + cache_file)

        return cache_file_url

    def _clean_cache_subtitles(self):
        """ clean up all cached subtitles """

        expires = datetime.datetime.now() - datetime.timedelta(seconds=self.cache_expiration_time)
        cache_base_dir = self.get_cache_path()

        if not xbmcvfs.exists(cache_base_dir):
            return

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

    def get_cache_path(self):
        """ return base path for subtitles caching """

        return xbmc.translatePath(self.args.addon.getAddonInfo("profile") + 'cache_subtitles/')

    def get_cache_file_name(self, subtitle_language, subtitle_format):
        """ build a file name for the subtitles file that kodi can display with a readable label """

        # kodi ignores the first part of e.g. de-DE - split and use only first part in uppercase
        iso_parts = subtitle_language.split('-')

        filename = xbmc.makeLegalFilename(
            convert_language_iso_to_string(self.args, subtitle_language) +
            '.' + iso_parts[0] +
            '.' + subtitle_format
        )

        # for some reason, makeLegalFilename likes to append a '/' at the end, effectively making the file a directory
        if filename.endswith('/'):
            filename = filename[:-1]

        return filename
