"""API client for China Unicom Bill."""
from __future__ import annotations

import json
import logging
import time
from typing import Any

import aiohttp
from aiohttp import ClientSession

from .const import (
    API_BALANCE_DETAIL,
    API_GET_TICKET,
    API_QUERY_GOODS_LIST,
    API_SERVICE_ENTRANCE,
    API_SSPBIGBALL,
    API_USAGE_DETAIL,
    HEADERS_FORM,
    HEADERS_JSON,
)

_LOGGER = logging.getLogger(__name__)


def _safe_float(value: str | float | None) -> float:
    """Safely convert a value to float, returning 0.0 on failure."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


class UnicomAPIError(Exception):
    """Base exception for Unicom API errors."""

    pass


class UnicomAuthError(UnicomAPIError):
    """Authentication error."""

    pass


class UnicomRateLimitError(UnicomAPIError):
    """Rate limit error."""

    pass


class UnicomAPI:
    """China Unicom API client."""

    def __init__(
        self,
        session: ClientSession,
        openid: str,
        usage_ticket: str = "",
        usage_ticket_phone: str = "",
        balance_ticket: str = "",
        balance_ticket_phone: str = "",
        micro_hall_user: str = "",
        micro_hall_access_token: str = "",
    ) -> None:
        """Initialize the API client."""
        self.session = session
        self.openid = openid
        
        # Manual credentials (optional)
        self._manual_usage_ticket = usage_ticket
        self._manual_usage_ticket_phone = usage_ticket_phone
        self._manual_balance_ticket = balance_ticket
        self._manual_balance_ticket_phone = balance_ticket_phone
        self._manual_micro_hall_user = micro_hall_user
        self._manual_micro_hall_access_token = micro_hall_access_token
        
        # Auto-fetched credentials
        self._auto_ticket = ""
        self._auto_ticket_phone = ""
        self._micro_hall_user = micro_hall_user
        self._micro_hall_access_token = micro_hall_access_token

    def _build_cookie_header(self) -> str:
        """Build Cookie header for mxx.client.10010.com."""
        cookies = []
        if self._micro_hall_user:
            cookies.append(f"microHallUser={self._micro_hall_user}")
        if self._micro_hall_access_token:
            cookies.append(f"microHallAccessToken={self._micro_hall_access_token}")
        return "; ".join(cookies)

    async def _auto_get_auth(self) -> None:
        """Auto-fetch authentication credentials."""
        try:
            # Step 1: Get ticket
            ticket_payload = {"openId": self.openid, "channel": "wxmini"}
            async with self.session.post(
                API_GET_TICKET, json=ticket_payload, headers=HEADERS_JSON
            ) as resp:
                text = await resp.text()
                ticket_json = json.loads(text)
                
                if ticket_json.get("code") != "0000":
                    _LOGGER.warning("getTicket failed: code=%s", ticket_json.get("code"))
                    return
                    
                ticket = ticket_json.get("data", "")
                self._auto_ticket = ticket
                self._auto_ticket_phone = f"wx{int(time.time() * 1000)}"
                _LOGGER.debug("getTicket success: %s...", ticket[:20])

            # Step 2: Get microHall Cookie via serviceEntrance
            try:
                entrance_url = (
                    f"{API_SERVICE_ENTRANCE}"
                    f"?ticket={ticket}"
                    f"&servicecode=YH10007"
                    f"&ticketChannel=XCXSYHF"
                )
                async with self.session.get(entrance_url) as entrance_resp:
                    for cookie_str in entrance_resp.headers.getall("Set-Cookie", []):
                        if "microHallUser=" in cookie_str:
                            self._micro_hall_user = (
                                cookie_str.split("microHallUser=", 1)[1]
                                .split(";")[0]
                                .strip()
                            )
                        if "microHallAccessToken=" in cookie_str:
                            self._micro_hall_access_token = (
                                cookie_str.split("microHallAccessToken=", 1)[1]
                                .split(";")[0]
                                .strip()
                            )
                            
                    if self._micro_hall_user:
                        _LOGGER.debug("serviceEntrance success, got microHall Cookie")
                    else:
                        _LOGGER.info("serviceEntrance returned no Cookie")
                        
            except Exception as err:
                _LOGGER.info("serviceEntrance failed (%s): %s", type(err).__name__, err)

        except Exception as err:
            _LOGGER.info("Auto-auth failed (%s): %s", type(err).__name__, err)

    async def get_overview(self) -> dict[str, Any]:
        """Get overview data from sspbigball API."""
        try:
            payload = {"openid": self.openid, "channel": "wxmini"}
            async with self.session.post(
                API_SSPBIGBALL, json=payload, headers=HEADERS_JSON
            ) as resp:
                text = await resp.text()
                data = json.loads(text)
                
                if data.get("code") == "0000":
                    return data.get("data", {})
                else:
                    _LOGGER.warning("sspbigball error: %s", data)
                    return {}
                    
        except Exception as err:
            _LOGGER.error("Failed to get overview: %s", err)
            raise UnicomAPIError(f"Overview API error: {err}") from err

    async def get_phone_number(self) -> str | None:
        """Extract complete phone number from API response.
        
        Tries queryGoodsList API first (returns complete number),
        falls back to usage detail API if needed.
        """
        # Method 1: Try queryGoodsList API (returns complete phone number)
        try:
            payload = {"openid": self.openid, "channel": "wxmini"}
            async with self.session.post(
                API_QUERY_GOODS_LIST, json=payload, headers=HEADERS_JSON
            ) as resp:
                text = await resp.text()
                data = json.loads(text)
                
                if data.get("code") == "0000" and data.get("data", {}).get("res"):
                    res_list = data["data"]["res"]
                    for item in res_list:
                        main_number = item.get("mainNumber", "")
                        if main_number and len(main_number) == 11 and main_number.startswith("1"):
                            _LOGGER.info("Found complete phone number from queryGoodsList: %s", main_number)
                            return main_number
        except Exception as err:
            _LOGGER.warning("queryGoodsList API failed: %s", err)
        
        # Method 2: Fallback to usage detail API (may return masked number)
        try:
            effective_ticket = self._manual_usage_ticket or self._auto_ticket
            effective_phone = self._manual_usage_ticket_phone or self._auto_ticket_phone
            
            form_data = {
                "duanlianjieabc": "",
                "channelCode": "",
                "serviceType": "",
                "saleChannel": "",
                "externalSources": "",
                "contactCode": "",
                "ticket": effective_ticket,
                "ticketPhone": effective_phone,
                "ticketChannel": "XCXYLCXYY",
                "language": "chinese",
            }
            
            headers = HEADERS_FORM.copy()
            cookie_header = self._build_cookie_header()
            if cookie_header:
                headers["Cookie"] = cookie_header

            async with self.session.post(
                API_USAGE_DETAIL, data=form_data, headers=headers
            ) as resp:
                text = await resp.text()
                data = json.loads(text)
                
                # Try to extract phone number from viceCardlist
                if data.get("shareData") and data["shareData"].get("details"):
                    for item in data["shareData"]["details"]:
                        vice_list = item.get("viceCardlist", [])
                        if vice_list and len(vice_list) > 0:
                            user_number = vice_list[0].get("usernumber", "")
                            if user_number and len(user_number) >= 7:
                                _LOGGER.info("Found phone number from usage detail API: %s", user_number)
                                return user_number
                
                return None
                    
        except Exception as err:
            _LOGGER.error("Failed to get phone number from usage detail API: %s", err)
            return None

    async def get_balance_detail(self) -> dict[str, Any]:
        """Get balance detail from accountBalancenew API."""
        try:
            effective_ticket = self._manual_balance_ticket or self._auto_ticket
            effective_phone = self._manual_balance_ticket_phone or self._auto_ticket_phone
            
            form_data = {
                "duanlianjieabc": "",
                "channelCode": "",
                "serviceType": "",
                "saleChannel": "",
                "externalSources": "",
                "contactCode": "",
                "ticket": effective_ticket,
                "ticketPhone": effective_phone,
                "ticketChannel": "XCXSYHF",
                "language": "chinese",
                "channel": "client",
            }
            
            headers = HEADERS_FORM.copy()
            cookie_header = self._build_cookie_header()
            if cookie_header:
                headers["Cookie"] = cookie_header

            async with self.session.post(
                API_BALANCE_DETAIL, data=form_data, headers=headers
            ) as resp:
                text = await resp.text()
                data = json.loads(text)
                
                if data.get("code") == "0000":
                    _LOGGER.debug("Balance detail fetched successfully")
                    return data.get("data", data)
                else:
                    _LOGGER.info(
                        "Balance detail error code=%s: %s",
                        data.get("code"),
                        data.get("msg", ""),
                    )
                    return {}
                    
        except Exception as err:
            _LOGGER.error("Failed to get balance detail: %s", err)
            raise UnicomAPIError(f"Balance API error: {err}") from err

    async def get_usage_detail(self) -> dict[str, Any]:
        """Get usage detail from queryOcsPackageFlow API."""
        try:
            effective_ticket = self._manual_usage_ticket or self._auto_ticket
            effective_phone = self._manual_usage_ticket_phone or self._auto_ticket_phone
            
            form_data = {
                "duanlianjieabc": "",
                "channelCode": "",
                "serviceType": "",
                "saleChannel": "",
                "externalSources": "",
                "contactCode": "",
                "ticket": effective_ticket,
                "ticketPhone": effective_phone,
                "ticketChannel": "XCXYLCXYY",
                "language": "chinese",
            }
            
            headers = HEADERS_FORM.copy()
            cookie_header = self._build_cookie_header()
            if cookie_header:
                headers["Cookie"] = cookie_header

            async with self.session.post(
                API_USAGE_DETAIL, data=form_data, headers=headers
            ) as resp:
                text = await resp.text()
                data = json.loads(text)
                
                parsed: dict[str, Any] = {"data_items": []}

                # Parse data items (elemType=3) from unshared (NEW: primary source)
                if data.get("unshared") and isinstance(data["unshared"], list):
                    for group in data["unshared"]:
                        if not isinstance(group, dict):
                            continue
                        
                        details = group.get("details", [])
                        if not isinstance(details, list):
                            continue
                        
                        group_type = group.get("type", "")
                        
                        for item in details:
                            if not isinstance(item, dict):
                                continue
                            
                            elem_type = item.get("elemType")
                            if elem_type == "3":  # Data
                                parsed["data_items"].append({
                                    "addUpItemName": item.get("addUpItemName"),
                                    "use": item.get("use"),
                                    "total": item.get("total"),
                                    "remain": item.get("remain"),
                                    "xexceedvalue": item.get("xexceedvalue"),
                                    "usedPercent": item.get("usedPercent"),
                                    "endDate": item.get("endDate"),
                                    "beforeTotal": item.get("beforeTotal"),
                                    "beforeRemain": item.get("beforeRemain"),
                                    "beforeUse": item.get("beforeUse"),
                                    "flowType": item.get("flowType"),
                                })
                
                # Fallback: Parse data items from shareData
                if not parsed["data_items"] and data.get("shareData") and data["shareData"].get("details"):
                    share_data = data["shareData"]
                    details = share_data.get("details", [])
                    
                    if isinstance(details, list):
                        for item in details:
                            # Skip if item is not a dict
                            if not isinstance(item, dict):
                                _LOGGER.debug("Skipping non-dict shareData item: %s", type(item).__name__)
                                continue
                            
                            if item.get("elemType") == "3":
                                parsed["data_items"].append({
                                    "addUpItemName": item.get("addUpItemName"),
                                    "use": item.get("use"),
                                    "total": item.get("total"),
                                    "remain": item.get("remain"),
                                    "xexceedvalue": item.get("xexceedvalue"),
                                    "usedPercent": item.get("usedPercent"),
                                    "endDate": item.get("endDate"),
                                    "beforeTotal": item.get("beforeTotal"),
                                    "beforeRemain": item.get("beforeRemain"),
                                    "beforeUse": item.get("beforeUse"),
                                    "flowType": item.get("flowType"),
                                })
                
                # Fallback: Try to parse data from resources if still no data items
                if not parsed["data_items"] and data.get("resources"):
                    _LOGGER.debug("Trying fallback: parsing data from resources")
                    resources = data.get("resources", [])
                    if isinstance(resources, list):
                        for group in resources:
                            if not isinstance(group, dict):
                                continue
                            
                            details = group.get("details", [])
                            if not isinstance(details, list):
                                continue
                            
                            for item in details:
                                if not isinstance(item, dict):
                                    continue
                                
                                # elemType=3 might also be in resources for some users
                                if item.get("elemType") == "3":
                                    parsed["data_items"].append({
                                        "addUpItemName": item.get("addUpItemName"),
                                        "use": item.get("use"),
                                        "total": item.get("total"),
                                        "remain": item.get("remain"),
                                        "xexceedvalue": item.get("xexceedvalue"),
                                        "usedPercent": item.get("usedPercent"),
                                        "endDate": item.get("endDate"),
                                        "beforeTotal": item.get("beforeTotal"),
                                        "beforeRemain": item.get("beforeRemain"),
                                        "beforeUse": item.get("beforeUse"),
                                        "flowType": item.get("flowType"),
                                    })

                # Parse voice and SMS from unshared (NEW: primary source) and resources
                # Strategy: accumulate from details items first,
                # then fall back to resource-group level (userResource/remainResource),
                # finally use top-level aggregate fields.
                voice_items = []
                sms_items = []
                voice_group_remain = None
                voice_group_use = None
                sms_group_remain = None
                sms_group_use = None

                # NEW: Parse from unshared first
                if data.get("unshared") and isinstance(data["unshared"], list):
                    for group in data["unshared"]:
                        if not isinstance(group, dict):
                            continue
                        
                        details = group.get("details", [])
                        if not isinstance(details, list):
                            continue
                        
                        # Capture group-level aggregates
                        group_type = group.get("type", "")
                        if group_type == "unsharedVoiceList":
                            try:
                                voice_group_use = float(group.get("userResource", 0))
                                voice_group_remain = float(group.get("remainResource", 0))
                            except (ValueError, TypeError):
                                pass
                        elif group_type == "unsharedSmsList":
                            try:
                                sms_group_use = float(group.get("userResource", 0))
                                sms_group_remain = float(group.get("remainResource", 0))
                            except (ValueError, TypeError):
                                pass
                        
                        # Parse individual items
                        for item in details:
                            if not isinstance(item, dict):
                                continue
                            
                            elem_type = item.get("elemType")
                            if elem_type == "1":  # Voice
                                voice_items.append(item)
                            elif elem_type == "2":  # SMS
                                sms_items.append(item)

                # Fallback: Parse from resources
                resources = data.get("resources", [])
                if isinstance(resources, list):
                    for group in resources:
                        # Skip if group is not a dict (some devices return int or other types)
                        if not isinstance(group, dict):
                            _LOGGER.debug("Skipping non-dict resource group: %s", type(group).__name__)
                            continue

                        gtype = group.get("type", "")
                        # Capture group-level aggregates for fallback
                        if gtype == "Voice":
                            try:
                                voice_group_use = float(group.get("userResource", 0))
                                voice_group_remain = float(group.get("remainResource", 0))
                            except (ValueError, TypeError):
                                pass
                        elif gtype == "smsList":
                            try:
                                sms_group_use = float(group.get("userResource", 0))
                                sms_group_remain = float(group.get("remainResource", 0))
                            except (ValueError, TypeError):
                                pass

                        details = group.get("details", [])
                        if not isinstance(details, list):
                            _LOGGER.debug("Skipping non-list details: %s", type(details).__name__)
                            continue

                        for item in details:
                            if not isinstance(item, dict):
                                _LOGGER.debug("Skipping non-dict item: %s", type(item).__name__)
                                continue

                            elem_type = item.get("elemType")
                            if elem_type == "1":  # Voice
                                voice_items.append(item)
                            elif elem_type == "2":  # SMS
                                sms_items.append(item)

                # --- Build voice result ---
                if voice_items:
                    total_use = sum(_safe_float(i.get("use")) for i in voice_items)
                    total_total = sum(_safe_float(i.get("total")) for i in voice_items)
                    total_remain = sum(_safe_float(i.get("remain")) for i in voice_items)
                    used_pct = round(total_use / total_total * 100) if total_total > 0 else 0
                    parsed["voice"] = {
                        "use": str(int(total_use)) if total_use == int(total_use) else str(total_use),
                        "total": str(int(total_total)) if total_total == int(total_total) else str(total_total),
                        "remain": str(int(total_remain)) if total_remain == int(total_remain) else str(total_remain),
                        "usedPercent": str(used_pct),
                    }
                elif voice_group_use is not None:
                    # Fallback: use resource-group level aggregates
                    parsed["voice"] = {
                        "use": str(int(voice_group_use)) if voice_group_use == int(voice_group_use) else str(voice_group_use),
                        "total": str(int(voice_group_use + voice_group_remain)) if (voice_group_use + voice_group_remain) == int(voice_group_use + voice_group_remain) else str(voice_group_use + voice_group_remain),
                        "remain": str(int(voice_group_remain)) if voice_group_remain == int(voice_group_remain) else str(voice_group_remain),
                        "usedPercent": str(round(voice_group_use / (voice_group_use + voice_group_remain) * 100)) if (voice_group_use + voice_group_remain) > 0 else "0",
                    }

                # --- Build SMS result ---
                if sms_items:
                    total_use = sum(_safe_float(i.get("use")) for i in sms_items)
                    total_total = sum(_safe_float(i.get("total")) for i in sms_items)
                    total_remain = sum(_safe_float(i.get("remain")) for i in sms_items)
                    used_pct = round(total_use / total_total * 100) if total_total > 0 else 0
                    parsed["sms"] = {
                        "use": str(int(total_use)) if total_use == int(total_use) else str(total_use),
                        "total": str(int(total_total)) if total_total == int(total_total) else str(total_total),
                        "remain": str(int(total_remain)) if total_remain == int(total_remain) else str(total_remain),
                        "usedPercent": str(used_pct),
                    }
                elif sms_group_use is not None:
                    # Fallback: use resource-group level aggregates
                    parsed["sms"] = {
                        "use": str(int(sms_group_use)) if sms_group_use == int(sms_group_use) else str(sms_group_use),
                        "total": str(int(sms_group_use + sms_group_remain)) if (sms_group_use + sms_group_remain) == int(sms_group_use + sms_group_remain) else str(sms_group_use + sms_group_remain),
                        "remain": str(int(sms_group_remain)) if sms_group_remain == int(sms_group_remain) else str(sms_group_remain),
                        "usedPercent": "0",
                    }

                has_data = (
                    bool(parsed.get("data_items"))
                    or bool(parsed.get("voice"))
                    or bool(parsed.get("sms"))
                )
                
                if has_data:
                    _LOGGER.debug(
                        "Usage detail fetched: voice=%s, sms=%s, data=%d items (from unshared=%s, shareData=%s, resources=%s)",
                        bool(parsed.get("voice")),
                        bool(parsed.get("sms")),
                        len(parsed.get("data_items", [])),
                        bool(data.get("unshared")),
                        bool(data.get("shareData")),
                        bool(data.get("resources"))
                    )
                    return parsed
                else:
                    _LOGGER.info("Usage detail returned no valid data")
                    return {}
                    
        except Exception as err:
            _LOGGER.error("Failed to get usage detail: %s", err)
            raise UnicomAPIError(f"Usage API error: {err}") from err

    async def fetch_all_data(self) -> dict[str, Any]:
        """Fetch all data from Unicom APIs."""
        result: dict[str, Any] = {
            "overview": {},
            "usage_details": {},
            "balance_detail": {},
        }

        try:
            # Step 0: Auto-fetch authentication
            await self._auto_get_auth()

            # Step 1: Get overview
            overview = await self.get_overview()
            if overview:
                result["overview"] = overview

            # Step 2: Get balance detail
            balance = await self.get_balance_detail()
            if balance:
                result["balance_detail"] = balance

            # Step 3: Get usage detail
            usage = await self.get_usage_detail()
            if usage:
                result["usage_details"] = usage

            return result

        except Exception as err:
            _LOGGER.error("Failed to fetch all data: %s", err)
            raise UnicomAPIError(f"Data fetch error: {err}") from err
