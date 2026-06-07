"""Sensor platform for China Unicom Bill."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.network import get_url
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ALL_SENSORS,
    CONF_CREATE_INDIVIDUAL_SENSORS,
    DOMAIN,
    NAME,
    SENSOR_CAN_USE_VALUE,
    SENSOR_CREDIT_VALUE,
    SENSOR_DATA_AVAILABLE,
    SENSOR_DATA_EXCEED,
    SENSOR_DATA_RATIO,
    SENSOR_DATA_TOTAL,
    SENSOR_DATA_USAGE,
    SENSOR_REAL_FEE,
    SENSOR_SMS_AVAILABLE,
    SENSOR_SMS_TOTAL,
    SENSOR_SMS_USAGE,
    SENSOR_TOTAL_OWED,
    SENSOR_VOICE_AVAILABLE,
    SENSOR_VOICE_RATIO,
    SENSOR_VOICE_TOTAL,
    SENSOR_VOICE_USAGE,
)
from .coordinator import UnicomBillCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the sensor platform."""
    coordinator: UnicomBillCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    create_individual = entry.data.get(CONF_CREATE_INDIVIDUAL_SENSORS, False)
    
    entities = []
    
    # Always create basic sensors
    entities.extend([
        UnicomVoiceUsageSensor(coordinator, entry),
        UnicomSmsUsageSensor(coordinator, entry),
        UnicomDataUsageSensor(coordinator, entry),
        UnicomBalanceSensor(coordinator, entry),
    ])
    
    # Optionally create detailed sensors
    if create_individual:
        entities.extend([
            UnicomVoiceTotalSensor(coordinator, entry),
            UnicomVoiceAvailableSensor(coordinator, entry),
            UnicomVoiceRatioSensor(coordinator, entry),
            UnicomSmsTotalSensor(coordinator, entry),
            UnicomSmsAvailableSensor(coordinator, entry),
            UnicomDataTotalSensor(coordinator, entry),
            UnicomDataAvailableSensor(coordinator, entry),
            UnicomDataExceedSensor(coordinator, entry),
            UnicomDataRatioSensor(coordinator, entry),
            UnicomRealFeeSensor(coordinator, entry),
            UnicomCanUseValueSensor(coordinator, entry),
        ])
    
    async_add_entities(entities)


def _parse_mb(value_str: str | float | None) -> float:
    """Parse MB value from string or number."""
    if not value_str:
        return 0.0
    try:
        if isinstance(value_str, (int, float)):
            return float(value_str)
        val = float(str(value_str).replace("MB", "").replace("GB", "").strip())
        if "GB" in str(value_str):
            val *= 1024
        return val
    except (ValueError, AttributeError):
        return 0.0


def _mb_to_display(mb_value: float) -> tuple[float, str]:
    """Convert MB to appropriate display unit."""
    if mb_value >= 1024:
        return round(mb_value / 1024, 2), "GB"
    return round(mb_value, 2), "MB"


class UnicomBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for Unicom sensors."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: UnicomBillCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        
        # Build configuration URL
        try:
            base_url = get_url(self.hass, prefer_external=False)
            self._config_url = f"{base_url}/config/integrations/integration/{DOMAIN}"
        except Exception:
            self._config_url = None

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="中国联通",
            manufacturer="中国联通",
            model="话费查询集成",
            sw_version=self.coordinator.version,
            configuration_url=self._config_url,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class UnicomVoiceUsageSensor(UnicomBaseSensor):
    """语音用量传感器."""

    def __init__(self, coordinator: UnicomBillCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_voice_usage"
        self._attr_name = "语音用量"
        self._attr_native_unit_of_measurement = "分钟"

    @property
    def native_value(self) -> float | None:
        """Return the state."""
        if not self.coordinator.data:
            return None
        usage = self.coordinator.data.get("usage_details", {})
        voice = usage.get("voice")
        if voice:
            try:
                return float(voice.get("use", 0))
            except (ValueError, TypeError):
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}
        usage = self.coordinator.data.get("usage_details", {})
        voice = usage.get("voice", {})
        return {
            "总量": voice.get("total"),
            "可用": voice.get("remain"),
            "使用比例": f"{voice.get('usedPercent', 'N/A')}%",
        }


