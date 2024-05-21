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
# along with this program.  If not, see <http://www.gnu.org/licenses/>

# pylint: disable=E0401,W0611
from urllib.parse import urlencode
from codequick import Route, Resolver, Listitem, run # noqa = F401
import xbmcaddon
from . import utils

ADDON = xbmcaddon.Addon(id=utils.ADDON_ID)


# pylint: disable=W0613
@Route.register
def root(plugin, content_type="video"):
    cr = utils.init_crunchyroll_client()
    profiles = cr.get_multiprofile()
    if len(profiles['profiles']) > 1:
        return_profiles = []
        for profile in profiles['profiles']:
            params = {
                'profile_id': profile['profile_id']
            }
            return_profiles.append(Listitem.from_dict(menu, params=params, label=profile['profile_name']))
        return return_profiles
    return list(menu(plugin, profiles['profiles'][0]['profile_id']))


@Route.register
def menu(plugin, profile_id):
    cr = utils.init_crunchyroll_client()
    cr.auth.switch_profile(profile_id)
    if not ADDON.getSetting("crunchyroll_username"):
        ADDON.openSettings()

    yield Listitem.search(search)
    yield Listitem.from_dict(watchlist, label=ADDON.getLocalizedString(30067))
    yield Listitem.from_dict(popular, label=ADDON.getLocalizedString(30052))
    yield Listitem.from_dict(newly_added, label=ADDON.getLocalizedString(30059))
    yield Listitem.from_dict(alpha, label=ADDON.getLocalizedString(30055))
    yield Listitem.from_dict(categories, label=ADDON.getLocalizedString(30056))
    yield Listitem.from_dict(simulcast, label=ADDON.getLocalizedString(30053))
    yield Listitem.from_dict(my_lists, label=ADDON.getLocalizedString(30069))


# pylint: disable=W0613
@Route.register
def search(plugin, search_query, start=0):
    cr = utils.init_crunchyroll_client()
    series, next_link = cr.search_anime(search_query, start)
    if series:
        result = []
        for serie in series:
            infos = serie.to_dict()
            item = Listitem.from_dict(show_series, **infos)
            result.append(item)
        if next_link:
            result.append(Listitem.next_page(search_query=search_query, start=next_link['start']))
        return result
    return False


# pylint: disable=W0613
@Route.register
def watchlist(plugin, start=0):
    cr = utils.init_crunchyroll_client()
    episodes, next_link = cr.get_watchlist(start)
    if episodes:
        result = []
        for episode in episodes:
            infos = episode.to_dict()
            item = Listitem.from_dict(play_episode, **infos)
            result.append(item)
        if next_link:
            result.append(Listitem.next_page(start=next_link['start']))
        return result
    return False


# pylint: disable=W0613,W0102
@Route.register
def popular(plugin, start=0, categories_list=[]):
    cr = utils.init_crunchyroll_client()
    series, next_link = cr.get_popular(start=start, categories=categories_list)
    for serie in series:
        infos = serie.to_dict()
        item = Listitem.from_dict(show_series, **infos)
        yield item
    if next_link:
        yield Listitem.next_page(start=next_link['start'], categories_list=categories_list)


# pylint: disable=W0613,W0102
@Route.register
def newly_added(plugin, start=0, categories_list=[]):
    cr = utils.init_crunchyroll_client()
    series, next_link = cr.get_newly_added(start=start, categories=categories_list)
    for serie in series:
        infos = serie.to_dict()
        item = Listitem.from_dict(show_series, **infos)
        yield item
    if next_link:
        yield Listitem.next_page(start=next_link['start'], categories_list=categories_list)


# pylint: disable=W0613
@Route.register
def show_series(plugin, series_id):
    cr = utils.init_crunchyroll_client()
    seasons = cr.get_series_seasons(series_id)
    for season in seasons:
        infos = season.to_dict()
        item = Listitem.from_dict(show_season, **infos)
        yield item


# pylint: disable=W0613
@Route.register
def show_season(plugin, season_id):
    cr = utils.init_crunchyroll_client()
    episodes = cr.get_season_episodes(season_id)
    for episode in episodes:
        infos = episode.to_dict()
        item = Listitem.from_dict(play_episode, **infos)
        yield item


# pylint: disable=W0613
@Route.register
def alpha(plugin):
    cr = utils.init_crunchyroll_client()
    index = cr.get_alpha()
    for item in index:
        yield Listitem.from_dict(alpha_one, params={'start': item['start'], 'number': item['number']}, label=item['prefix'])


# pylint: disable=W0613
@Route.register
def alpha_one(plugin, start, number):
    cr = utils.init_crunchyroll_client()
    # We don't care about next_link, but it's returned anyway by browse method
    # pylint: disable=W0612
    series, next_link = cr.browse('alphabetical', start, number)
    for serie in series:
        infos = serie.to_dict()
        item = Listitem.from_dict(show_series, **infos)
        yield item


