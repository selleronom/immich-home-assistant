"""Hub for Immich integration."""

from __future__ import annotations

import logging
from urllib.parse import urljoin

import aiohttp

from homeassistant.exceptions import HomeAssistantError

_HEADER_API_KEY = "x-api-key"
_LOGGER = logging.getLogger(__name__)


class ImmichHub:
    """Immich API hub."""

    def __init__(self, host: str, api_key: str, verify_ssl: bool = True) -> None:
        """Initialize."""
        self.host = host
        self.api_key = api_key
        connector = aiohttp.TCPConnector(ssl=verify_ssl)
        self.session = aiohttp.ClientSession(connector=connector)  # Create one session

    async def close_session(self) -> None:
        """Close session when done."""
        await self.session.close()

    async def authenticate(self) -> bool:
        """Test if we can authenticate with the host."""
        try:
            url = urljoin(self.host, "/api/auth/validateToken")
            headers = {"Accept": "application/json", _HEADER_API_KEY: self.api_key}

            async with self.session.post(url=url, headers=headers) as response:
                if response.status != 200:
                    raw_result = await response.text()
                    _LOGGER.error("Error from API: body=%s", raw_result)
                    return False

                auth_result = await response.json()

                if not auth_result.get("authStatus"):
                    raw_result = await response.text()
                    _LOGGER.error("Error from API: body=%s", raw_result)
                    return False

                return True
        except aiohttp.ClientError as exception:
            _LOGGER.error("Error connecting to the API: %s", exception)
            raise CannotConnect from exception

    async def get_my_user_info(self) -> dict:
        """Get user info."""
        try:
            url = urljoin(self.host, "/api/users/me")
            headers = {"Accept": "application/json", _HEADER_API_KEY: self.api_key}

            async with self.session.get(url=url, headers=headers) as response:
                if response.status != 200:
                    raw_result = await response.text()
                    _LOGGER.error("Error from API: body=%s", raw_result)
                    raise ApiError()

                user_info: dict = await response.json()

                return user_info
        except aiohttp.ClientError as exception:
            _LOGGER.error("Error connecting to the API: %s", exception)
            raise CannotConnect from exception

    async def get_asset_info(self, asset_id: str) -> dict | None:
        """Get asset info."""
        try:
            url = urljoin(self.host, f"/api/assets/{asset_id}")
            headers = {"Accept": "application/json", _HEADER_API_KEY: self.api_key}

            async with self.session.get(url=url, headers=headers) as response:
                if response.status != 200:
                    raw_result = await response.text()
                    _LOGGER.error("Error from API: body=%s", raw_result)
                    raise ApiError()

                asset_info: dict = await response.json()

                return asset_info
        except aiohttp.ClientError as exception:
            _LOGGER.error("Error connecting to the API: %s", exception)
            raise CannotConnect from exception

    async def download_asset(self, asset_id: str) -> bytes | None:
        """Download the asset."""
        try:
            url = urljoin(self.host, f"/api/assets/{asset_id}/thumbnail?size=preview")
            headers = {_HEADER_API_KEY: self.api_key}

            async with self.session.get(url=url, headers=headers) as response:
                if response.status != 200:
                    _LOGGER.error("Error from API: status=%d", response.status)
                    return None

                return await response.read()
        except aiohttp.ClientError as exception:
            _LOGGER.error("Error connecting to the API: %s", exception)
            raise CannotConnect from exception

    async def list_favorite_images(self) -> list[dict]:
        """List all favorite images."""
        try:
            url = urljoin(self.host, "/api/search/metadata")
            headers = {"Accept": "application/json", _HEADER_API_KEY: self.api_key}
            data = {"isFavorite": "true"}

            async with self.session.post(
                url=url, headers=headers, data=data
            ) as response:
                if response.status != 200:
                    raw_result = await response.text()
                    _LOGGER.error("Error from API: body=%s", raw_result)
                    raise ApiError()

                favorites = await response.json()
                assets: list[dict] = favorites["assets"]["items"]

                filtered_assets: list[dict] = [
                    asset for asset in assets if asset["type"] == "IMAGE"
                ]

                return filtered_assets
        except aiohttp.ClientError as exception:
            _LOGGER.error("Error connecting to the API: %s", exception)
            raise CannotConnect from exception

    async def list_all_albums(self) -> list[dict]:
        """List all albums."""
        try:
            url = urljoin(self.host, "/api/albums")
            headers = {"Accept": "application/json", _HEADER_API_KEY: self.api_key}

            async with self.session.get(url=url, headers=headers) as response:
                if response.status != 200:
                    raw_result = await response.text()
                    _LOGGER.error("Error from API: body=%s", raw_result)
                    raise ApiError()

                album_list: list[dict] = await response.json()

                return album_list
        except aiohttp.ClientError as exception:
            _LOGGER.error("Error connecting to the API: %s", exception)
            raise CannotConnect from exception

    async def list_album_images(self, album_id: str) -> list[dict]:
        """List all images in an album."""
        try:
            url = urljoin(self.host, f"/api/albums/{album_id}")
            headers = {"Accept": "application/json", _HEADER_API_KEY: self.api_key}

            async with self.session.get(url=url, headers=headers) as response:
                if response.status != 200:
                    raw_result = await response.text()
                    _LOGGER.error("Error from API: body=%s", raw_result)
                    raise ApiError()

                album_info: dict = await response.json()
                assets: list[dict] = album_info["assets"]

                filtered_assets: list[dict] = [
                    asset for asset in assets if asset["type"] == "IMAGE"
                ]

                return filtered_assets
        except aiohttp.ClientError as exception:
            _LOGGER.error("Error connecting to the API: %s", exception)
            raise CannotConnect from exception

    async def list_memory_lane_images(self) -> list[dict]:
        """Fetch today's memory lane images."""
        from datetime import datetime

        date = datetime.now()
        day = date.day
        month = date.month

        url = urljoin(self.host, f"/api/assets/memory-lane?day={day}&month={month}")
        headers = {"Accept": "application/json", _HEADER_API_KEY: self.api_key}

        async with self.session.get(url=url, headers=headers) as response:
            if response.status != 200:
                raw_result = await response.text()
                _LOGGER.error("Error from API: body=%s", raw_result)
                raise ApiError()

            items: list[dict] = await response.json()
            assets = []
            for item in items:
                for asset in item["assets"]:
                    if asset.get("type") == "IMAGE":
                        assets.append(asset)
            return assets


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class ApiError(HomeAssistantError):
    """Error to indicate that the API returned an error."""
