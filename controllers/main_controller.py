"""
Main controller for the translation application.

Binds UI events, services, and models following the MVC architecture.
Ensures true non-blocking background translation with QThread and strong object references.
"""

import logging
from typing import Optional

from PySide6.QtCore import QObject, Slot, QThread

from models.translation_model import AppState, HistoryItem
from services.translation_service import TranslationService, TranslationWorker
from ui.main_window import MainWindow
from utils.helpers import save_state, load_state, get_current_time_iso

logger = logging.getLogger(__name__)


class MainController(QObject):
    """
    Controller orchestrating UI, translation worker threads, and data persistence.
    """

    def __init__(self, window: MainWindow) -> None:
        super().__init__()
        self.window = window
        self.translation_service = TranslationService()
        self.app_state: Optional[AppState] = None

        # Strong instance references for active worker and thread
        self.worker: Optional[TranslationWorker] = None
        self.thread: Optional[QThread] = None
        self.is_translating: bool = False

        # Load state from config
        self._load_state()

        # Connect UI signals to controller slots
        self._connect_signals()

        # Initial history update
        self._refresh_history_list()

    @property
    def current_translation_thread(self) -> Optional[QThread]:
        """Backward compatibility property for current active thread."""
        return self.thread

    @current_translation_thread.setter
    def current_translation_thread(self, val: Optional[QThread]) -> None:
        self.thread = val

    def _load_state(self) -> None:
        """Load app state and sync with window."""
        state_dict = load_state()
        self.app_state = AppState.from_dict(state_dict)
        self.window.app_state = self.app_state
        self._refresh_history_list()

    def _save_state(self) -> None:
        """Persist current state to file."""
        if not self.app_state or not self.window:
            return

        try:
            self.app_state.theme = self.window.current_theme
            self.app_state.source_language = self.window.source_lang_combo.currentData() or "auto"
            self.app_state.target_language = self.window.target_lang_combo.currentData() or "en"
            self.app_state.window_width = self.window.width()
            self.app_state.window_height = self.window.height()
            self.app_state.window_x = self.window.x()
            self.app_state.window_y = self.window.y()
            # Synchronize favorites list
            self.app_state.favorites = [item for item in self.app_state.history if item.is_favorite]
            save_state(self.app_state.to_dict())
        except Exception as e:
            logger.error(f"Error persisting state: {e}")

    def _connect_signals(self) -> None:
        """Connect UI events to controller methods."""
        self.window.translate_requested.connect(self.handle_translate_request)
        self.window.swap_requested.connect(self.handle_swap)
        self.window.clear_requested.connect(self.handle_clear)
        self.window.copy_output_requested.connect(self.handle_copy)
        self.window.history_item_deleted.connect(self.handle_history_delete)
        self.window.history_item_toggle_favorite.connect(self.handle_history_toggle_favorite)
        self.window.history_item_reuse.connect(self.handle_history_reuse)
        self.window.history_filter_changed.connect(self._on_history_filter_changed)
        self.window.window_closing.connect(self.cleanup)

    @Slot(str, str, str)
    def handle_translate_request(self, source_text: str, source_lang: str, target_lang: str) -> None:
        """
        Handle translation request: validate, debounce, and start non-blocking QThread worker.
        Never blocks or calls thread.wait() on the main GUI thread.
        """
        # 1. Debounce / busy lock: ignore duplicate triggers while running
        if self.is_translating:
            logger.info("Translation already in progress; ignoring duplicate trigger.")
            self.window.status_bar.showMessage("Translation in progress, please wait...", 2000)
            return

        source_clean = source_text.strip()
        if not source_clean:
            self.window.set_translating(False)
            self.window.show_error_message("Source text is empty.")
            return

        # 2. Language pair validation
        if source_lang == target_lang and source_lang != "auto":
            self.window.set_translating(False)
            self.window.show_error_message("Source and target languages cannot be identical.")
            return

        # 4. Set busy lock and update UI immediately
        self.is_translating = True
        self.window.set_translating(True)

        # 5. Clean up any previous dead thread
        if self.thread and not self.thread.isRunning():
            self.thread = None
            self.worker = None

        # 6. Initialize dedicated QThread and worker with strong instance references
        self.thread = QThread()
        self.worker = TranslationWorker(source_clean, source_lang, target_lang)
        self.worker.moveToThread(self.thread)

        # 7. Wire signals safely via Qt QueuedConnection back to GUI thread
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_translation_finished)
        self.worker.error.connect(self.on_translation_error)

        # Automatically quit thread and schedule deletion on completion
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._on_thread_finished)

        # 8. Start non-blocking thread (never call thread.wait() or worker.run() here!)
        self.thread.start()

    @Slot()
    def _on_thread_finished(self) -> None:
        """Handle worker thread cleanup when thread completes execution."""
        self.is_translating = False
        self.window.set_translating(False)
        self.thread = None
        self.worker = None

    @Slot(str, str)
    def on_translation_finished(self, source_text: str, target_text: str) -> None:
        """Callback on main GUI thread when translation succeeds."""
        self.is_translating = False
        self.window.set_translating(False)
        self.window.set_translation_result(source_text, target_text)
        self.window.status_bar.showMessage("Translation completed successfully ✅", 3000)

        # Record into history and persist state
        source_lang = self.window.source_lang_combo.currentData() or "auto"
        target_lang = self.window.target_lang_combo.currentData() or "en"
        self._add_history_item(source_text, target_text, source_lang, target_lang)
        self._refresh_history_list()
        self._save_state()

    @Slot(str)
    def on_translation_error(self, error_msg: str) -> None:
        """Callback on main GUI thread when translation fails."""
        self.is_translating = False
        self.window.set_translating(False)
        self.window.show_error_message(error_msg)
        self.window.status_bar.showMessage("Translation failed", 3000)

    def _add_history_item(self, source_text: str, target_text: str, source_lang: str, target_lang: str) -> None:
        """Create a new history item and add to state."""
        if not self.app_state:
            return

        new_id = max([item.id for item in self.app_state.history], default=0) + 1
        new_item = HistoryItem(
            id=new_id,
            timestamp=get_current_time_iso(),
            source_lang=source_lang,
            target_lang=target_lang,
            source_text=source_text,
            target_text=target_text,
            is_favorite=False,
        )
        self.app_state.history.append(new_item)

    def _refresh_history_list(self) -> None:
        """Update the history list widget with filtered data."""
        if not self.app_state or not self.window:
            return

        search_text = self.window.search_line.text().strip().lower()
        show_favorites = self.window.show_favorites_check.isChecked()

        filtered = []
        for item in self.app_state.history:
            if show_favorites and not item.is_favorite:
                continue
            if search_text:
                in_src = search_text in item.source_text.lower()
                in_tgt = search_text in item.target_text.lower()
                if not (in_src or in_tgt):
                    continue
            filtered.append(item)

        # Sort by timestamp descending (most recent first)
        filtered.sort(key=lambda x: x.timestamp, reverse=True)
        self.window.update_history_list(filtered)

    @Slot()
    def handle_swap(self) -> None:
        """Handle swap request."""
        self._save_state()

    @Slot()
    def handle_clear(self) -> None:
        """Handle clear request."""
        pass

    @Slot()
    def handle_copy(self) -> None:
        """Handle copy request."""
        pass

    @Slot(int)
    def handle_history_delete(self, history_id: int) -> None:
        """Delete a history item by id."""
        if not self.app_state:
            return
        self.app_state.history = [item for item in self.app_state.history if item.id != history_id]
        self._refresh_history_list()
        self._save_state()
        self.window.status_bar.showMessage("Item deleted from history", 2000)

    @Slot(int)
    def handle_history_toggle_favorite(self, history_id: int) -> None:
        """Toggle favorite status of a history item."""
        if not self.app_state:
            return
        for item in self.app_state.history:
            if item.id == history_id:
                item.is_favorite = not item.is_favorite
                status = "added to" if item.is_favorite else "removed from"
                self.window.status_bar.showMessage(f"Item {status} favorites", 2000)
                break
        self._refresh_history_list()
        self._save_state()

    @Slot(str, bool)
    def _on_history_filter_changed(self, _text: str, _fav: bool) -> None:
        """Refresh history list when filter/search UI changes."""
        self._refresh_history_list()

    @Slot(str, str, str)
    def handle_history_reuse(self, source_text: str, source_lang: str, target_lang: str) -> None:
        """Log reuse action."""
        logger.info(f"Reused history item ({source_lang} -> {target_lang})")

    @Slot()
    def cleanup(self) -> None:
        """Gracefully terminate background workers on window close and persist state."""
        if self.thread and self.thread.isRunning():
            logger.info("Cleaning up active translation thread on shutdown...")
            if self.worker:
                self.worker.cancel()
            self.thread.quit()
            if not self.thread.wait(1000):
                logger.warning("Translation thread did not exit within timeout; terminating...")
                self.thread.terminate()
                self.thread.wait(500)
            self.thread = None
            self.worker = None

        self.is_translating = False
        self._save_state()

    def save_state(self) -> None:
        """Public method to save state and cleanup running worker threads."""
        self.cleanup()