# pylint: disable=W0613
@Route.register
def categories(plugin):
    cr = utils.init_crunchyroll_client()
    categories_list = cr.get_categories()
    for category in categories_list:
        infos = category.to_dict()
        item = Listitem.from_dict(sub_category, **infos)
        yield item


# pylint: disable=W0613
@Route.register
def sub_category(plugin, category_id):
    cr = utils.init_crunchyroll_client()
    yield Listitem.from_dict(popular, params={"categories": [category_id]}, label=ADDON.getLocalizedString(30052))
    yield Listitem.from_dict(newly_added, params={"categories": [category_id]}, label=ADDON.getLocalizedString(30059))
    sub_categories_list = cr.get_sub_categories(category_id)
    for category in sub_categories_list:
        infos = category.to_dict()
        item = Listitem.from_dict(browse_sub_category, **infos)
        yield item


# pylint: disable=W0613
@Route.register
def browse_sub_category(plugin, categories_list, start=0):
    cr = utils.init_crunchyroll_client()
    series, next_link = cr.browse(start=start, categories=categories_list)
    for serie in series:
        infos = serie.to_dict()
        item = Listitem.from_dict(show_series, **infos)
        yield item
    if next_link:
        yield Listitem.next_page(start=next_link['start'], categories_list=categories_list)


# pylint: disable=W0613
@Route.register
def simulcast(plugin, start=0, season=None):
    cr = utils.init_crunchyroll_client()
    if not season:
        seasonal_tags = cr.get_seasonal_tags()
        season = seasonal_tags[0]['id']
    series, next_link = cr.browse(seasonal_tag=season, start=start)
    for serie in series:
        infos = serie.to_dict()
        item = Listitem.from_dict(show_series, **infos)
        yield item
    if next_link:
        yield Listitem.next_page(start=next_link['start'], season=season)


# pylint: disable=W0613
@Route.register
def my_lists(plugin):
    yield Listitem.from_dict(watchlist, label=ADDON.getLocalizedString(30067))
    yield Listitem.from_dict(crunchylists, label=ADDON.getLocalizedString(30068))
    yield Listitem.from_dict(history, label=ADDON.getLocalizedString(30042))


# pylint: disable=W0613
@Route.register
def crunchylists(plugin):
    cr = utils.init_crunchyroll_client()
    lists = cr.get_crunchylists()
    for item in lists:
        yield Listitem.from_dict(crunchylist, params={'list_id': item['list_id']}, label=item['title'])


# pylint: disable=W0613
@Route.register
def crunchylist(plugin, list_id):
    cr = utils.init_crunchyroll_client()
    series = cr.get_crunchylist(list_id)
    for serie in series:
        infos = serie.to_dict()
        item = Listitem.from_dict(show_series, **infos)
        yield item


# pylint: disable=W0613
@Route.register
def history(plugin, page=1):
    cr = utils.init_crunchyroll_client()
    episodes, next_link = cr.get_history(page)
    for episode in episodes:
        infos = episode.to_dict()
        item = Listitem.from_dict(play_episode, **infos)
        yield item
    if next_link:
        yield Listitem.next_page(page=next_link['page'])


# pylint: disable=W0613
@Resolver.register
def play_episode(plugin, episode_id):
    cr = utils.init_crunchyroll_client()
    from inputstreamhelper import Helper  # pylint: disable=import-outside-toplevel
    helper = Helper("mpd", drm='com.widevine.alpha')
    helper.check_inputstream()
    infos = cr.get_stream_infos(episode_id)
    item = Listitem()
    item.label = infos["name"]
    item.subtitles = utils.get_subtitles(episode_id, infos['subtitles'])
    item.set_path(infos['url'])
    listitem = item.listitem
    audio_code = utils.iso_639_1_to_iso_639_2(infos['actual_audio'])
    listitem.setProperty("audio_language", audio_code)
    listitem.setProperty("episode_id", episode_id)
    listitem.setMimeType('application/xml+dash')
    listitem.setContentLookup(False)
    listitem.setProperty('inputstream', 'inputstream.adaptive')
    listitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
    listitem.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
    manifest_headers = {
        'User-Agent': cr.auth.user_agent,
        'Authorization': infos['auth']
    }
    listitem.setProperty('inputstream.adaptive.manifest_headers', urlencode(manifest_headers))
    license_headers = {
        'User-Agent': cr.auth.user_agent,
        'Content-Type': 'application/octet-stream',
        'Origin': 'https://static.crunchyroll.com',
        'Authorization': infos['auth'],
        'x-cr-content-id': infos['stream_id'],
        'x-cr-video-token': infos['token']
    }
    license_config = {
        'license_server_url': utils.CRUNCHYROLL_LICENSE_URL,
        'headers': urlencode(license_headers),
        'post_data': 'R{SSM}',
        'reponse_data': 'JBlicense'
    }
    listitem.setProperty('inputstream.adaptive.license_key', '|'.join(list(license_config.values())))

    return item
