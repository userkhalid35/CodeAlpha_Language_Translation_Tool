"""
Data models for the translation application.

This module defines the data structures used throughout the application,
including HistoryItem and the overall AppState.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any


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
    def from_dict(cls, data: Dict[str, Any]) -> "HistoryItem":
        """Create instance from dictionary with defensive fallbacks."""
        if not isinstance(data, dict):
            return cls(
                id=0,
                timestamp="",
                source_lang="auto",
                target_lang="en",
                source_text="",
                target_text="",
                is_favorite=False,
            )
        return cls(
            id=int(data.get("id", 0)),
            timestamp=str(data.get("timestamp", "")),
            source_lang=str(data.get("source_lang", "auto")),
            target_lang=str(data.get("target_lang", "en")),
            source_text=str(data.get("source_text", "")),
            target_text=str(data.get("target_text", "")),
            is_favorite=bool(data.get("is_favorite", False)),
        )


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
        max_characters: maximum supported character count (default: 50,000).
        history: List of HistoryItem.
        favorites: List of HistoryItem.
    """
    theme: str = "dark"
    window_width: int = 1024
    window_height: int = 768
    window_x: int = 100
    window_y: int = 100
    source_language: str = "auto"
    target_language: str = "en"
    max_characters: int = 50000
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
            "max_characters": self.max_characters,
            "history": [item.to_dict() for item in self.history],
            "favorites": [item.to_dict() for item in self.favorites],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppState":
        """Create instance from dictionary with defensive type validation."""
        if not isinstance(data, dict):
            return cls()

        raw_history = data.get("history", [])
        if isinstance(raw_history, list):
            history = [HistoryItem.from_dict(h) for h in raw_history if isinstance(h, dict)]
        else:
            history = []

        raw_favorites = data.get("favorites", [])
        if isinstance(raw_favorites, list):
            favorites = [HistoryItem.from_dict(f) for f in raw_favorites if isinstance(f, dict)]
        else:
            favorites = []

        return cls(
            theme=str(data.get("theme", "dark")),
            window_width=max(int(data.get("window_width", 1024)), 600),
            window_height=max(int(data.get("window_height", 768)), 450),
            window_x=max(int(data.get("window_x", 100)), 0),
            window_y=max(int(data.get("window_y", 100)), 0),
            source_language=str(data.get("source_language", "auto")),
            target_language=str(data.get("target_language", "en")),
            max_characters=max(int(data.get("max_characters", 50000)), 50000),
            history=history,
            favorites=favorites,
        )