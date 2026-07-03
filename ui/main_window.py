"""
Main application window.

This module defines the main UI layout, including all panels, menus,
and status bar. It follows the specified vertical stack layout.
"""

import logging
import os
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime

from PySide6.QtCore import Qt, QSize, Signal, Slot, QTimer
from PySide6.QtGui import (
    QAction, QKeySequence, QFont, QFontDatabase, QIcon, QPixmap
)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QGroupBox, QLabel, QComboBox, QTextEdit, QPlainTextEdit,
    QPushButton, QListWidget, QListWidgetItem, QLineEdit,
    QMenuBar, QMenu, QToolBar, QStatusBar, QMessageBox,
    QSizePolicy, QSpacerItem, QCheckBox, QApplication, QStyle,
    QStyleFactory
)

from ui.styles import DARK_STYLE, LIGHT_STYLE
from models.translation_model import HistoryItem, AppState
from services.translation_service import TranslationService
from utils.helpers import (
    load_state, save_state, get_current_time_iso, is_connected_to_internet
)

logger = logging.getLogger(__name__)


class HistoryListWidget(QListWidget):
    """
    Custom list widget to display history items with additional interactions.
    """
    item_selected_for_reuse = Signal(str, str, str)  # source_text, source_lang, target_lang
    item_toggle_favorite = Signal(int)  # history item id
    item_delete = Signal(int)  # history item id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, pos) -> None:
        """Show context menu on right-click."""
        item = self.itemAt(pos)
        if not item:
            return
        history_id = item.data(Qt.UserRole)
        menu = QMenu(self)
        reuse_action = QAction("Reuse (source → source)", self)
        reuse_action.triggered.connect(lambda: self.emit_reuse(history_id))
        favorite_action = QAction("Toggle Favorite", self)
        favorite_action.triggered.connect(lambda: self.emit_favorite(history_id))
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.emit_delete(history_id))
        menu.addAction(reuse_action)
        menu.addAction(favorite_action)
        menu.addAction(delete_action)
        menu.exec(self.mapToGlobal(pos))

    def emit_reuse(self, history_id: int) -> None:
        """Emit signal to reuse the item's source text and languages."""
        # We need to retrieve the item data. We'll store full history item in data.
        # Instead, we'll fetch from model via controller; but we'll just emit source and languages.
        # Let's fetch the item's stored data from the list item.
        for i in range(self.count()):
            item = self.item(i)
            if item.data(Qt.UserRole) == history_id:
                # item's tooltip or additional data
                source_text = item.data(Qt.UserRole + 1)  # custom role
                source_lang = item.data(Qt.UserRole + 2)
                target_lang = item.data(Qt.UserRole + 3)
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
    - Status bar: network indicator
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


    def __init__(self) -> None:
        super().__init__()
        self.app_state: Optional[AppState] = None
        self.translation_threads = []  # keep track of running threads? Not needed.
        self.current_theme = "dark"
        self._setup_ui()
        self._load_initial_state()
        self._populate_language_dropdowns()

    def _setup_ui(self) -> None:
        """Create the main UI layout."""
        self.setWindowTitle("CodeAlpha Translator")
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Menu bar
        self._create_menu_bar()

        # Toolbar
        self._create_toolbar()

        # --- Source Panel ---
        source_group = QGroupBox("Source")
        source_layout = QVBoxLayout(source_group)
        # Language row
        lang_row = QHBoxLayout()
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.setMinimumWidth(160)
        lang_row.addWidget(QLabel("Language:"))
        lang_row.addWidget(self.source_lang_combo)
        lang_row.addStretch()
        # Character counter
        self.char_counter_label = QLabel("0 characters")
        lang_row.addWidget(self.char_counter_label)
        source_layout.addLayout(lang_row)
        # Text input
        self.source_text_edit = QPlainTextEdit()
        self.source_text_edit.setPlaceholderText("Enter text to translate...")
        self.source_text_edit.textChanged.connect(self._update_char_count)
        source_layout.addWidget(self.source_text_edit)
        main_layout.addWidget(source_group)

        # --- Control Bar ---
        control_layout = QHBoxLayout()
        control_layout.setSpacing(12)
        self.translate_btn = QPushButton("Translate")
        self.translate_btn.setDefault(True)
        self.translate_btn.clicked.connect(self._on_translate_clicked)
        control_layout.addWidget(self.translate_btn)
        self.swap_btn = QPushButton("Swap")
        self.swap_btn.clicked.connect(self._on_swap_clicked)
        control_layout.addWidget(self.swap_btn)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        control_layout.addWidget(self.clear_btn)
        control_layout.addStretch()
        main_layout.addLayout(control_layout)

        # --- Target Panel ---
        target_group = QGroupBox("Target")
        target_layout = QVBoxLayout(target_group)
        lang_row2 = QHBoxLayout()
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.setMinimumWidth(160)
        lang_row2.addWidget(QLabel("Language:"))
        lang_row2.addWidget(self.target_lang_combo)
        lang_row2.addStretch()
        # Copy button
        self.copy_btn = QPushButton("Copy")
        self.copy_btn.clicked.connect(self._on_copy_clicked)
        lang_row2.addWidget(self.copy_btn)
        target_layout.addLayout(lang_row2)
        # Text output
        self.target_text_edit = QPlainTextEdit()
        self.target_text_edit.setReadOnly(True)
        self.target_text_edit.setPlaceholderText("Translation will appear here...")
        target_layout.addWidget(self.target_text_edit)
        main_layout.addWidget(target_group)

        # --- Bottom Panel: History & Favorites ---
        bottom_group = QGroupBox("History & Favorites")
        bottom_layout = QVBoxLayout(bottom_group)
        # Search line edit
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_line = QLineEdit()
        self.search_line.setPlaceholderText("Filter history...")
        self.search_line.textChanged.connect(self._filter_history)
        search_layout.addWidget(self.search_line)
        # Show favorites only checkbox
        self.show_favorites_check = QCheckBox("Show Favorites only")
        self.show_favorites_check.stateChanged.connect(self._filter_history)
        search_layout.addWidget(self.show_favorites_check)
        bottom_layout.addLayout(search_layout)
        # List widget
        self.history_list = HistoryListWidget()
        self.history_list.item_selected_for_reuse.connect(self._on_history_reuse)
        self.history_list.item_toggle_favorite.connect(self._on_history_favorite_toggle)
        self.history_list.item_delete.connect(self._on_history_delete)
        bottom_layout.addWidget(self.history_list)
        main_layout.addWidget(bottom_group)

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.network_indicator = QLabel("Network: Checking...")
        self.status_bar.addPermanentWidget(self.network_indicator)
        self._update_network_status()
        # Timer to periodically check network
        self.network_timer = QTimer()
        self.network_timer.timeout.connect(self._update_network_status)
        self.network_timer.start(5000)  # every 5 seconds

        # Keyboard shortcuts
        self._setup_shortcuts()

        # Apply theme
        self.apply_theme("dark")

    def _create_menu_bar(self) -> None:
        """Create application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        copy_action = QAction("Copy Output", self)
        copy_action.setShortcut(QKeySequence("Ctrl+C"))
        copy_action.triggered.connect(self._on_copy_clicked)
        edit_menu.addAction(copy_action)
        clear_action = QAction("Clear", self)
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
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self) -> None:
        """Create a toolbar with common actions."""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        # Add actions (icons would be needed, we skip for simplicity)
        # We'll just add text buttons in toolbar for common actions.
        # Actually we already have main control buttons; toolbar can be minimal.
        # Add a theme toggle button.
        theme_btn = QPushButton("Toggle Theme")
        theme_btn.clicked.connect(self._toggle_theme)
        toolbar.addWidget(theme_btn)
        toolbar.addSeparator()
        # Add a network status icon placeholder
        net_icon_label = QLabel("🌐")
        toolbar.addWidget(net_icon_label)
        # We already have status bar, but it's okay.

    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts."""
        # Translate: Ctrl+Enter
        translate_shortcut = QKeySequence("Ctrl+Enter")
        translate_action = QAction(self)
        translate_action.setShortcut(translate_shortcut)
        translate_action.triggered.connect(self._on_translate_clicked)
        self.addAction(translate_action)

        # Clear: Ctrl+L already in menu
        # Copy: Ctrl+C already in menu

    def _populate_language_dropdowns(self) -> None:
        """Fill language comboboxes with supported languages."""
        service = TranslationService()
        langs = service.get_supported_languages()
        # Add "Auto Detect" for source
        self.source_lang_combo.clear()
        self.source_lang_combo.addItem("Auto Detect", "auto")
        # Add languages sorted by name
        for name, code in langs.items():
            self.source_lang_combo.addItem(name.capitalize(), code)
            self.target_lang_combo.addItem(name.capitalize(), code)

        # Set default selection from state if available
        if self.app_state:
            src = self.app_state.source_language
            tgt = self.app_state.target_language
            self._set_combo_by_code(self.source_lang_combo, src)
            self._set_combo_by_code(self.target_lang_combo, tgt)

    def _set_combo_by_code(self, combo: QComboBox, code: str) -> None:
        """Set combo selection by language code."""
        index = combo.findData(code)
        if index >= 0:
            combo.setCurrentIndex(index)
        else:
            # fallback to first (Auto Detect or English)
            combo.setCurrentIndex(0)

    def _update_char_count(self) -> None:
        """Update character counter label."""
        count = len(self.source_text_edit.toPlainText())
        self.char_counter_label.setText(f"{count} characters")

    @Slot()
    def _on_translate_clicked(self) -> None:
        """Handle translate button click."""
        source_text = self.source_text_edit.toPlainText().strip()
        if not source_text:
            QMessageBox.information(self, "Empty Input", "Please enter text to translate.")
            return
        source_lang = self.source_lang_combo.currentData()
        target_lang = self.target_lang_combo.currentData()
        # Validate: if source and target are same and source not auto, warn
        if source_lang == target_lang and source_lang != "auto":
            QMessageBox.warning(
                self,
                "Invalid Language Pair",
                "Source and target languages cannot be the same. Please select different languages or use Auto Detect."
            )
            return
        # Emit signal for controller
        self.translate_requested.emit(source_text, source_lang, target_lang)

    @Slot()
    def _on_swap_clicked(self) -> None:
        """Handle swap button click: swap languages and text."""
        # Swap language selections
        src_idx = self.source_lang_combo.currentIndex()
        tgt_idx = self.target_lang_combo.currentIndex()
        self.source_lang_combo.setCurrentIndex(tgt_idx)
        self.target_lang_combo.setCurrentIndex(src_idx)
        # Swap text: source <-> target (but target is read-only; we can set source to target's content)
        source_text = self.source_text_edit.toPlainText()
        target_text = self.target_text_edit.toPlainText()
        self.source_text_edit.setPlainText(target_text)
        self.target_text_edit.setPlainText(source_text)
        # Notify controller (so it can persist state if needed).
        self.swap_requested.emit()



    @Slot()
    def _on_clear_clicked(self) -> None:
        """Handle clear button click: clear source and target."""
        self.source_text_edit.clear()
        self.target_text_edit.clear()
        # Also clear character counter updates automatically.
        self.clear_requested.emit()



    @Slot()
    def _on_copy_clicked(self) -> None:
        """Handle copy button: copy target text to clipboard."""
        target_text = self.target_text_edit.toPlainText()
        if target_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(target_text)
            self.status_bar.showMessage("Copied to clipboard", 2000)
        else:
            QMessageBox.information(self, "Nothing to Copy", "No translation result to copy.")

    @Slot(str)
    def _filter_history(self, text: str) -> None:
        """Filter history list based on search text and favorites toggle."""
        # We need to get current history data from controller; we'll emit signal?
        # Actually, we can maintain a list of history items in the window? Better to get from controller.
        # We'll let controller update the list via a method.
        # For now, we'll assume controller manages the list content.
        # Emit so controller can refresh filtered history.
        self.history_filter_changed.emit(self.search_line.text(), self.show_favorites_check.isChecked())



    def _request_history_update(self) -> None:
        """Deprecated: controller is notified via `history_filter_changed`."""
        self.history_filter_changed.emit(self.search_line.text(), self.show_favorites_check.isChecked())



    def update_history_list(self, history_items: List[HistoryItem]) -> None:
        """Populate the history list widget with given items (after filtering)."""
        self.history_list.clear()
        for item in history_items:
            # Display format: [Favorite?] Source: ... -> Target: ...
            favorite_marker = "★ " if item.is_favorite else ""
            display_text = f"{favorite_marker}{item.source_text[:30]} → {item.target_text[:30]}"
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.UserRole, item.id)
            list_item.setData(Qt.UserRole + 1, item.source_text)
            list_item.setData(Qt.UserRole + 2, item.source_lang)
            list_item.setData(Qt.UserRole + 3, item.target_lang)
            # Optionally set tooltip with full text
            list_item.setToolTip(f"{item.source_text}\n\n→\n\n{item.target_text}")
            self.history_list.addItem(list_item)

    @Slot(int)
    def _on_history_delete(self, history_id: int) -> None:
        """Handle deletion from history list."""
        self.history_item_deleted.emit(history_id)

    @Slot(int)
    def _on_history_favorite_toggle(self, history_id: int) -> None:
        """Handle toggle favorite from history list."""
        self.history_item_toggle_favorite.emit(history_id)

    @Slot(str, str, str)
    def _on_history_reuse(self, source_text: str, source_lang: str, target_lang: str) -> None:
        """Handle reuse from history: set source text and languages."""
        self.source_text_edit.setPlainText(source_text)
        # Set combos
        self._set_combo_by_code(self.source_lang_combo, source_lang)
        self._set_combo_by_code(self.target_lang_combo, target_lang)
        # Optionally auto-translate? We'll let user click translate.
        self.status_bar.showMessage("Reused source text from history", 2000)

    @Slot()
    def _toggle_theme(self) -> None:
        """Toggle between dark and light themes."""
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self.apply_theme(new_theme)
        # Update state and save
        if self.app_state:
            self.app_state.theme = new_theme
            save_state(self.app_state.to_dict())

    def apply_theme(self, theme: str) -> None:
        """Apply the specified theme (dark/light)."""
        if theme == "dark":
            style = DARK_STYLE
        else:
            style = LIGHT_STYLE
        self.setStyleSheet(style)
        self.current_theme = theme

    def _update_network_status(self) -> None:
        """Update network indicator in status bar."""
        if is_connected_to_internet():
            self.network_indicator.setText("Network: Online ✅")
            self.network_indicator.setStyleSheet("color: #4caf50;")
        else:
            self.network_indicator.setText("Network: Offline ❌")
            self.network_indicator.setStyleSheet("color: #f44336;")

    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About CodeAlpha Translator",
            "CodeAlpha Translation Tool\n\n"
            "A desktop AI language translation application using deep-translator.\n"
            "Built with PySide6 and MVC architecture.\n\n"
            "© 2026 CodeAlpha Task 1"
        )

    def _load_initial_state(self) -> None:
        """Load application state from config file."""
        state_dict = load_state()
        self.app_state = AppState.from_dict(state_dict)
        # Apply theme
        self.apply_theme(self.app_state.theme)
        # Set window geometry
        self.resize(self.app_state.window_width, self.app_state.window_height)
        self.move(self.app_state.window_x, self.app_state.window_y)

    def closeEvent(self, event) -> None:
        """Save state on close."""
        if self.app_state:
            # Update state from UI
            self.app_state.window_width = self.width()
            self.app_state.window_height = self.height()
            self.app_state.window_x = self.x()
            self.app_state.window_y = self.y()
            self.app_state.source_language = self.source_lang_combo.currentData()
            self.app_state.target_language = self.target_lang_combo.currentData()
            # History and favorites will be saved by controller
            save_state(self.app_state.to_dict())
        event.accept()

    # Additional methods for controller to update UI
    def set_translation_result(self, source_text: str, target_text: str) -> None:
        """Display translation result in target panel."""
        self.target_text_edit.setPlainText(target_text)

    def show_error_message(self, message: str) -> None:
        """Display an error message in status bar or dialog."""
        self.status_bar.showMessage(f"Error: {message}", 5000)
        QMessageBox.warning(self, "Translation Error", message)

    def get_current_state(self) -> AppState:
        """Return the current application state (for saving)."""
        if self.app_state:
            # Update dynamic fields
            self.app_state.source_language = self.source_lang_combo.currentData()
            self.app_state.target_language = self.target_lang_combo.currentData()
            self.app_state.window_width = self.width()
            self.app_state.window_height = self.height()
            self.app_state.window_x = self.x()
            self.app_state.window_y = self.y()
        return self.app_state