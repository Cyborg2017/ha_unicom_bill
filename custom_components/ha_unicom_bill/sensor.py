"""Sensor platform for China Unicom Bill."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfInformation, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.network import get_url
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CREATE_INDIVIDUAL_SENSORS, CONF_PHONE_NUMBER, DOMAIN
from .coordinator import UnicomBillCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class UnicomSensorEntityDescription(SensorEntityDescription):
    """China Unicom sensor description."""

    value_fn: Callable[[dict], Any]
    attributes_fn: Callable[[dict], dict[str, Any]] | None = None


def _parse_mb(value: str | float | None) -> float:
    """Parse MB value from string or number."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        # Remove unit suffix if present
        s = str(value).upper().replace("MB", "").replace("GB", "").strip()
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def _mb_to_display(mb_value: float) -> tuple[float, str]:
    """Convert MB to appropriate display unit."""
    if mb_value >= 1024:
        return round(mb_value / 1024, 2), "GB"
    return round(mb_value, 2), "MB"


# Basic sensors (always created)
BASIC_SENSOR_DESCRIPTIONS: list[UnicomSensorEntityDescription] = [
    UnicomSensorEntityDescription(
        key="voice_usage",
        translation_key="voice_usage",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:phone",
        value_fn=lambda data: (
            int(float(data.get("usage_details", {}).get("voice", {}).get("use", 0)))
            if data.get("usage_details", {}).get("voice")
            else None
        ),
        attributes_fn=lambda data: {
            "total": data.get("usage_details", {}).get("voice", {}).get("total"),
            "available": data.get("usage_details", {}).get("voice", {}).get("remain"),
            "usage_ratio": f"{data.get('usage_details', {}).get('voice', {}).get('usedPercent', 'N/A')}%",
        } if data.get("usage_details", {}).get("voice") else {},
    ),
    UnicomSensorEntityDescription(
        key="sms_usage",
        translation_key="sms_usage",
        state_class=SensorStateClass.TOTAL,
        icon="mdi:message-text",
        value_fn=lambda data: (
            int(float(data.get("usage_details", {}).get("sms", {}).get("use", 0)))
            if data.get("usage_details", {}).get("sms")
            else None
        ),
        attributes_fn=lambda data: {
            "total": data.get("usage_details", {}).get("sms", {}).get("total"),
            "available": data.get("usage_details", {}).get("sms", {}).get("remain"),
            "usage_ratio": f"{data.get('usage_details', {}).get('sms', {}).get('usedPercent', 'N/A')}%",
        } if data.get("usage_details", {}).get("sms") else {},
    ),
    UnicomSensorEntityDescription(
        key="data_usage",
        translation_key="data_usage",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        icon="mdi:cellphone-link",
        value_fn=lambda data: (
            round(
                sum(_parse_mb(item.get("use")) for item in data.get("usage_details", {}).get("data_items", [])) / 1024,
                2
            ) if data.get("usage_details", {}).get("data_items") else None
        ),
        attributes_fn=lambda data: (
            _build_data_attributes(data) if data.get("usage_details", {}).get("data_items") else {}
        ),
    ),
    UnicomSensorEntityDescription(
        key="balance",
        translation_key="balance",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="CNY",
        icon="mdi:wallet",
        value_fn=lambda data: (
            float(data.get("balance_detail", {}).get("canusefeecustNew", 
                   data.get("balance_detail", {}).get("canusefeecust", 0)))
            if data.get("balance_detail")
            else None
        ),
        attributes_fn=lambda data: {
            "current_balance": data.get("balance_detail", {}).get("curntbalancecust"),
            "real_time_fee": data.get("balance_detail", {}).get("totalrealfee", 
                         data.get("balance_detail", {}).get("realfeecustnew")),
            "total_owed": data.get("balance_detail", {}).get("allbowefeecust"),
            "credit_limit": data.get("balance_detail", {}).get("canuselimitcust"),
        } if data.get("balance_detail") else {},
    ),
]

