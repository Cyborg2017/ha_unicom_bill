"""The China Unicom Bill integration."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from aiohttp import ClientSession
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import UnicomAPI
from .const import DOMAIN, PLATFORMS
from .coordinator import UnicomBillCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up China Unicom Bill from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Read version from manifest.json asynchronously
    try:
        manifest_path = Path(__file__).parent / "manifest.json"
        version = await hass.async_add_executor_job(
            _read_manifest_version, manifest_path
        )
    except Exception:
        version = "unknown"

    # Create API instance
    api = UnicomAPI(
        session=ClientSession(),
        openid=entry.data["openid"],
        usage_ticket=entry.data.get("manual_ticket", ""),
        micro_hall_user=entry.data.get("manual_cookie", ""),
        micro_hall_access_token=entry.data.get("manual_microhall_cookie", ""),
    )

    # Try to auto-detect phone number from API if not configured
    phone_number = entry.data.get("phone_number", "")
    if not phone_number:
        try:
            _LOGGER.info("Attempting to auto-detect phone number from API...")
            detected_phone = await api.get_phone_number()
            if detected_phone:
                _LOGGER.info("Auto-detected phone number: %s", detected_phone)
                # Update config entry with detected phone number
                new_data = {**entry.data, "phone_number": detected_phone}
                hass.config_entries.async_update_entry(entry, data=new_data)
                phone_number = detected_phone
            else:
                _LOGGER.info("Could not auto-detect phone number from API")
        except Exception as err:
            _LOGGER.warning("Failed to auto-detect phone number: %s", err)

    # Create coordinator
    refresh_interval = entry.data.get("refresh_interval", 15)
    coordinator = UnicomBillCoordinator(
        hass=hass,
        api=api,
        refresh_interval=refresh_interval,
        version=version,
    )

    # Store coordinator in hass.data
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Trigger initial data refresh
    await coordinator.async_config_entry_first_refresh()

    # Forward to sensor platform
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    )

    return True


def _read_manifest_version(manifest_path: Path) -> str:
    """Read version from manifest.json (runs in executor)."""
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    return manifest.get("version", "unknown")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # Close API session
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.api.session.close()
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
