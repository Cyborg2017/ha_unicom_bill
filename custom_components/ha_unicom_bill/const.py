"""Constants for the China Unicom Bill integration."""
from homeassistant.const import Platform

DOMAIN = "ha_unicom_bill"
NAME = "China Unicom Bill"

# Platform configuration
PLATFORMS = [Platform.SENSOR]

# Configuration keys
CONF_OPENID = "openid"
CONF_PHONE_NUMBER = "phone_number"
CONF_REFRESH_INTERVAL = "refresh_interval"
CONF_CREATE_INDIVIDUAL_SENSORS = "create_individual_sensors"

# Optional authentication keys (auto-fetched if not provided)
CONF_USAGE_TICKET = "usage_ticket"
CONF_USAGE_TICKET_PHONE = "usage_ticket_phone"
CONF_BALANCE_TICKET = "balance_ticket"
CONF_BALANCE_TICKET_PHONE = "balance_ticket_phone"
CONF_MICRO_HALL_USER = "micro_hall_user"
CONF_MICRO_HALL_ACCESS_TOKEN = "micro_hall_access_token"

# Default values
DEFAULT_NAME = "Bill Query Integration"
DEFAULT_REFRESH_INTERVAL = 15  # minutes
DEFAULT_CREATE_INDIVIDUAL_SENSORS = False

# API Endpoints
API_SSPBIGBALL = "https://mina.10010.com/wxapplet/weixinNew/sspbigball"
API_USAGE_DETAIL = (
    "https://mxx.client.10010.com/servicequerybusiness"
    "/operationservice/queryOcsPackageFlowLeftContentRevisedInJune"
)
API_BALANCE_DETAIL = (
    "https://mxx.client.10010.com/servicequerybusiness"
    "/balancenew/accountBalancenew.htm"
)
API_BILL_DETAIL = (
    "https://m.client.10010.com/serviceimportantbusiness"
    "/phoneBillNew/queryDetail"
)
API_GET_TICKET = "https://mina.10010.com/wxapplet/weixinNew/getTicket"
API_SERVICE_ENTRANCE = "https://mxx.client.10010.com/servicebusiness/wx/serviceEntrance"
API_QUERY_GOODS_LIST = "https://mina.10010.com/wxapplet/weixinNew/queryGoodsList"

# Request headers
HEADERS_JSON = {"Content-Type": "application/json"}
HEADERS_FORM = {"Content-Type": "application/x-www-form-urlencoded"}

# User agent for WeChat Mini Program
WX_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 "
    "MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI "
    "MiniProgramEnv/Windows WindowsWechat/WMPF"
)