# Detailed sensors (optional)
DETAILED_SENSOR_DESCRIPTIONS: list[UnicomSensorEntityDescription] = [
    UnicomSensorEntityDescription(
        key="voice_total",
        translation_key="voice_total",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:phone",
        value_fn=lambda data: (
            int(float(data.get("usage_details", {}).get("voice", {}).get("total", 0)))
            if data.get("usage_details", {}).get("voice")
            else None
        ),
    ),
    UnicomSensorEntityDescription(
        key="voice_available",
        translation_key="voice_available",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:phone-check",
        value_fn=lambda data: (
            int(float(data.get("usage_details", {}).get("voice", {}).get("remain", 0)))
            if data.get("usage_details", {}).get("voice")
            else None
        ),
    ),
    UnicomSensorEntityDescription(
        key="voice_ratio",
        translation_key="voice_ratio",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        icon="mdi:percent",
        value_fn=lambda data: (
            round(float(data.get("usage_details", {}).get("voice", {}).get("usedPercent", 0)), 2)
            if data.get("usage_details", {}).get("voice")
            else None
        ),
    ),
    UnicomSensorEntityDescription(
        key="sms_total",
        translation_key="sms_total",
        state_class=SensorStateClass.TOTAL,
        icon="mdi:message-text",
        value_fn=lambda data: (
            int(float(data.get("usage_details", {}).get("sms", {}).get("total", 0)))
            if data.get("usage_details", {}).get("sms")
            else None
        ),
    ),
    UnicomSensorEntityDescription(
        key="sms_available",
        translation_key="sms_available",
        state_class=SensorStateClass.TOTAL,
        icon="mdi:message-check",
        value_fn=lambda data: (
            int(float(data.get("usage_details", {}).get("sms", {}).get("remain", 0)))
            if data.get("usage_details", {}).get("sms")
            else None
        ),
    ),
    UnicomSensorEntityDescription(
        key="data_total",
        translation_key="data_total",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        icon="mdi:database",
        value_fn=lambda data: (
            round(
                sum(_parse_mb(item.get("total")) for item in data.get("usage_details", {}).get("data_items", [])) / 1024,
                2
            ) if data.get("usage_details", {}).get("data_items") else None
        ),
    ),
    UnicomSensorEntityDescription(
        key="data_available",
        translation_key="data_available",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        icon="mdi:database-check",
        value_fn=lambda data: (
            round(
                sum(_parse_mb(item.get("remain")) for item in data.get("usage_details", {}).get("data_items", []) if item.get("remain")) / 1024,
                2
            ) if data.get("usage_details", {}).get("data_items") else None
        ),
    ),
    UnicomSensorEntityDescription(
        key="data_exceed",
        translation_key="data_exceed",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        icon="mdi:database-alert",
        value_fn=lambda data: (
            round(
                sum(_parse_mb(item.get("xexceedvalue")) for item in data.get("usage_details", {}).get("data_items", []) if item.get("xexceedvalue")) / 1024,
                2
            ) if data.get("usage_details", {}).get("data_items") else None
        ),
    ),
    UnicomSensorEntityDescription(
        key="data_ratio",
        translation_key="data_ratio",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        icon="mdi:percent",
        value_fn=lambda data: (
            _calc_data_ratio(data) if data.get("usage_details", {}).get("data_items") else None
        ),
    ),
    UnicomSensorEntityDescription(
        key="real_fee",
        translation_key="real_fee",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="CNY",
        icon="mdi:currency-cny",
        value_fn=lambda data: (
            float(data.get("balance_detail", {}).get("totalrealfee", 
                   data.get("balance_detail", {}).get("realfeecustnew", 0)))
            if data.get("balance_detail")
            else None
        ),
    ),
    UnicomSensorEntityDescription(
        key="can_use_value",
        translation_key="can_use_value",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="CNY",
        icon="mdi:cash-multiple",
        value_fn=lambda data: (
            float(data.get("balance_detail", {}).get("curntbalancecust", 0))
            if data.get("balance_detail")
            else None
        ),
    ),
    UnicomSensorEntityDescription(
        key="total_owed",
        translation_key="total_owed",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="CNY",
        icon="mdi:cash-minus",
        value_fn=lambda data: (
            float(data.get("balance_detail", {}).get("allbowefeecust", 0))
            if data.get("balance_detail")
            else None
        ),
    ),
]


