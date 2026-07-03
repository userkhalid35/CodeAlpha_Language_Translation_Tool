"""
Data models for the translation application.

This module defines the data structures used throughout the application,
including HistoryItem, Favorites, and the overall State.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime


@dataclass
class HistoryItem:
    """
    Represents a single translation entry in history.

    Attributes:
        id: Unique identifier (integer auto-increment).
        timestamp: ISO format datetime string.
        source_lang: Source language code or 'auto'.
        target_lang: Target language code.
        source_text: Original text.
        target_text: Translated text.
        is_favorite: Boolean indicating if marked as favorite.
    """
    id: int
    timestamp: str
    source_lang: str
    target_lang: str
    source_text: str
    target_text: str
    is_favorite: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryItem":
        """Create instance from dictionary."""
        return cls(**data)


@dataclass
class AppState:
    """
    Holds the entire application state.

    Attributes:
        theme: 'dark' or 'light'.
        window_width: int.
        window_height: int.
        window_x: int.
        window_y: int.
        source_language: language code for source.
        target_language: language code for target.
        history: List of HistoryItem.
        favorites: List of HistoryItem (could be separate or referenced by id).
    """
    theme: str = "dark"
    window_width: int = 1024
    window_height: int = 768
    window_x: int = 100
    window_y: int = 100
    source_language: str = "auto"
    target_language: str = "en"
    history: List[HistoryItem] = field(default_factory=list)
    favorites: List[HistoryItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary, converting HistoryItems to dicts."""
        return {
            "theme": self.theme,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "window_x": self.window_x,
            "window_y": self.window_y,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "history": [item.to_dict() for item in self.history],
            "favorites": [item.to_dict() for item in self.favorites],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppState":
        """Create instance from dictionary."""
        history = [HistoryItem.from_dict(h) for h in data.get("history", [])]
        favorites = [HistoryItem.from_dict(f) for f in data.get("favorites", [])]
        return cls(
            theme=data.get("theme", "dark"),
            window_width=data.get("window_width", 1024),
            window_height=data.get("window_height", 768),
            window_x=data.get("window_x", 100),
            window_y=data.get("window_y", 100),
            source_language=data.get("source_language", "auto"),
            target_language=data.get("target_language", "en"),
            history=history,
            favorites=favorites,
        )