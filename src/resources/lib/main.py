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

from codequick import run, Route, Resolver, Listitem
from .client import CrunchyrollClient
import xbmcaddon
import xbmc
from . import utils

addon = xbmcaddon.Addon(id=utils.ADDON_ID)
email = addon.getSetting("crunchyroll_username")
password = addon.getSetting("crunchyroll_password")
locale = utils.local_from_id(addon.getSetting("subtitle_language"))
cr = CrunchyrollClient(email, password, locale) 

@Route.register
def root(plugin, content_type="video"):
    yield Listitem.search(search)
    yield Listitem.from_dict(watchlist, label=addon.getLocalizedString(30067))
    yield Listitem.from_dict(popular, label=addon.getLocalizedString(30052))
    yield Listitem.from_dict(newly_added, label=addon.getLocalizedString(30059))
    yield Listitem.from_dict(alpha, label=addon.getLocalizedString(30055))
    yield Listitem.from_dict(category, label=addon.getLocalizedString(30056))
    yield Listitem.from_dict(simulcast, label=addon.getLocalizedString(30053))

@Route.register
def search(plugin, search_query, start=0):
    series, nextLink = cr.search_anime(search_query, start)
    for serie in series:
        infos = serie.to_dict()
        item = Listitem.from_dict(show_series,**infos)
        yield item
    if nextLink:
        yield Listitem.next_page(search_query=search_query, start=nextLink['start'])

@Route.register
def watchlist(plugin, start=0):
    episodes, nextLink = cr.watchlist(start)
    for episode in episodes:
        infos = episode.to_dict()
        item = Listitem.from_dict(play_show,**infos)
        yield item
    if nextLink:
        yield Listitem.next_page(start=nextLink['start'])

@Route.register
def popular(plugin, start=0, categories=[]):
    series, nextLink = cr.popular(start=start, categories=categories)
    for serie in series:
        infos = serie.to_dict()
        item = Listitem.from_dict(show_series,**infos)
        yield item
    if nextLink:
        yield Listitem.next_page(start=nextLink['start'], categories=categories)

@Route.register
def newly_added(plugin, start=0, categories=[]):
    series, nextLink = cr.newly_added(start=start, categories=categories)
    for serie in series:
        infos = serie.to_dict()
        item = Listitem.from_dict(show_series,**infos)
        yield item
    if nextLink:
        yield Listitem.next_page(start=nextLink['start'], categories=categories)


@Route.register
def show_series(plugin, id):
    seasons = cr.get_series_seasons(id)
    for season in seasons:
        infos = season.to_dict()
        item = Listitem.from_dict(show_season,**infos)
        yield item 
    

@Route.register
def show_season(plugin, id):
    episodes = cr.get_season_episodes(id)
    for episode in episodes:
        infos = episode.to_dict()
        item = Listitem.from_dict(play_show,**infos)
        yield item

@Route.register
def alpha(plugin):
    index = cr.alpha()
    for item in index:
        yield Listitem.from_dict(alpha_one, params = {'start': item['start'], 'number': item['number']}, label = item['prefix'])

@Route.register
def alpha_one(plugin, start, number):
    # We don't care about nextLink, but it's send anyway by browse method
    series, nextLink = cr.browse('alphabetical', start, number)
    for serie in series:
        infos = serie.to_dict()
        item = Listitem.from_dict(show_series,**infos)
        yield item
    
@Route.register
def category(plugin):
    categories = cr.get_categories()
    for category in categories:
        infos = category.to_dict()
        item = Listitem.from_dict(sub_category,**infos)
        yield item
        
@Route.register
def sub_category(plugin, category_id):
    yield Listitem.from_dict(popular, params = {"categories": [category_id]}, label=addon.getLocalizedString(30052))
    yield Listitem.from_dict(newly_added, params = {"categories": [category_id]}, label=addon.getLocalizedString(30059))
    sub_categories = cr.get_sub_categories(category_id)
    for category in sub_categories:
        infos = category.to_dict()
        item = Listitem.from_dict(browse_sub_category, **infos)
        yield item

@Route.register
def browse_sub_category(plugin, categories, start=0):
    series, nextLink = cr.browse(start=start, categories=categories)
    for serie in series:
        infos = serie.to_dict()
        item = Listitem.from_dict(show_series,**infos)
        yield item
    if nextLink:
        yield Listitem.next_page(start=nextLink['start'], categories=categories)

@Route.register
def simulcast(plugin, start=0, season=None):
    if not season:
        seasonal_tags = cr.get_seasonal_tags()
        season = seasonal_tags[0]['id']
    series,nextLink = cr.browse(seasonal_tag=season,start=start)
    for serie in series:
        infos = serie.to_dict()
        item = Listitem.from_dict(show_series,**infos)
        yield item
    if nextLink:
        yield Listitem.next_page(start=nextLink['start'], season=season)

    
@Resolver.register
def play_show(plugin, id):
    return cr.get_stream_url(id)
