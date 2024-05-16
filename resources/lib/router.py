# -*- coding: utf-8 -*-
# Crunchyroll
# Copyright (C) 2023 lumiru
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
from typing import Optional

# A URL is formatted with {parameters}, each parameter are passed to controller args.
# The "mode" option will be passed to args if set.
plugin_routes: dict = {
    "main_submenu": {
        "url": "/menu/{mode}"
    },
    "main_submenu_with_offset": {
        "url": "/menu/{mode}/offset/{offset}"
    },
    "genre_submenu": {
        "url": "/menu/{mode}/{genre}"
    },
    "genre_submenu_with_offset": {
        "url": "/menu/{mode}/{genre}/offset/{offset}"
    },
    "category_submenu": {
        "url": "/menu/{mode}/{genre}/category/{category_filter}"
    },
    "category_submenu_with_offset": {
        "url": "/menu/{mode}/{genre}/category/{category_filter}/offset/{offset}"
    },
    "season_submenu": {
        "url": "/menu/{mode}/{genre}/season/{season_filter}"
    },
    "season_submenu_with_offset": {
        "url": "/menu/{mode}/{genre}/season/{season_filter}/offset/{offset}"
    },
    "crunchylist_view": {
        "url": "/crunchylist/{crunchylists_item_id}",
        "mode": "crunchylists_item"
    },
    "series_view": {
        "url": "/series/{series_id}",
        "mode": "seasons"
    },
    "season_view": {
        "url": "/series/{series_id}/{season_id}",
        "mode": "episodes"
    },
    "season_view_with_offset": {
        "url": "/series/{series_id}/{season_id}/offset/{offset}",
        "mode": "episodes"
    },
    "video_episode_play": {
        "url": "/video/{series_id}/{episode_id}/{stream_id}",
        "mode": "videoplay"
    },
    "video_movie_play": {
        "url": "/video/{episode_id}/{stream_id}",
        "mode": "videoplay"
    },
    "profiles_view": {
        "url": "/profiles/{mode}",
        "mode": "profiles_list"
    },
}


def extract_url_params(url: str) -> Optional[dict]:
    """
    The router logic itself.
    It iterates over routes and return params for the first found matching pattern (which should be the only one).
    """

    for route_name, route_conf in plugin_routes.items():
        pattern = route_conf.get("url")
        if pattern[0] == "/":
            pattern = pattern[1:]
        regexp = "^/?" + pattern.replace("{", "(?P<").replace("}", ">[^/]+)") + "$"
        result = re.match(regexp, url)
        if result is not None:
            resp = result.groupdict()
            resp["current_route"] = route_name
            if not resp.get("mode"):
                resp["mode"] = route_conf.get("mode")
            return resp

    return None


def build_path(args: dict) -> Optional[str]:
    """
    Build URL from plugin list item args.
    It will use the route configuration designated by "route" arg.
    If "route" arg was not set, it will try to find a URL matching the "mode" arg and other available args.
    """

    route_name = args.get("route")
    if not route_name:
        route_name = find_route_matching_args(args)
        if not route_name:
            return None
    return create_path_from_route(route_name, args)


def find_route_matching_args(args: dict) -> Optional[str]:
    """
    Try to get the best matching route to given "mode" arg and plugin list item args.
    """

    # Get all routes matching mode
    routes_matching_mode = filter_routes_by_mode(args.get("mode"))
    # Extract parameter list for each route
    params_by_route_matching_mode = {
        route_name: extract_params_from_pattern(route_conf.get("url"))
        for route_name, route_conf in routes_matching_mode.items()
    }
    # Filter out routes that require non-existing args
    filtered_params = {
        route: params
        for route, params in params_by_route_matching_mode.items()
        if check_args_contains_params(args, params)
    }
    # Choose the best one by looking for the largest parameter count
    param_number: int = 0
    selected_route: str | None = None
    for route, params in filtered_params.items():
        if len(params) > param_number:
            param_number = len(params)
            selected_route = route
    if not selected_route:
        return None
    return selected_route


def create_path_from_route(route_name: str, args: dict) -> Optional[str]:
    """
    Build URL from a route name and plugin list item args.
    """

    # Retrieve pattern
    route = plugin_routes.get(route_name)
    if not route:
        return None
    result = route.get("url")
    # Replace each {parameter} by its value from args
    pattern_params = extract_params_from_pattern(result)
    for param in pattern_params:
        result = result.replace("{%s}" % param, str(args.get(param)))
    return result


def filter_routes_by_mode(searching_mode: str) -> dict:
    """
    Filter routes by mode.
    If no route was found for requested mode, return all routes without mode set.
    """

    __PARAMETER_ROUTE_MODE__ = "__no_mode_set"
    # TODO: Cache it
    routes_by_mode = {}
    for route_name, route_conf in plugin_routes.items():
        mode = route_conf.get("mode", __PARAMETER_ROUTE_MODE__)
        if not routes_by_mode.get(mode):
            routes_by_mode[mode] = {}
        routes_by_mode.get(mode)[route_name] = route_conf

    if not routes_by_mode.get(searching_mode):
        return routes_by_mode.get(__PARAMETER_ROUTE_MODE__)

    return routes_by_mode.get(searching_mode)


def extract_params_from_pattern(pattern: str) -> list:
    return re.findall(r"\{([^}]+)}", pattern)


def check_args_contains_params(args: dict, params: list) -> bool:
    for param in params:
        if not args.get(param):
            return False
    return True
