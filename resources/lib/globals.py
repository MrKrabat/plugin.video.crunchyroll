# -*- coding: utf-8 -*-
# Crunchyroll
# Copyright (C) 2024 smirgol
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

try:
    from urlparse import parse_qs
except ImportError:
    from urllib.parse import parse_qs


class Globals:
    def __init__(self):
        self.api = None  # we cannot type this, due to circular import in api.py
        self.args = None  # we cannot type this, due to circular import in model.py

    def init(self, argv) -> None:
        from resources.lib.api import API

        self.args = self.parse(argv)
        self.api = API(G.args.subtitle)

    @staticmethod
    def parse(argv):
        """Decode arguments
        """
        from resources.lib.model import Args

        if argv[2]:
            return Args(argv, parse_qs(argv[2][1:]))
        else:
            return Args(argv, {})


G = Globals()
