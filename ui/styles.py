"""
Stylesheets for dark and light themes.

These styles provide a premium, clean, IDE-like aesthetic.
"""

DARK_STYLE = """
    QMainWindow, QDialog {
        background-color: #1e1e1e;
        color: #d4d4d4;
    }
    QMenuBar {
        background-color: #2d2d2d;
        color: #d4d4d4;
        border-bottom: 1px solid #3c3c3c;
    }
    QMenuBar::item {
        background-color: transparent;
        padding: 4px 10px;
    }
    QMenuBar::item:selected {
        background-color: #3c3c3c;
    }
    QMenu {
        background-color: #2d2d2d;
        border: 1px solid #3c3c3c;
    }
    QMenu::item {
        padding: 6px 20px;
    }
    QMenu::item:selected {
        background-color: #3c3c3c;
    }
    QToolBar {
        background-color: #2d2d2d;
        border: none;
        spacing: 8px;
        padding: 4px;
    }
    QLabel {
        color: #d4d4d4;
    }
    QGroupBox {
        border: 1px solid #3c3c3c;
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: #d4d4d4;
    }
    QPushButton {
        background-color: #3c3c3c;
        border: 1px solid #3c3c3c;
        border-radius: 4px;
        padding: 6px 16px;
        color: #d4d4d4;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #4c4c4c;
        border-color: #4c4c4c;
    }
    QPushButton:pressed {
        background-color: #2c2c2c;
    }
    QPushButton:disabled {
        color: #6c6c6c;
        background-color: #2c2c2c;
    }
    QComboBox {
        background-color: #2d2d2d;
        border: 1px solid #3c3c3c;
        border-radius: 4px;
        padding: 5px 8px;
        color: #d4d4d4;
    }
    QComboBox:hover {
        border-color: #4c4c4c;
    }
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    QComboBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 4px solid #d4d4d4;
        margin-right: 6px;
    }
    QComboBox QAbstractItemView {
        background-color: #2d2d2d;
        border: 1px solid #3c3c3c;
        selection-background-color: #3c3c3c;
        color: #d4d4d4;
    }
    QTextEdit, QPlainTextEdit {
        background-color: #252525;
        border: 1px solid #3c3c3c;
        border-radius: 4px;
        color: #d4d4d4;
        padding: 8px;
        font-family: "Consolas", "Courier New", monospace;
        font-size: 12pt;
    }
    QTextEdit:focus, QPlainTextEdit:focus {
        border-color: #4c4c4c;
    }
    QLineEdit {
        background-color: #2d2d2d;
        border: 1px solid #3c3c3c;
        border-radius: 4px;
        padding: 5px 8px;
        color: #d4d4d4;
    }
    QLineEdit:focus {
        border-color: #4c4c4c;
    }
    QScrollBar:vertical {
        background: #252525;
        width: 12px;
        border-radius: 6px;
    }
    QScrollBar::handle:vertical {
        background: #3c3c3c;
        border-radius: 6px;
        min-height: 20px;
    }
    QScrollBar::handle:vertical:hover {
        background: #4c4c4c;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        border: none;
        background: none;
    }
    QScrollBar:horizontal {
        background: #252525;
        height: 12px;
        border-radius: 6px;
    }
    QScrollBar::handle:horizontal {
        background: #3c3c3c;
        border-radius: 6px;
        min-width: 20px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #4c4c4c;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        border: none;
        background: none;
    }
    QStatusBar {
        background-color: #1e1e1e;
        color: #d4d4d4;
        border-top: 1px solid #3c3c3c;
    }
    QListWidget {
        background-color: #252525;
        border: 1px solid #3c3c3c;
        border-radius: 4px;
        color: #d4d4d4;
        padding: 4px;
    }
    QListWidget::item {
        padding: 6px;
        border-bottom: 1px solid #2d2d2d;
    }
    QListWidget::item:selected {
        background-color: #3c3c3c;
    }
    QListWidget::item:hover {
        background-color: #2d2d2d;
    }
    QCheckBox {
        color: #d4d4d4;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid #3c3c3c;
        border-radius: 3px;
        background: #2d2d2d;
    }
    QCheckBox::indicator:checked {
        background: #3c3c3c;
    }
"""

