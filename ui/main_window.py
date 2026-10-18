"""
Main application window.

This module defines the main UI layout, including all panels, menus,
and status bar. It follows the vertical stack layout and provides rich UX.
"""

import logging
from typing import Optional, List, Dict, Any

from PySide6.QtCore import Qt, QSize, Signal, Slot, QTimer, QThread
from PySide6.QtGui import (
    QAction, QKeySequence, QFont, QIcon, QPixmap
)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QComboBox, QPlainTextEdit,
    QPushButton, QListWidget, QListWidgetItem, QLineEdit,
    QMenuBar, QMenu, QToolBar, QStatusBar, QMessageBox,
    QCheckBox, QApplication
)

from ui.styles import DARK_STYLE, LIGHT_STYLE
from models.translation_model import HistoryItem, AppState
from services.translation_service import TranslationService
from utils.helpers import (
    load_state, save_state, is_connected_to_internet
)

logger = logging.getLogger(__name__)


class NetworkCheckWorker(QThread):
    """Background worker to check connectivity without freezing GUI event loop."""
    status_checked = Signal(bool)

    def run(self) -> None:
        online = is_connected_to_internet(timeout=1.0)
        self.status_checked.emit(online)


class HistoryListWidget(QListWidget):
    """
    Custom list widget to display history items with right-click context menu
    and double-click to reuse.
    """
    item_selected_for_reuse = Signal(str, str, str)  # source_text, source_lang, target_lang
    item_toggle_favorite = Signal(int)  # history item id
    item_delete = Signal(int)           # history item id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    def show_context_menu(self, pos) -> None:
        """Show context menu on right-click."""
        item = self.itemAt(pos)
        if not item:
            return
        history_id = item.data(int(Qt.ItemDataRole.UserRole))
        if history_id is None:
            return

        menu = QMenu(self)
        reuse_action = QAction("Reuse Translation", self)
        reuse_action.triggered.connect(lambda: self.emit_reuse(history_id))

        favorite_action = QAction("Toggle Favorite (★)", self)
        favorite_action.triggered.connect(lambda: self.emit_favorite(history_id))

        delete_action = QAction("Delete from History", self)
        delete_action.triggered.connect(lambda: self.emit_delete(history_id))

        menu.addAction(reuse_action)
        menu.addAction(favorite_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        menu.exec(self.mapToGlobal(pos))

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Double click directly reuses the history item."""
        history_id = item.data(int(Qt.ItemDataRole.UserRole))
        if history_id is not None:
            self.emit_reuse(history_id)

    def emit_reuse(self, history_id: int) -> None:
        """Emit signal to reuse the item's source text and languages."""
        user_role = int(Qt.ItemDataRole.UserRole)
        for i in range(self.count()):
            item = self.item(i)
            if item.data(user_role) == history_id:
                source_text = item.data(user_role + 1) or ""
                source_lang = item.data(user_role + 2) or "auto"
                target_lang = item.data(user_role + 3) or "en"
                self.item_selected_for_reuse.emit(source_text, source_lang, target_lang)
                break

    def emit_favorite(self, history_id: int) -> None:
        self.item_toggle_favorite.emit(history_id)

    def emit_delete(self, history_id: int) -> None:
        self.item_delete.emit(history_id)


class MainWindow(QMainWindow):
    """
    Main application window.

    Layout (vertical):
    - Title bar (menu, toolbar)
    - Source panel: language dropdown + text input + character counter
    - Control bar: Translate, Swap, Clear buttons
    - Target panel: language dropdown + text output + copy button
    - Bottom panel: searchable history/favorites list
    - Status bar: network indicator and operation feedback
    """

    # Signals for controller communication
    translate_requested = Signal(str, str, str)  # source_text, source_lang, target_lang
    swap_requested = Signal()
    clear_requested = Signal()
    copy_output_requested = Signal()
    history_item_deleted = Signal(int)  # id
    history_item_toggle_favorite = Signal(int)
    history_item_reuse = Signal(str, str, str)  # source_text, source_lang, target_lang
    history_filter_changed = Signal(str, bool)  # search_text, show_favorites_only
    window_closing = Signal()  # emitted during closeEvent for safe thread cleanup

    def __init__(self) -> None:
        super().__init__()
        self.app_state: Optional[AppState] = None
        self.current_theme = "dark"
        self._net_worker: Optional[NetworkCheckWorker] = None
        self._setup_ui()
        self._load_initial_state()
        self._populate_language_dropdowns()

    def _setup_ui(self) -> None:
        """Create the main UI layout."""
        self.setWindowTitle("CodeAlpha Translator")
        self.setMinimumSize(600, 500)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Menu bar & Toolbar
        self._create_menu_bar()
        self._create_toolbar()

        # --- Source Panel ---
        source_group = QGroupBox("Source")
        source_layout = QVBoxLayout(source_group)
        lang_row = QHBoxLayout()
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.setMinimumWidth(180)
        lang_row.addWidget(QLabel("Language:"))
        lang_row.addWidget(self.source_lang_combo)
        lang_row.addStretch()

        self.char_counter_label = QLabel("0 characters")
        self.char_counter_label.setStyleSheet("color: #888888; font-size: 11px;")
        lang_row.addWidget(self.char_counter_label)
        source_layout.addLayout(lang_row)

        self.source_text_edit = QPlainTextEdit()
        self.source_text_edit.setPlaceholderText("Enter text to translate...")
        self.source_text_edit.textChanged.connect(self._update_char_count)
        source_layout.addWidget(self.source_text_edit)
        main_layout.addWidget(source_group, stretch=2)

        # --- Control Bar ---
        control_layout = QHBoxLayout()
        control_layout.setSpacing(12)
        self.translate_btn = QPushButton("Translate (Ctrl+Enter)")
        self.translate_btn.setDefault(True)
        self.translate_btn.clicked.connect(self._on_translate_clicked)
        control_layout.addWidget(self.translate_btn)

        self.swap_btn = QPushButton("⇄ Swap Languages")
        self.swap_btn.clicked.connect(self._on_swap_clicked)
        control_layout.addWidget(self.swap_btn)

        self.clear_btn = QPushButton("Clear (Ctrl+L)")
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        control_layout.addWidget(self.clear_btn)

        control_layout.addStretch()
        main_layout.addLayout(control_layout)

        # --- Target Panel ---
        target_group = QGroupBox("Target")
        target_layout = QVBoxLayout(target_group)
        lang_row2 = QHBoxLayout()
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.setMinimumWidth(180)
        lang_row2.addWidget(QLabel("Language:"))
        lang_row2.addWidget(self.target_lang_combo)
        lang_row2.addStretch()

        self.copy_btn = QPushButton("📋 Copy Output")
        self.copy_btn.clicked.connect(self._on_copy_clicked)
        lang_row2.addWidget(self.copy_btn)
        target_layout.addLayout(lang_row2)

        self.target_text_edit = QPlainTextEdit()
        self.target_text_edit.setReadOnly(True)
        self.target_text_edit.setPlaceholderText("Translation will appear here...")
        target_layout.addWidget(self.target_text_edit)
        main_layout.addWidget(target_group, stretch=2)

        # --- Bottom Panel: History & Favorites ---
        bottom_group = QGroupBox("History & Favorites (Double-click to reuse, right-click for menu)")
        bottom_layout = QVBoxLayout(bottom_group)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_line = QLineEdit()
        self.search_line.setPlaceholderText("Filter history by keyword...")
        self.search_line.textChanged.connect(self._filter_history)
        search_layout.addWidget(self.search_line)

        self.show_favorites_check = QCheckBox("Show Favorites only (★)")
        self.show_favorites_check.stateChanged.connect(self._filter_history)
        search_layout.addWidget(self.show_favorites_check)
        bottom_layout.addLayout(search_layout)

        self.history_list = HistoryListWidget()
        self.history_list.item_selected_for_reuse.connect(self._on_history_reuse)
        self.history_list.item_toggle_favorite.connect(self._on_history_favorite_toggle)
        self.history_list.item_delete.connect(self._on_history_delete)
        bottom_layout.addWidget(self.history_list)
        main_layout.addWidget(bottom_group, stretch=2)

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.network_indicator = QLabel("Network: Checking...")
        self.status_bar.addPermanentWidget(self.network_indicator)
        self._update_network_status()

        # Timer to periodically check network
        self.network_timer = QTimer(self)
        self.network_timer.timeout.connect(self._update_network_status)
        self.network_timer.start(8000)  # every 8 seconds

        # Keyboard shortcuts
        self._setup_shortcuts()

        # Apply default theme
        self.apply_theme("dark")

    def _create_menu_bar(self) -> None:
        """Create application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        copy_action = QAction("Copy Output (Ctrl+Shift+C)", self)
        copy_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        copy_action.triggered.connect(self._on_copy_clicked)
        edit_menu.addAction(copy_action)

        clear_action = QAction("Clear All", self)
        clear_action.setShortcut(QKeySequence("Ctrl+L"))
        clear_action.triggered.connect(self._on_clear_clicked)
        edit_menu.addAction(clear_action)

        # View menu
        view_menu = menubar.addMenu("&View")
        theme_action = QAction("Toggle Dark/Light Theme", self)
        theme_action.setShortcut(QKeySequence("Ctrl+T"))
        theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(theme_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")
        about_action = QAction("About CodeAlpha Translator", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self) -> None:
        """Create a compact toolbar with quick actions."""
        toolbar = QToolBar("Quick Tools")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        theme_btn = QPushButton("🌓 Toggle Theme")
        theme_btn.clicked.connect(self._toggle_theme)
        toolbar.addWidget(theme_btn)

    def _setup_shortcuts(self) -> None:
        """Setup persistent application-wide keyboard shortcuts."""
        self.translate_shortcut_action = QAction(self)
        self.translate_shortcut_action.setShortcuts([
            QKeySequence("Ctrl+Return"),
            QKeySequence("Ctrl+Enter"),
        ])
        self.translate_shortcut_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self.translate_shortcut_action.triggered.connect(self._on_translate_clicked)
        self.addAction(self.translate_shortcut_action)

    def _populate_language_dropdowns(self) -> None:
        """Fill language comboboxes with supported languages."""
        langs = TranslationService.get_supported_languages()

        self.source_lang_combo.blockSignals(True)
        self.target_lang_combo.blockSignals(True)

        self.source_lang_combo.clear()
        self.target_lang_combo.clear()

        # Add "Auto Detect" for source
        self.source_lang_combo.addItem("Auto Detect", "auto")

        # Add languages sorted alphabetically
        for name, code in sorted(langs.items()):
            display_name = name.capitalize()
            self.source_lang_combo.addItem(display_name, code)
            self.target_lang_combo.addItem(display_name, code)

        self.source_lang_combo.blockSignals(False)
        self.target_lang_combo.blockSignals(False)

        # Set default selections from state
        if self.app_state:
            self._set_combo_by_code(self.source_lang_combo, self.app_state.source_language)
            self._set_combo_by_code(self.target_lang_combo, self.app_state.target_language)
        else:
            self._set_combo_by_code(self.source_lang_combo, "auto")
            self._set_combo_by_code(self.target_lang_combo, "en")

    def _set_combo_by_code(self, combo: QComboBox, code: str) -> None:
        """Set combo selection by language code."""
        if not code:
            combo.setCurrentIndex(0)
            return

        index = combo.findData(code)
        if index >= 0:
            combo.setCurrentIndex(index)
        else:
            combo.setCurrentIndex(0)

    def _update_char_count(self) -> None:
        """Update character counter label."""
        count = len(self.source_text_edit.toPlainText())
        self.char_counter_label.setText(f"{count} character{'s' if count != 1 else ''}")

    def set_translating(self, is_translating: bool) -> None:
        """Update UI state during active translation."""
        if is_translating:
            self.translate_btn.setEnabled(False)
            self.translate_btn.setText("Translating...")
            self.status_bar.showMessage("Translating text...", 0)
        else:
            self.translate_btn.setEnabled(True)
            self.translate_btn.setText("Translate (Ctrl+Enter)")

    @Slot()
    def _on_translate_clicked(self) -> None:
        """Handle translate button click or Ctrl+Enter."""
        if not self.translate_btn.isEnabled():
            return

        source_text = self.source_text_edit.toPlainText().strip()
        if not source_text:
            QMessageBox.information(self, "Empty Input", "Please enter text to translate.")
            return

        source_lang = self.source_lang_combo.currentData()
        target_lang = self.target_lang_combo.currentData()

        if source_lang == target_lang and source_lang != "auto":
            QMessageBox.warning(
                self,
                "Invalid Language Pair",
                "Source and target languages cannot be identical. Please select different languages or use 'Auto Detect'."
            )
            return

        # Immediately disable Translate button and show status
        self.set_translating(True)
        self.translate_requested.emit(source_text, source_lang, target_lang)

    @Slot()
    def _on_swap_clicked(self) -> None:
        """
        Handle swap button click: safely swap languages and text using codes.
        """
        src_code = self.source_lang_combo.currentData()
        tgt_code = self.target_lang_combo.currentData()

        if src_code == "auto":
            QMessageBox.information(
                self,
                "Cannot Swap",
                "Cannot swap while source language is 'Auto Detect'. Please choose a specific source language first."
            )
            return

        # Swap languages by code safely
        self._set_combo_by_code(self.source_lang_combo, tgt_code)
        self._set_combo_by_code(self.target_lang_combo, src_code)

        # Swap text: source <-> target
        src_text = self.source_text_edit.toPlainText()
        tgt_text = self.target_text_edit.toPlainText()
        self.source_text_edit.setPlainText(tgt_text)
        self.target_text_edit.setPlainText(src_text)

        self.status_bar.showMessage("Languages and text swapped", 2000)
        self.swap_requested.emit()

    @Slot()
    def _on_clear_clicked(self) -> None:
        """Handle clear button click: clear text fields."""
        self.source_text_edit.clear()
        self.target_text_edit.clear()
        self.status_bar.showMessage("Cleared", 1500)
        self.clear_requested.emit()

    @Slot()
    def _on_copy_clicked(self) -> None:
        """Handle copy button: copy target text to clipboard."""
        target_text = self.target_text_edit.toPlainText()
        if target_text.strip():
            clipboard = QApplication.clipboard()
            clipboard.setText(target_text)
            self.status_bar.showMessage("Copied translation to clipboard ✅", 2500)
            self.copy_output_requested.emit()
        else:
            QMessageBox.information(self, "Nothing to Copy", "No translation output available to copy.")

    def _filter_history(self, *args) -> None:
        """Filter history list based on search text and favorites toggle."""
        search_query = self.search_line.text().strip()
        favorites_only = self.show_favorites_check.isChecked()
        self.history_filter_changed.emit(search_query, favorites_only)

    def update_history_list(self, history_items: List[HistoryItem]) -> None:
        """Populate the history list widget with given items."""
        self.history_list.clear()
        user_role = int(Qt.ItemDataRole.UserRole)
        for item in history_items:
            fav_marker = "★ " if item.is_favorite else ""
            src_snip = item.source_text.replace("\n", " ").strip()
            tgt_snip = item.target_text.replace("\n", " ").strip()
            if len(src_snip) > 35:
                src_snip = src_snip[:32] + "..."
            if len(tgt_snip) > 35:
                tgt_snip = tgt_snip[:32] + "..."

            display_text = f"{fav_marker}[{item.source_lang} → {item.target_lang}] {src_snip} ➔ {tgt_snip}"
            list_item = QListWidgetItem(display_text)
            list_item.setData(user_role, item.id)
            list_item.setData(user_role + 1, item.source_text)
            list_item.setData(user_role + 2, item.source_lang)
            list_item.setData(user_role + 3, item.target_lang)

            tooltip = (
                f"ID: {item.id}\n"
                f"Date: {item.timestamp}\n"
                f"Pair: {item.source_lang} -> {item.target_lang}\n\n"
                f"Source:\n{item.source_text}\n\n"
                f"Translation:\n{item.target_text}\n\n"
                f"(Double click to reuse)"
            )
            list_item.setToolTip(tooltip)
            self.history_list.addItem(list_item)

    @Slot(int)
    def _on_history_delete(self, history_id: int) -> None:
        self.history_item_deleted.emit(history_id)

    @Slot(int)
    def _on_history_favorite_toggle(self, history_id: int) -> None:
        self.history_item_toggle_favorite.emit(history_id)

    @Slot(str, str, str)
    def _on_history_reuse(self, source_text: str, source_lang: str, target_lang: str) -> None:
        """Handle reuse from history: populate inputs and notify controller."""
        self.source_text_edit.setPlainText(source_text)
        self._set_combo_by_code(self.source_lang_combo, source_lang)
        self._set_combo_by_code(self.target_lang_combo, target_lang)
        self.status_bar.showMessage("Reused text and language settings from history", 2500)
        self.history_item_reuse.emit(source_text, source_lang, target_lang)

    @Slot()
    def _toggle_theme(self) -> None:
        """Toggle between dark and light themes."""
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self.apply_theme(new_theme)
        if self.app_state:
            self.app_state.theme = new_theme
            save_state(self.app_state.to_dict())

    def apply_theme(self, theme: str) -> None:
        """Apply the specified theme."""
        if theme == "light":
            self.setStyleSheet(LIGHT_STYLE)
            self.current_theme = "light"
        else:
            self.setStyleSheet(DARK_STYLE)
            self.current_theme = "dark"

    def _update_network_status(self) -> None:
        """Check network asynchronously in background thread to avoid any GUI freeze."""
        if hasattr(self, "_net_worker") and self._net_worker and self._net_worker.isRunning():
            return
        self._net_worker = NetworkCheckWorker(self)
        self._net_worker.status_checked.connect(self._on_network_status_checked)
        self._net_worker.start()

    @Slot(bool)
    def _on_network_status_checked(self, online: bool) -> None:
        """Update network indicator safely on GUI thread without blocking."""
        if online:
            self.network_indicator.setText("Network: Online ✅")
            self.network_indicator.setStyleSheet("color: #4caf50; font-weight: bold;")
        else:
            self.network_indicator.setText("Network: Offline ❌")
            self.network_indicator.setStyleSheet("color: #f44336; font-weight: bold;")

    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About CodeAlpha Translator",
            "<h3>CodeAlpha Language Translation Tool</h3>"
            "<p>A modern desktop translation tool built with Python, PySide6, and deep-translator.</p>"
            "<p><b>Features:</b> Asynchronous translation, 100+ languages, auto-detection, "
            "persistent history, favorites, and dark/light themes.</p>"
            "<p>© CodeAlpha</p>"
        )

    def _load_initial_state(self) -> None:
        """Load initial state for window size and theme."""
        state_dict = load_state()
        self.app_state = AppState.from_dict(state_dict)
        self.apply_theme(self.app_state.theme)
        self.resize(self.app_state.window_width, self.app_state.window_height)
        self.move(self.app_state.window_x, self.app_state.window_y)

    def closeEvent(self, event) -> None:
        """Stop timers, notify controller of closing for thread cleanup, and accept close."""
        self.window_closing.emit()
        if hasattr(self, "network_timer") and self.network_timer.isActive():
            self.network_timer.stop()
        if hasattr(self, "_net_worker") and self._net_worker and self._net_worker.isRunning():
            self._net_worker.quit()
            self._net_worker.wait(200)
        if self.app_state:
            self.app_state.window_width = self.width()
            self.app_state.window_height = self.height()
            self.app_state.window_x = self.x()
            self.app_state.window_y = self.y()
            self.app_state.source_language = self.source_lang_combo.currentData()
            self.app_state.target_language = self.target_lang_combo.currentData()
            save_state(self.app_state.to_dict())
        event.accept()

    def set_translation_result(self, source_text: str, target_text: str) -> None:
        """Display translation result in target panel."""
        self.target_text_edit.setPlainText(target_text)

    def show_error_message(self, message: str) -> None:
        """Display an error message in status bar and warning modal."""
        self.status_bar.showMessage(f"Error: {message}", 5000)
        QMessageBox.warning(self, "Translation Notice", message)