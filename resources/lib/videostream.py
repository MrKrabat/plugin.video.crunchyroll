import datetime
import os
from typing import Union, Dict, Optional

import xbmcgui
import xbmcplugin
import xbmcvfs

from resources.lib.api import API
from resources.lib.model import Object, Args, CrunchyrollError
from resources.lib.utils import log, log_error_with_trace, convert_language_iso_to_string, crunchy_log


class VideoPlayerStreamData(Object):
    def __init__(self):
        self.stream_url: str | None = None
        self.subtitle_urls: list[str] | None = None


"""
Build a VideoPlayerStream DTO using args.steam_id

Will download stream details from cr api and store the appropriate stream url

It will then check if soft subs are enabled in settings and if so, manage downloading the required subtitles, which
are then renamed to make kodi label them in a readable way - this is because kodi uses the filename of the subtitles
to identify the language and the cr files have cryptic filenames, which will render gibberish to the user on kodi 
instead of a proper label 
"""


class VideoStream(Object):
    def __init__(self, args: Args, api: API):
        self.api: API = api
        self.args: Args = args
        self.cache_expiration_time: int = 60 * 60 * 24 * 7  # 7 days
        # cache cleanup
        self._clean_cache_subtitles()

    def get_player_stream_data(self) -> Optional[VideoPlayerStreamData]:
        if not hasattr(self.args, 'stream_id') or not self.args.stream_id:
            return None

        video_player_stream_data = VideoPlayerStreamData()

        api_stream_data = self._get_stream_data_from_api()
        if api_stream_data is False:
            raise CrunchyrollError("Failed to fetch stream data from api")

        video_player_stream_data.stream_url = self._get_stream_url_from_api_data(api_stream_data)
        video_player_stream_data.subtitle_urls = self._get_subtitles_from_api_data(api_stream_data)

        return video_player_stream_data

    """ get json stream data from cr api for given args.stream_id """

    def _get_stream_data_from_api(self) -> Union[Dict, bool]:
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

    """ retrieve appropriate stream url from api data """

    def _get_stream_url_from_api_data(self, api_data: Dict) -> Union[str, None]:
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

    """ retrieve appropriate subtitle urls from api data, using local caching and renaming """

    def _get_subtitles_from_api_data(self, api_stream_data) -> Union[str, None]:
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

    """ cache a subtitle from the given url and rename it for kodi to label it correctly """

    def _cache_subtitle(self, subtitle_url: str, subtitle_language: str, subtitle_format: str) -> bool:
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

        cache_target = xbmcvfs.translatePath(self.get_cache_path() + self.args.stream_id + '/')
        xbmcvfs.mkdirs(cache_target)

        cache_file = self.get_cache_file_name(subtitle_language, subtitle_format)

        with open(cache_target + cache_file, 'w', encoding='utf-8') as file:
            result = file.write(subtitles_req.get('data'))

        return True if result > 0 else False

    """ try to get a subtitle using it's url, language info and format. may call _cache_subtitle if it doesn't exist """

    def _get_subtitle_from_cache(self, subtitle_url: str, subtitle_language: str, subtitle_format: str) -> Union[str, None]:
        if not subtitle_url or not subtitle_language or not subtitle_format:
            log("get_subtitle_from_cache: missing argument")
            return None

        # prepare the filename for the subtitles
        cache_file = self.get_cache_file_name(subtitle_language, subtitle_format)

        # build full path to cached file
        cache_target = xbmcvfs.translatePath(self.get_cache_path() + self.args.stream_id + '/') + cache_file

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

    """ clean up all cached subtitles """

    def _clean_cache_subtitles(self) -> bool:
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

    """ return base path for subtitles caching """

    def get_cache_path(self) -> str:
        return xbmcvfs.translatePath(self.args.addon.getAddonInfo("profile") + 'cache_subtitles/')

    def get_cache_file_name(self, subtitle_language: str, subtitle_format: str) -> str:
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

        return filename