LIGHT_STYLE = """
    QMainWindow, QDialog {
        background-color: #f3f3f3;
        color: #333333;
    }
    QMenuBar {
        background-color: #e8e8e8;
        color: #333333;
        border-bottom: 1px solid #cccccc;
    }
    QMenuBar::item {
        background-color: transparent;
        padding: 4px 10px;
    }
    QMenuBar::item:selected {
        background-color: #d0d0d0;
    }
    QMenu {
        background-color: #f9f9f9;
        border: 1px solid #cccccc;
    }
    QMenu::item {
        padding: 6px 20px;
    }
    QMenu::item:selected {
        background-color: #d0d0d0;
    }
    QToolBar {
        background-color: #e8e8e8;
        border: none;
        spacing: 8px;
        padding: 4px;
    }
    QLabel {
        color: #333333;
    }
    QGroupBox {
        border: 1px solid #cccccc;
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: #333333;
    }
    QPushButton {
        background-color: #e8e8e8;
        border: 1px solid #cccccc;
        border-radius: 4px;
        padding: 6px 16px;
        color: #333333;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #d8d8d8;
        border-color: #bbbbbb;
    }
    QPushButton:pressed {
        background-color: #c8c8c8;
    }
    QPushButton:disabled {
        color: #999999;
        background-color: #e0e0e0;
    }
    QComboBox {
        background-color: #ffffff;
        border: 1px solid #cccccc;
        border-radius: 4px;
        padding: 5px 8px;
        color: #333333;
    }
    QComboBox:hover {
        border-color: #aaaaaa;
    }
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    QComboBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 4px solid #333333;
        margin-right: 6px;
    }
    QComboBox QAbstractItemView {
        background-color: #ffffff;
        border: 1px solid #cccccc;
        selection-background-color: #d0d0d0;
        color: #333333;
    }
    QTextEdit, QPlainTextEdit {
        background-color: #ffffff;
        border: 1px solid #cccccc;
        border-radius: 4px;
        color: #333333;
        padding: 8px;
        font-family: "Consolas", "Courier New", monospace;
        font-size: 12pt;
    }
    QTextEdit:focus, QPlainTextEdit:focus {
        border-color: #999999;
    }
    QLineEdit {
        background-color: #ffffff;
        border: 1px solid #cccccc;
        border-radius: 4px;
        padding: 5px 8px;
        color: #333333;
    }
    QLineEdit:focus {
        border-color: #999999;
    }
    QScrollBar:vertical {
        background: #e8e8e8;
        width: 12px;
        border-radius: 6px;
    }
    QScrollBar::handle:vertical {
        background: #cccccc;
        border-radius: 6px;
        min-height: 20px;
    }
    QScrollBar::handle:vertical:hover {
        background: #bbbbbb;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        border: none;
        background: none;
    }
    QScrollBar:horizontal {
        background: #e8e8e8;
        height: 12px;
        border-radius: 6px;
    }
    QScrollBar::handle:horizontal {
        background: #cccccc;
        border-radius: 6px;
        min-width: 20px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #bbbbbb;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        border: none;
        background: none;
    }
    QStatusBar {
        background-color: #f3f3f3;
        color: #333333;
        border-top: 1px solid #cccccc;
    }
    QListWidget {
        background-color: #ffffff;
        border: 1px solid #cccccc;
        border-radius: 4px;
        color: #333333;
        padding: 4px;
    }
    QListWidget::item {
        padding: 6px;
        border-bottom: 1px solid #e8e8e8;
    }
    QListWidget::item:selected {
        background-color: #d0d0d0;
    }
    QListWidget::item:hover {
        background-color: #e0e0e0;
    }
    QCheckBox {
        color: #333333;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid #cccccc;
        border-radius: 3px;
        background: #ffffff;
    }
    QCheckBox::indicator:checked {
        background: #cccccc;
    }
"""