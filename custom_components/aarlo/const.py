"""Constants for the Aarlo component."""

from datetime import timedelta

COMPONENT_DOMAIN = "aarlo"
COMPONENT_DATA = "aarlo-data"
COMPONENT_SERVICES = "aarlo-services"
COMPONENT_CONFIG = "aarlo-config"
COMPONENT_ATTRIBUTION = "Data provided by my.arlo.com"
COMPONENT_BRAND = "Arlo"

NOTIFICATION_ID = "aarlo_notification"
NOTIFICATION_TITLE = "aarlo Component Setup"

# All config.
CONF_PACKET_DUMP = "packet_dump"
CONF_CACHE_VIDEOS = "cache_videos"
CONF_DB_MOTION_TIME = "db_motion_time"
CONF_DB_DING_TIME = "db_ding_time"
CONF_RECENT_TIME = "recent_time"
CONF_LAST_FORMAT = "last_format"
CONF_CONF_DIR = "conf_dir"
CONF_REQ_TIMEOUT = "request_timeout"
CONF_STR_TIMEOUT = "stream_timeout"
CONF_NO_MEDIA_UP = "no_media_upload"
CONF_MEDIA_RETRY = "media_retry"
CONF_SNAPSHOT_CHECKS = "snapshot_checks"
CONF_USER_AGENT = "user_agent"
CONF_MODE_API = "mode_api"
CONF_DEVICE_REFRESH = "refresh_devices_every"
CONF_MODE_REFRESH = "refresh_modes_every"
CONF_RECONNECT_EVERY = "reconnect_every"
CONF_VERBOSE_DEBUG = "verbose_debug"
CONF_INJECTION_SERVICE = "injection_service"
CONF_SNAPSHOT_TIMEOUT = "snapshot_timeout"
CONF_TFA_SOURCE = "tfa_source"
CONF_TFA_TYPE = "tfa_type"
CONF_TFA_HOST = "tfa_host"
CONF_TFA_USERNAME = "tfa_username"
CONF_TFA_PASSWORD = "tfa_password"
CONF_TFA_TIMEOUT = "tfa_timeout"
CONF_TFA_TOTAL_TIMEOUT = "tfa_total_timeout"
CONF_LIBRARY_DAYS = "library_days"
CONF_AUTH_HOST = "auth_host"
CONF_SERIAL_IDS = "serial_ids"
CONF_STREAM_SNAPSHOT = "stream_snapshot"
CONF_STREAM_SNAPSHOT_STOP = "stream_snapshot_stop"
CONF_SAVE_UPDATES_TO = "save_updates_to"
CONF_USER_STREAM_DELAY = "user_stream_delay"
CONF_SAVE_MEDIA_TO = "save_media_to"
CONF_NO_UNICODE_SQUASH = "no_unicode_squash"
CONF_SAVE_SESSION = "save_session"
CONF_BACKEND = "backend"
CONF_CIPHER_LIST = "cipher_list"
CONF_MQTT_HOST = "mqtt_host"
CONF_MQTT_HOSTNAME_CHECK = "mqtt_hostname_check"
CONF_MQTT_TRANSPORT = "mqtt_transport"

# All defaults

# Alarm Specifics
STATE_ALARM_ARLO_ARMED = "armed"
STATE_ALARM_ARLO_HOME = "home"
STATE_ALARM_ARLO_NIGHT = "night"

ALARM_ICON = "mdi:security"

CONF_CODE_ARM_REQUIRED = "code_arm_required"
CONF_CODE_DISARM_REQUIRED = "code_disarm_required"
CONF_DISARMED_MODE_NAME = "disarmed_mode_name"
CONF_HOME_MODE_NAME = "home_mode_name"
CONF_AWAY_MODE_NAME = "away_mode_name"
CONF_NIGHT_MODE_NAME = "night_mode_name"
CONF_ALARM_VOLUME = "alarm_volume"
CONF_COMMAND_TEMPLATE = "command_template"

DEFAULT_COMMAND_TEMPLATE = "{{action}}"
DEFAULT_TRIGGER_TIME = timedelta(seconds=60)
DEFAULT_ALARM_VOLUME = 8

SCAN_INTERVAL = timedelta(seconds=60)
PACKET_DUMP = False
CACHE_VIDEOS = False
DB_MOTION_TIME = timedelta(seconds=30)
DB_DING_TIME = timedelta(seconds=10)
RECENT_TIME = timedelta(minutes=60)
LAST_FORMAT = "%m-%d %H:%M"
CONF_DIR = ""
REQ_TIMEOUT = timedelta(seconds=15)
STR_TIMEOUT = timedelta(seconds=120)
NO_MEDIA_UP = False
MEDIA_RETRY = [5, 15, 25]
SNAPSHOT_CHECKS = None
USER_AGENT = "arlo"
MODE_API = "auto"
DEVICE_REFRESH = 2
MODE_REFRESH = 0
RECONNECT_EVERY = 0
VERBOSE_DEBUG = False
DEFAULT_INJECTION_SERVICE = False
SNAPSHOT_TIMEOUT = timedelta(seconds=45)
DEFAULT_TFA_SOURCE = "imap"
DEFAULT_TFA_TYPE = "email"
DEFAULT_TFA_HOST = "unknown.imap.com"
DEFAULT_TFA_USERNAME = "unknown@unknown.com"
DEFAULT_TFA_PASSWORD = "unknown"
DEFAULT_TFA_TIMEOUT = timedelta(seconds=3)
DEFAULT_TFA_TOTAL_TIMEOUT = timedelta(seconds=60)
DEFAULT_LIBRARY_DAYS = 27
SERIAL_IDS = False
STREAM_SNAPSHOT = False
STREAM_SNAPSHOT_STOP = 0
SAVE_UPDATES_TO = ""
USER_STREAM_DELAY = 1
SAVE_MEDIA_TO = ""
NO_UNICODE_SQUASH = True
SAVE_SESSION = True
DEFAULT_BACKEND = "auto"
DEFAULT_CIPHER_LIST = ""
DEFAULT_MQTT_HOSTNAME_CHECK = True
DEFAULT_MQTT_TRANSPORT = "tcp"
