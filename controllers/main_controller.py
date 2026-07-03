"""
Main controller for the translation application.

Binds UI events, services, and models.
"""

import logging
from typing import Optional, List
from datetime import datetime

from PySide6.QtCore import QObject, Slot, QThread
from PySide6.QtWidgets import QMessageBox

from models.translation_model import AppState, HistoryItem
from services.translation_service import TranslationService
from ui.main_window import MainWindow
from utils.helpers import save_state, load_state, get_current_time_iso, is_connected_to_internet

logger = logging.getLogger(__name__)


class MainController(QObject):
    """
    Controller orchestrating UI, translation service, and data persistence.
    """

    def __init__(self, window: MainWindow) -> None:
        super().__init__()
        self.window = window
        self.translation_service = TranslationService()
        self.app_state: Optional[AppState] = None
        self.current_translation_thread: Optional[QThread] = None

        # Load state from config
        self._load_state()

        # Connect UI signals to controller slots
        self._connect_signals()

        # Initial history update
        self._refresh_history_list()

    def _load_state(self) -> None:
        """Load app state and sync with window."""
        state_dict = load_state()
        self.app_state = AppState.from_dict(state_dict)
        # Ensure window's app_state is set
        self.window.app_state = self.app_state
        # Update history list with initial data
        self._refresh_history_list()

    def _save_state(self) -> None:
        """Persist current state to file."""
        if self.app_state:
            # Update state from window
            self.app_state.theme = self.window.current_theme
            self.app_state.source_language = self.window.source_lang_combo.currentData()
            self.app_state.target_language = self.window.target_lang_combo.currentData()
            self.app_state.window_width = self.window.width()
            self.app_state.window_height = self.window.height()
            self.app_state.window_x = self.window.x()
            self.app_state.window_y = self.window.y()
            save_state(self.app_state.to_dict())

    def _connect_signals(self) -> None:
        """Connect UI events to controller methods."""
        # Translation request
        self.window.translate_requested.connect(self.handle_translate_request)
        # Swap, clear, copy are handled by UI directly, but we may need to update state.
        self.window.swap_requested.connect(self.handle_swap)
        self.window.clear_requested.connect(self.handle_clear)
        self.window.copy_output_requested.connect(self.handle_copy)
        # History actions
        self.window.history_item_deleted.connect(self.handle_history_delete)
        self.window.history_item_toggle_favorite.connect(self.handle_history_toggle_favorite)
        self.window.history_item_reuse.connect(self.handle_history_reuse)
        self.window.history_filter_changed.connect(self._on_history_filter_changed)


        # Window close event will be handled by window's closeEvent, but we can also connect.
        # We'll let window call save state on close.

    @Slot(str, str, str)
    def handle_translate_request(self, source_text: str, source_lang: str, target_lang: str) -> None:
        """
        Handle translation request: validate, start async translation.
        """
        if not source_text.strip():
            self.window.show_error_message("Source text is empty.")
            return

        # Check internet connectivity
        if not is_connected_to_internet():
            self.window.show_error_message("No internet connection. Please check your network.")
            return

        # Validate languages: if source and target same (and source not auto) -> handled in UI, but double-check.
        if source_lang == target_lang and source_lang != "auto":
            self.window.show_error_message("Source and target languages cannot be the same.")
            return

        # Start translation
        self.window.status_bar.showMessage("Translating...", 0)  # persistent

        # Use async service
        self.current_translation_thread = TranslationService.translate_async(
            source_text,
            source_lang,
            target_lang,
            self.on_translation_finished,
            self.on_translation_error
        )

    @Slot(str, str)
    def on_translation_finished(self, source_text: str, target_text: str) -> None:
        """
        Callback when translation succeeds.
        """
        self.window.set_translation_result(source_text, target_text)
        self.window.status_bar.showMessage("Translation complete", 3000)

        # Add to history
        self._add_history_item(source_text, target_text,
                               self.window.source_lang_combo.currentData(),
                               self.window.target_lang_combo.currentData())
        self._refresh_history_list()
        self._save_state()

    @Slot(str)
    def on_translation_error(self, error_msg: str) -> None:
        """
        Callback when translation fails.
        """
        self.window.show_error_message(error_msg)
        self.window.status_bar.showMessage("Translation failed", 3000)

    def _add_history_item(self, source_text: str, target_text: str, source_lang: str, target_lang: str) -> None:
        """Create a new history item and add to state."""
        new_id = max([item.id for item in self.app_state.history], default=0) + 1
        new_item = HistoryItem(
            id=new_id,
            timestamp=get_current_time_iso(),
            source_lang=source_lang,
            target_lang=target_lang,
            source_text=source_text,
            target_text=target_text,
            is_favorite=False
        )
        self.app_state.history.append(new_item)
        # Also update favorites if needed? Not automatically.

    def _refresh_history_list(self) -> None:
        """Update the history list widget with filtered data."""
        if not self.app_state:
            return
        # Apply filters
        search_text = self.window.search_line.text().strip().lower()
        show_favorites = self.window.show_favorites_check.isChecked()
        filtered = []
        for item in self.app_state.history:
            if show_favorites and not item.is_favorite:
                continue
            if search_text:
                if search_text not in item.source_text.lower() and search_text not in item.target_text.lower():
                    continue
            filtered.append(item)
        # Sort by timestamp descending (most recent first)
        filtered.sort(key=lambda x: x.timestamp, reverse=True)
        self.window.update_history_list(filtered)

    @Slot()
    def handle_swap(self) -> None:
        """Handle swap (already handled in UI, but we may need to update state)."""
        # The UI already swaps combos and text; we just save state.
        self._save_state()

    @Slot()
    def handle_clear(self) -> None:
        """Handle clear (already handled in UI)."""
        # No extra logic needed.
        pass

    @Slot()
    def handle_copy(self) -> None:
        """Handle copy (already handled in UI)."""
        pass

    @Slot(int)
    def handle_history_delete(self, history_id: int) -> None:
        """Delete a history item by id."""
        self.app_state.history = [item for item in self.app_state.history if item.id != history_id]
        self._refresh_history_list()
        self._save_state()

    @Slot(int)
    def handle_history_toggle_favorite(self, history_id: int) -> None:
        """Toggle favorite status of a history item."""
        for item in self.app_state.history:
            if item.id == history_id:
                item.is_favorite = not item.is_favorite
                break
        self._refresh_history_list()
        self._save_state()

    @Slot(str, str, str)
    def _on_history_filter_changed(self, _text: str, _fav: bool) -> None:
        """Refresh history list when filter/search UI changes."""
        self._refresh_history_list()

    @Slot(str, str, str)
    def handle_history_reuse(self, source_text: str, source_lang: str, target_lang: str) -> None:

        """Reuse source text and languages from history."""
        # UI already sets the fields; we might want to auto-translate? No.
        pass

    def save_state(self) -> None:
        """Public method to save state (called on window close)."""
        self._save_state()

