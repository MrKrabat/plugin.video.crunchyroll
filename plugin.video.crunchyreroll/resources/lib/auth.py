# -*- coding: utf-8 -*-
# Crunchyroll
# Copyright (C) 2023 Xtero
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

from datetime import datetime
import uuid
import requests
from requests.auth import AuthBase
# pylint: disable=E0401
from codequick.storage import PersistentDict
from . import utils


class CrunchyrollAuth(AuthBase):

    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.device_name = "Phone"
        self.device_type = "Kodi"

        with PersistentDict(f"crunchyroll_auth@{email}") as data:
            self.data = data

        with PersistentDict("device_uuid") as device_uuid:
            self.device_uuid = device_uuid

        if "uuid" not in list(self.device_uuid.keys()):
            self.device_uuid["uuid"] = str(uuid.uuid4())
            self.device_uuid.flush()

        # These are extracted from the Android application
        self.auth_headers = {
            "User-Agent": utils.CRUNCHYROLL_UA,
            "Authorization": "Basic bDBqdHgtZjNqZ3F0dWxxY3NnN246RkR1YU9KQUhOTjNiYnpzT1Y3TEZjQk5BSm1HTHFuVFE="
        }

        # Make sure all above fields are set
        if not self.is_auth():
            self._authenticate()

    def _store_token(self, data):
        self.data['access_token'] = data['access_token']
        self.data['refresh_token'] = data['refresh_token']
        self.data['expires_in'] = data['expires_in']
        self.data['scope'] = data['scope']
        self.data['country'] = data['country']
        self.data['account_id'] = data['account_id']
        self.data['profile_id'] = data['profile_id']
        now = datetime.timestamp(datetime.now())
        self.data['last_update'] = now
        # Store data for reuse
        self.data.flush()

    def _authenticate(self):
        data = {
            "username": self.email,
            "password": self.password,
            "grant_type": "password",
            "scope": "offline_access",
            "device_id": self.device_uuid["uuid"],
            "device_type": self.device_type,
            "device_name": self.device_name
        }
        url = f"{utils.CRUNCHYROLL_API_URL}/auth/v1/token"
        resp = requests.post(url, headers=self.auth_headers, data=data, timeout=10)
        resp.raise_for_status()
        self._store_token(resp.json())

    def _refresh(self):
        data = {
            "refresh_token": self.data['refresh_token'],
            "grant_type": "refresh_token",
            "scope": "offline_access",
            "device_id": self.device_uuid["uuid"],
            "device_type": self.device_type,
            "device_name": self.device_name
        }
        url = f"{utils.CRUNCHYROLL_API_URL}/auth/v1/token"
        resp = requests.post(url, headers=self.auth_headers, data=data, timeout=10)
        resp.raise_for_status()
        self._store_token(resp.json())

    def is_auth(self):
        last_update = self.data.get('last_update', 0)
        expires_in = self.data.get('expires_in', 0)
        now = datetime.timestamp(datetime.now())
        # If time is under last_update + expires_in, we assume we are still authenticated
        return now < (last_update + expires_in)

    def need_refresh(self):
        last_update = self.data.get('last_update', 0)
        expires_in = self.data.get('expires_in', 0)
        now = datetime.timestamp(datetime.now())
        return now > (last_update + expires_in*3/4)

    def __call__(self, request):
        if not self.is_auth():
            self._authenticate()
        elif self.need_refresh():
            self._refresh()

        request.headers['Authorization'] = f"Bearer {self.data['access_token']}"
        return request