def _build_data_attributes(data: dict) -> dict[str, Any]:
    """Build data usage attributes."""
    usage = data.get("usage_details", {})
    data_items = usage.get("data_items", [])
    if not data_items:
        return {}
    
    total_use_mb = sum(_parse_mb(item.get("use")) for item in data_items)
    total_total_mb = sum(_parse_mb(item.get("total")) for item in data_items)
    total_remain_mb = sum(_parse_mb(item.get("remain")) for item in data_items if item.get("remain"))
    total_exceed_mb = sum(_parse_mb(item.get("xexceedvalue")) for item in data_items if item.get("xexceedvalue"))
    ratio = round(total_use_mb / total_total_mb * 100, 2) if total_total_mb > 0 else 0
    
    return {
        "used": f"{_mb_to_display(total_use_mb)[0]} {_mb_to_display(total_use_mb)[1]}",
        "total": f"{_mb_to_display(total_total_mb)[0]} {_mb_to_display(total_total_mb)[1]}",
        "available": f"{_mb_to_display(total_remain_mb)[0]} {_mb_to_display(total_remain_mb)[1]}",
        "exceeded": f"{_mb_to_display(total_exceed_mb)[0]} {_mb_to_display(total_exceed_mb)[1]}",
        "usage_ratio": f"{ratio}%",
        "package_count": len(data_items),
    }


def _calc_data_ratio(data: dict) -> float | None:
    """Calculate data usage ratio."""
    usage = data.get("usage_details", {})
    data_items = usage.get("data_items", [])
    if not data_items:
        return None
    
    total_use_mb = sum(_parse_mb(item.get("use")) for item in data_items)
    total_total_mb = sum(_parse_mb(item.get("total")) for item in data_items)
    
    return round(total_use_mb / total_total_mb * 100, 2) if total_total_mb > 0 else 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: UnicomBillCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    create_individual = entry.data.get(CONF_CREATE_INDIVIDUAL_SENSORS, False)
    
    entities: list[UnicomBillSensor] = []
    
    # Build configuration URL
    try:
        base_url = get_url(hass, prefer_external=False)
        config_url = f"{base_url}/config/integrations/integration/{DOMAIN}"
    except Exception:
        config_url = None

    # Always create basic sensors
    for desc in BASIC_SENSOR_DESCRIPTIONS:
        entities.append(
            UnicomBillSensor(
                coordinator=coordinator,
                entry=entry,
                description=desc,
                config_url=config_url,
            )
        )
    
    # Optionally create detailed sensors
    if create_individual:
        for desc in DETAILED_SENSOR_DESCRIPTIONS:
            entities.append(
                UnicomBillSensor(
                    coordinator=coordinator,
                    entry=entry,
                    description=desc,
                    config_url=config_url,
                )
            )
    
    async_add_entities(entities)


class UnicomBillSensor(CoordinatorEntity[UnicomBillCoordinator], SensorEntity):
    """China Unicom bill sensor entity."""

    _attr_has_entity_name = True

    entity_description: UnicomSensorEntityDescription

    def __init__(
        self,
        coordinator: UnicomBillCoordinator,
        entry: ConfigEntry,
        description: UnicomSensorEntityDescription,
        config_url: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        
        # Get phone number from config (may be masked like 123****7890)
        phone_number = entry.data.get(CONF_PHONE_NUMBER, "")
        
        # Device name is just the phone number
        device_name = phone_number if phone_number else "China Unicom"
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=device_name,
            manufacturer="China Unicom",
            model="Bill Query Integration",
            sw_version=coordinator.version,
            configuration_url=config_url,
        )
        
        # Entity ID uses phone number with * removed for cleaner IDs
        if phone_number:
            # Remove * characters to get clean digits for entity ID
            clean_phone = phone_number.replace("*", "")
            self.entity_id = f"sensor.unicom_{clean_phone}_{description.key}"
        else:
            self.entity_id = f"sensor.{DOMAIN}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the state."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data or not self.entity_description.attributes_fn:
            return {}
        return self.entity_description.attributes_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
