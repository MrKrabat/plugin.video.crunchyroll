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

try:
    from urllib import unquote_plus
except ImportError:
    from urllib.parse import unquote_plus

from json import dumps

import xbmcaddon


class Args(object):
    """Arguments class
    Hold all arguments passed to the script and also persistent user data and
    reference to the addon. It is intended to hold all data necessary for the
    script.
    """

    def __init__(self, argv, kwargs):
        """Initialize arguments object
        Hold also references to the addon which can't be kept at module level.
        """
        self.PY2 = sys.version_info[0] == 2  #: True for Python 2
        self._argv = argv
        self._addonid = self._argv[0][9:-1]
        self._addon = xbmcaddon.Addon(id=self._addonid)
        self._addonname = self._addon.getAddonInfo("name")
        self._cj = None
        self._device_id = None
        self._subtitle = None
        self._subtitle_fallback = None
        # needed to pass some data around
        self._playhead = None
        self.stream_id = None

        for key, value in kwargs.items():
            if value:
                setattr(self, key, unquote_plus(value[0]))

    @property
    def addon(self):
        return self._addon

    @property
    def addonname(self):
        return self._addonname

    @property
    def addonid(self):
        return self._addonid

    @property
    def argv(self):
        return self._argv

    @property
    def device_id(self):
        return self._device_id

    @property
    def subtitle(self):
        return self._subtitle

    @property
    def subtitle_fallback(self):
        return self._subtitle_fallback


class Meta(type, metaclass=type("", (type,), {"__str__": lambda _: "~hi"})):
    def __str__(self):
        return f"<class 'crunchyroll_beta.types.{self.__name__}'>"


class Object(metaclass=Meta):
    @staticmethod
    def default(obj: "Object"):
        return {
            "_": obj.__class__.__name__,
            **{
                attr: (
                    getattr(obj, attr)
                )
                for attr in filter(lambda x: not x.startswith("_"), obj.__dict__)
                if getattr(obj, attr) is not None
            }
        }

    def __str__(self) -> str:
        return dumps(self, indent=4, default=Object.default, ensure_ascii=False)


class CMS(Object):
    def __init__(self, data: dict):
        self.bucket: str = data.get("bucket")
        self.policy: str = data.get("policy")
        self.signature: str = data.get("signature")
        self.key_pair_id: str = data.get("key_pair_id")


class AccountData(Object):
    def __init__(self, data: dict):
        self.access_token: str = data.get("access_token")
        self.refresh_token: str = data.get("refresh_token")
        self.expires: str = data.get("expires")
        self.token_type: str = data.get("token_type")
        self.scope: str = data.get("scope")
        self.country: str = data.get("country")
        self.account_id: str = data.get("account_id")
        self.cms: CMS = CMS(data.get("cms", {}))
        self.service_available: bool = data.get("service_available")
        self.avatar: str = data.get("avatar")
        self.has_beta: bool = data.get("cr_beta_opt_in")
        self.email_verified: bool = data.get("crleg_email_verified")
        self.email: str = data.get("email")
        self.maturity_rating: str = data.get("maturity_rating")
        self.account_language: str = data.get("preferred_communication_language")
        self.default_subtitles_language: str = data.get("preferred_content_subtitle_language")
        self.default_audio_language: str = data.get("preferred_content_audio_language")
        self.username: str = data.get("username")


class MovieData(Object):
    def __init__(self, data: dict):
        from . import utils

        meta = data.get("panel").get("movie_metadata")

        self.title: str = meta.get("movie_listing_title", "")
        self.tvshowtitle: str = meta.get("movie_listing_title", "")
        self.duration: int = int(meta.get("duration_ms", 0) / 1000)
        self.playhead: int = data.get("playhead", 0)
        self.episode: str = "1"
        self.episode_id: str | None = data.get("panel", {}).get("id")
        self.collection_id: str | None = None
        self.series_id: str | None = None
        self.plot: str = data.get("panel", {}).get("description", "")
        self.plotoutline: str = data.get("panel", {}).get("description", "")
        self.year: str = meta.get("premium_available_date")[:10] if meta.get(
            "premium_available_date") is not None else ""
        self.aired: str = meta.get("premium_available_date")[:10] if meta.get(
            "premium_available_date") is not None else ""
        self.premiered: str = meta.get("premium_available_date")[:10] if meta.get(
            "premium_available_date") is not None else ""
        self.thumb: str | None = utils.get_image_from_struct(data.get("panel"), "thumbnail", 2)
        self.fanart: str | None = utils.get_image_from_struct(data.get("panel"), "thumbnail", 2)
        self.playcount: int = 0
        self.stream_id: str | None = None

        try:
            # note that for fetching streams we need a special guid, not the episode_id
            self.stream_id = utils.get_stream_id_from_url(
                data.get("panel", {}).get("__links__", {}).get("streams", {}).get("href", "")
            )

            # history data has the stream_id at a different location
            if self.stream_id is None:
                self.stream_id = utils.get_stream_id_from_url(
                    data.get("panel", {}).get("streams_link")
                )

            if self.stream_id is None:
                raise Exception("")

        except Exception:
            raise CrunchyrollError("Failed to get stream id for %s" % self.title)

        if self.playhead is not None and self.duration is not None:
            self.playcount = 1 if (int(self.playhead / self.duration * 100)) > 90 else 0


# dto
class EpisodeData(Object):
    def __init__(self, data: dict):
        from . import utils

        meta = data.get("panel").get("episode_metadata")

        self.title: str = meta.get("season_title") + " #" + meta.get("episode") + " - " + data.get("panel").get("title")
        self.tvshowtitle: str = meta.get("series_title", "")
        self.duration: int = int(meta.get("duration_ms", 0) / 1000)
        self.playhead: int = data.get("playhead", 0)
        self.episode: str = meta.get("episode", "")
        self.episode_id: str | None = data.get("panel", {}).get("id")
        self.collection_id: str | None = meta.get("season_id")
        self.series_id: str | None = meta.get("series_id")
        self.plot: str = data.get("panel", {}).get("description", "")
        self.plotoutline: str = data.get("panel", {}).get("description", "")
        self.year: str = meta.get("episode_air_date")[:10] if meta.get("episode_air_date") is not None else ""
        self.aired: str = meta.get("episode_air_date")[:10] if meta.get("episode_air_date") is not None else ""
        self.premiered: str = meta.get("episode_air_date")[:10] if meta.get("episode_air_date") is not None else ""
        self.thumb: str | None = utils.get_image_from_struct(data.get("panel"), "thumbnail", 2)
        self.fanart: str | None = utils.get_image_from_struct(data.get("panel"), "thumbnail", 2)
        self.playcount: int = 0
        self.stream_id: str | None = None

        try:
            # note that for fetching streams we need a special guid, not the episode_id
            self.stream_id = utils.get_stream_id_from_url(
                data.get("panel", {}).get("__links__", {}).get("streams", {}).get("href", "")
            )

            # history data has the stream_id at a different location
            if self.stream_id is None:
                self.stream_id = utils.get_stream_id_from_url(
                    data.get("panel", {}).get("streams_link")
                )

            if self.stream_id is None:
                raise Exception("")

        except Exception:
            raise CrunchyrollError("Failed to get stream id for %s" % self.title)

        if self.playhead is not None and self.duration is not None:
            self.playcount = 1 if (int(self.playhead / self.duration * 100)) > 90 else 0


class CrunchyrollError(Exception):
    pass


class LoginError(Exception):
    pass

