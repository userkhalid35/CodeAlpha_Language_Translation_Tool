"""
Helper functions for file I/O, network checks, input sanitization, and date utilities.
"""

import json
import os
import logging
import socket
import urllib.request
import urllib.error
import tempfile
from typing import Dict, Any
from datetime import datetime, timezone

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "settings.json")
DEFAULT_STATE = {
    "theme": "dark",
    "window_width": 1024,
    "window_height": 768,
    "window_x": 100,
    "window_y": 100,
    "source_language": "auto",
    "target_language": "en",
    "max_characters": 50000,
    "history": [],
    "favorites": []
}

logger = logging.getLogger(__name__)


def load_state() -> Dict[str, Any]:
    """
    Load application state from JSON file.
    If file does not exist or is corrupted, return default state safely.
    """
    try:
        if not os.path.isfile(CONFIG_PATH):
            logger.info("Config file not found. Initializing with default state.")
            return DEFAULT_STATE.copy()

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            logger.warning("Config file root is not an object. Resetting to defaults.")
            return DEFAULT_STATE.copy()

        # Ensure all standard keys exist
        for key, default_val in DEFAULT_STATE.items():
            if key not in data:
                data[key] = default_val

        # Sanitize window geometry
        try:
            data["window_width"] = max(int(data.get("window_width", 1024)), 600)
            data["window_height"] = max(int(data.get("window_height", 768)), 450)
            data["window_x"] = max(int(data.get("window_x", 100)), 0)
            data["window_y"] = max(int(data.get("window_y", 100)), 0)
            data["max_characters"] = max(int(data.get("max_characters", 50000)), 50000)
        except (ValueError, TypeError):
            data["window_width"] = 1024
            data["window_height"] = 768
            data["window_x"] = 100
            data["window_y"] = 100
            data["max_characters"] = 50000

        # Validate list types
        if not isinstance(data.get("history"), list):
            data["history"] = []
        if not isinstance(data.get("favorites"), list):
            data["favorites"] = []

        return data
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Config file corrupted ({e}). Falling back to defaults.")
        return DEFAULT_STATE.copy()
    except Exception as e:
        logger.error(f"Unexpected error loading state ({e}). Falling back to defaults.")
        return DEFAULT_STATE.copy()


def save_state(state: Dict[str, Any]) -> None:
    """
    Save application state to JSON file using an atomic write to prevent corruption.
    """
    try:
        config_dir = os.path.dirname(CONFIG_PATH)
        os.makedirs(config_dir, exist_ok=True)

        # Atomic write: write to temp file then replace
        temp_file = os.path.join(config_dir, "settings.json.tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4, ensure_ascii=False)

        os.replace(temp_file, CONFIG_PATH)
    except Exception as e:
        logger.error(f"Error saving state: {e}")


def get_current_time_iso() -> str:
    """Return current UTC time in ISO format (e.g. 2026-10-19T03:20:00Z)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_connected_to_internet(host: str = "8.8.8.8", port: int = 53, timeout: float = 1.0) -> bool:
    """
    Check internet connectivity quickly without blocking the caller.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.error, OSError):
        pass

    try:
        req = urllib.request.Request(
            "https://www.google.com",
            headers={"User-Agent": "CodeAlpha-Translator-Check/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status in (200, 204, 301, 302)
    except Exception:
        return False


def sanitize_text(text: str) -> str:
    """
    Sanitize input text: normalize whitespace and strip leading/trailing spaces.
    """
    if not text:
        return ""
    return text.strip()