class UnicomSmsUsageSensor(UnicomBaseSensor):
    """短信用量传感器."""

    def __init__(self, coordinator: UnicomBillCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_sms_usage"
        self._attr_name = "短信用量"
        self._attr_native_unit_of_measurement = "条"

    @property
    def native_value(self) -> float | None:
        """Return the state."""
        if not self.coordinator.data:
            return None
        usage = self.coordinator.data.get("usage_details", {})
        sms = usage.get("sms")
        if sms:
            try:
                return float(sms.get("use", 0))
            except (ValueError, TypeError):
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}
        usage = self.coordinator.data.get("usage_details", {})
        sms = usage.get("sms", {})
        return {
            "总量": sms.get("total"),
            "可用": sms.get("remain"),
            "使用比例": f"{sms.get('usedPercent', 'N/A')}%",
        }


class UnicomDataUsageSensor(UnicomBaseSensor):
    """流量用量传感器."""

    def __init__(self, coordinator: UnicomBillCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_data_usage"
        self._attr_name = "流量用量"

    @property
    def native_value(self) -> float | None:
        """Return the state."""
        if not self.coordinator.data:
            return None
        usage = self.coordinator.data.get("usage_details", {})
        data_items = usage.get("data_items", [])
        if data_items:
            total_use_mb = sum(_parse_mb(item.get("use")) for item in data_items)
            value, unit = _mb_to_display(total_use_mb)
            self._attr_native_unit_of_measurement = unit
            return value
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}
        usage = self.coordinator.data.get("usage_details", {})
        data_items = usage.get("data_items", [])
        if data_items:
            total_use_mb = sum(_parse_mb(item.get("use")) for item in data_items)
            total_total_mb = sum(_parse_mb(item.get("total")) for item in data_items)
            total_remain_mb = sum(
                _parse_mb(item.get("remain")) for item in data_items if item.get("remain")
            )
            total_exceed_mb = sum(
                _parse_mb(item.get("xexceedvalue"))
                for item in data_items
                if item.get("xexceedvalue")
            )
            ratio = round(total_use_mb / total_total_mb * 100, 2) if total_total_mb > 0 else 0
            
            return {
                "已用": f"{_mb_to_display(total_use_mb)[0]} {_mb_to_display(total_use_mb)[1]}",
                "总量": f"{_mb_to_display(total_total_mb)[0]} {_mb_to_display(total_total_mb)[1]}",
                "可用": f"{_mb_to_display(total_remain_mb)[0]} {_mb_to_display(total_remain_mb)[1]}",
                "超出": f"{_mb_to_display(total_exceed_mb)[0]} {_mb_to_display(total_exceed_mb)[1]}",
                "使用比例": f"{ratio}%",
                "套餐数": len(data_items),
            }
        return {}


class UnicomBalanceSensor(UnicomBaseSensor):
    """余额传感器."""

    def __init__(self, coordinator: UnicomBillCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_balance"
        self._attr_name = "账户余额"
        self._attr_native_unit_of_measurement = "元"

    @property
    def native_value(self) -> float | None:
        """Return the state."""
        if not self.coordinator.data:
            return None
        balance = self.coordinator.data.get("balance_detail", {})
        if balance:
            try:
                return float(balance.get("canusefeecustNew", balance.get("canusefeecust", 0)))
            except (ValueError, TypeError):
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}
        balance = self.coordinator.data.get("balance_detail", {})
        return {
            "当前余额": balance.get("curntbalancecust"),
            "实时话费": balance.get("totalrealfee", balance.get("realfeecustnew")),
            "总欠费": balance.get("allbowefeecust"),
            "信用额度": balance.get("canuselimitcust"),
        }


# ==================== 详细传感器（可选）====================

