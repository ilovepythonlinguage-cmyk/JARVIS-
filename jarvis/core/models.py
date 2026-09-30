from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class Intent(str, Enum):
    OPEN_APPLICATION = "open_application"
    OPEN_WEBSITE = "open_website"
    OPEN_FOLDER = "open_folder"
    WEB_SEARCH = "web_search"
    YOUTUBE_SEARCH = "youtube_search"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    SET_VOLUME = "set_volume"
    MUTE = "mute"
    UNMUTE = "unmute"
    MEDIA_PLAY_PAUSE = "media_play_pause"
    MEDIA_NEXT = "media_next"
    MEDIA_PREVIOUS = "media_previous"
    MEDIA_STOP = "media_stop"
    GET_TIME = "get_time"
    GET_DATE = "get_date"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    DISK_USAGE = "disk_usage"
    LOCK = "lock"
    SHUTDOWN = "shutdown"
    REBOOT = "reboot"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class Command:
    intent: Intent
    slots: dict[str, Any] = field(default_factory=dict)
    original_text: str = ""
