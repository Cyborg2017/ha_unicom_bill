"""Constants for the 中国联通话费查询 (China Unicom Bill) integration."""
from homeassistant.const import Platform

DOMAIN = "ha_unicom_bill"
NAME = "中国联通话费查询"

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
DEFAULT_NAME = "话费查询集成"
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
API_GET_TICKET = "https://mina.10010.com/wxapplet/weixinNew/getTicket"
API_SERVICE_ENTRANCE = "https://mxx.client.10010.com/servicebusiness/wx/serviceEntrance"

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

# Sensor types
SENSOR_VOICE_USAGE = "voice_usage"
SENSOR_VOICE_TOTAL = "voice_total"
SENSOR_VOICE_AVAILABLE = "voice_available"
SENSOR_VOICE_RATIO = "voice_ratio"

SENSOR_SMS_USAGE = "sms_usage"
SENSOR_SMS_TOTAL = "sms_total"
SENSOR_SMS_AVAILABLE = "sms_available"

SENSOR_DATA_USAGE = "data_usage"
SENSOR_DATA_TOTAL = "data_total"
SENSOR_DATA_AVAILABLE = "data_available"
SENSOR_DATA_EXCEED = "data_exceed"
SENSOR_DATA_RATIO = "data_ratio"

SENSOR_REAL_FEE = "real_fee"
SENSOR_CAN_USE_VALUE = "can_use_value"

# All available sensors
ALL_SENSORS = {
    SENSOR_VOICE_USAGE: {"name": "已用语音", "unit": "分钟"},
    SENSOR_VOICE_TOTAL: {"name": "语音总量", "unit": "分钟"},
    SENSOR_VOICE_AVAILABLE: {"name": "剩余语音", "unit": "分钟"},
    SENSOR_VOICE_RATIO: {"name": "语音使用比例", "unit": "%"},
    SENSOR_SMS_USAGE: {"name": "已用短信", "unit": "条"},
    SENSOR_SMS_TOTAL: {"name": "短信总量", "unit": "条"},
    SENSOR_SMS_AVAILABLE: {"name": "剩余短信", "unit": "条"},
    SENSOR_DATA_USAGE: {"name": "已用流量", "unit": "GB"},
    SENSOR_DATA_TOTAL: {"name": "流量总量", "unit": "GB"},
    SENSOR_DATA_AVAILABLE: {"name": "剩余流量", "unit": "GB"},
    SENSOR_DATA_EXCEED: {"name": "超支流量", "unit": "MB"},
    SENSOR_DATA_RATIO: {"name": "流量使用比例", "unit": "%"},
    SENSOR_REAL_FEE: {"name": "本月话费", "unit": "元"},
    SENSOR_CAN_USE_VALUE: {"name": "上月结余话费", "unit": "元"},
}