class UnicomVoiceTotalSensor(UnicomBaseSensor):
    """语音总量传感器."""

    def __init__(self, coordinator: UnicomBillCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_voice_total"
        self._attr_name = "语音总量"
        self._attr_native_unit_of_measurement = "分钟"

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        usage = self.coordinator.data.get("usage_details", {}).get("voice")
        if usage:
            try:
                return float(usage.get("total", 0))
            except (ValueError, TypeError):
                return None
        return None


class UnicomVoiceAvailableSensor(UnicomBaseSensor):
    """语音可用传感器."""

    def __init__(self, coordinator: UnicomBillCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_voice_available"
        self._attr_name = "语音可用"
        self._attr_native_unit_of_measurement = "分钟"

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        usage = self.coordinator.data.get("usage_details", {}).get("voice")
        if usage:
            try:
                return float(usage.get("remain", 0))
            except (ValueError, TypeError):
                return None
        return None


class UnicomVoiceRatioSensor(UnicomBaseSensor):
    """语音使用比例传感器."""

    def __init__(self, coordinator: UnicomBillCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_voice_ratio"
        self._attr_name = "语音使用比例"
        self._attr_native_unit_of_measurement = "%"

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        usage = self.coordinator.data.get("usage_details", {}).get("voice")
        if usage:
            try:
                return round(float(usage.get("usedPercent", 0)), 2)
            except (ValueError, TypeError):
                return None
        return None


class UnicomSmsTotalSensor(UnicomBaseSensor):
    """短信总量传感器."""

    def __init__(self, coordinator: UnicomBillCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_sms_total"
        self._attr_name = "短信总量"
        self._attr_native_unit_of_measurement = "条"

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        usage = self.coordinator.data.get("usage_details", {}).get("sms")
        if usage:
            try:
                return float(usage.get("total", 0))
            except (ValueError, TypeError):
                return None
        return None


class UnicomSmsAvailableSensor(UnicomBaseSensor):
    """短信可用传感器."""

    def __init__(self, coordinator: UnicomBillCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_sms_available"
        self._attr_name = "短信可用"
        self._attr_native_unit_of_measurement = "条"

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        usage = self.coordinator.data.get("usage_details", {}).get("sms")
        if usage:
            try:
                return float(usage.get("remain", 0))
            except (ValueError, TypeError):
                return None
        return None


class UnicomDataTotalSensor(UnicomBaseSensor):
    """流量总量传感器."""

    def __init__(self, coordinator: UnicomBillCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_data_total"
        self._attr_name = "流量总量"

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        usage = self.coordinator.data.get("usage_details", {})
        data_items = usage.get("data_items", [])
        if data_items:
            total_mb = sum(_parse_mb(item.get("total")) for item in data_items)
            value, unit = _mb_to_display(total_mb)
            self._attr_native_unit_of_measurement = unit
            return value
        return None


class UnicomDataAvailableSensor(UnicomBaseSensor):
    """流量可用传感器."""

    def __init__(self, coordinator: UnicomBillCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_data_available"
        self._attr_name = "流量可用"

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        usage = self.coordinator.data.get("usage_details", {})
        data_items = usage.get("data_items", [])
        if data_items:
            total_mb = sum(
                _parse_mb(item.get("remain"))
                for item in data_items
                if item.get("remain")
            )
            value, unit = _mb_to_display(total_mb)
            self._attr_native_unit_of_measurement = unit
            return value
        return None


class UnicomDataExceedSensor(UnicomBaseSensor):
    """流量超出传感器."""

    def __init__(self, coordinator: UnicomBillCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_data_exceed"
        self._attr_name = "流量超出"

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        usage = self.coordinator.data.get("usage_details", {})
        data_items = usage.get("data_items", [])
        if data_items:
            total_mb = sum(
                _parse_mb(item.get("xexceedvalue"))
                for item in data_items
                if item.get("xexceedvalue")
            )
            value, unit = _mb_to_display(total_mb)
            self._attr_native_unit_of_measurement = unit
            return value
        return None


class UnicomDataRatioSensor(UnicomBaseSensor):
    """流量使用比例传感器."""

    def __init__(self, coordinator: UnicomBillCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_data_ratio"
        self._attr_name = "流量使用比例"
        self._attr_native_unit_of_measurement = "%"

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        usage = self.coordinator.data.get("usage_details", {})
        data_items = usage.get("data_items", [])
        if data_items:
            total_use = sum(_parse_mb(item.get("use")) for item in data_items)
            total_total = sum(_parse_mb(item.get("total")) for item in data_items)
            if total_total > 0:
                return round(total_use / total_total * 100, 2)
        return None


class UnicomRealFeeSensor(UnicomBaseSensor):
    """实时话费传感器."""

    def __init__(self, coordinator: UnicomBillCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_real_fee"
        self._attr_name = "实时话费"
        self._attr_native_unit_of_measurement = "元"

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        balance = self.coordinator.data.get("balance_detail", {})
        if balance:
            try:
                return float(
                    balance.get("totalrealfee", balance.get("realfeecustnew", 0))
                )
            except (ValueError, TypeError):
                return None
        return None


class UnicomCanUseValueSensor(UnicomBaseSensor):
    """可用赠款传感器."""

    def __init__(self, coordinator: UnicomBillCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_can_use_value"
        self._attr_name = "可用赠款"
        self._attr_native_unit_of_measurement = "元"

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        balance = self.coordinator.data.get("balance_detail", {})
        if balance:
            try:
                return float(balance.get("curntbalancecust", 0))
            except (ValueError, TypeError):
                return None
        return None

