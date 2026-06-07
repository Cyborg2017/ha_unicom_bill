"""DataUpdateCoordinator for China Unicom Bill."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import UnicomAPI, UnicomAPIError
from .const import DEFAULT_REFRESH_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class UnicomBillCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for China Unicom Bill data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: UnicomAPI,
        refresh_interval: int = DEFAULT_REFRESH_INTERVAL,
        version: str = "unknown",
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=refresh_interval),
        )
        self.api = api
        self.version = version

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            data = await self.api.fetch_all_data()
            
            if not data:
                raise UpdateFailed("No data received from API")
                
            _LOGGER.info(
                "Data updated successfully: overview=%s, usage=%s, balance=%s",
                bool(data.get("overview")),
                bool(data.get("usage_details")),
                bool(data.get("balance_detail")),
            )
            
            return data

        except UnicomAPIError as err:
            raise UpdateFailed(f"API error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err
