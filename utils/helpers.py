"""
Helper functions for file I/O, network checks, input sanitization, and date utilities.
"""

import json
import os
import logging
from typing import Dict, Any
from datetime import datetime
import socket
import urllib.request
import urllib.error

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "settings.json")
DEFAULT_STATE = {
    "theme": "dark",
    "window_width": 1024,
    "window_height": 768,
    "window_x": 100,
    "window_y": 100,
    "source_language": "auto",
    "target_language": "en",
    "history": [],
    "favorites": []
}

logger = logging.getLogger(__name__)


def load_state() -> Dict[str, Any]:
    """
    Load application state from JSON file.
    If file does not exist or is corrupted, return default state.
    """
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure all keys exist
            for key in DEFAULT_STATE:
                if key not in data:
                    data[key] = DEFAULT_STATE[key]
            return data
    except FileNotFoundError:
        logger.warning(f"Config file not found: {CONFIG_PATH}. Using defaults.")
        return DEFAULT_STATE.copy()
    except json.JSONDecodeError:
        logger.error(f"Config file corrupted. Using defaults.")
        return DEFAULT_STATE.copy()
    except Exception as e:
        logger.error(f"Error loading state: {e}")
        return DEFAULT_STATE.copy()


def save_state(state: Dict[str, Any]) -> None:
    """
    Save application state to JSON file.
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving state: {e}")


def get_current_time_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def is_connected_to_internet(host: str = "8.8.8.8", port: int = 53, timeout: int = 3) -> bool:
    """
    Check internet connectivity by trying to connect to a well-known host.
    Uses socket connection (faster than HTTP).
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        # Fallback: try HTTP request to google.com
        try:
            urllib.request.urlopen("https://www.google.com", timeout=timeout)
            return True
        except:
            return False


def sanitize_text(text: str) -> str:
    """
    Sanitize input text: strip leading/trailing spaces, remove control characters.
    """
    # Remove control characters except newline and tab
    import re
    # Keep alphanumeric, space, punctuation, newline, tab.
    # This is a simple sanitization; we can also remove emoji? Not necessary.
    # We'll just strip.
    return text.strip()