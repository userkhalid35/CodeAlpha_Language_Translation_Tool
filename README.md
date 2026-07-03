# CodeAlpha Translation Tool

A production-grade desktop AI language translation application built with Python, PySide6, and the MVC architectural pattern. It provides a clean, IDE-like interface for translating text using the `deep-translator` library (Google Translate backend). Features include asynchronous translation, language detection, history with search and favorites, theme switching, and persistent state.

## Features

- **Translate text** between 100+ languages with automatic source language detection.
- **Async translation** using QThread – GUI remains responsive.
- **Dark/Light themes** with premium styles.
- **History & Favorites**: Store, search, delete, and reuse past translations.
- **Swap languages** and text instantly.
- **Copy translated text** to clipboard.
- **Keyboard shortcuts**: `Ctrl+Enter` (Translate), `Ctrl+L` (Clear), `Ctrl+C` (Copy Output).
- **Persistent state**: Window size, position, language selections, history, and favorites saved in `config/settings.json`.
- **Network status indicator** in status bar.
- **Error handling** with user-friendly messages.

## Architecture

The application strictly follows the Model-View-Controller pattern:

- **Model** (`models/translation_model.py`): Data classes (`HistoryItem`, `AppState`).
- **View** (`ui/main_window.py` + `ui/styles.py`): PySide6 widgets and stylesheets.
- **Controller** (`controllers/main_controller.py`): Binds UI events to services and models.
- **Service** (`services/translation_service.py`): Manages translation API and async workers.
- **Utilities** (`utils/helpers.py`): File I/O, network check, sanitization.
- **Entry point** (`main.py`): App bootstrap, logging, and launch.

## Installation

1. Ensure Python 3.12+ is installed.
2. Clone or download the project files.
3. Install dependencies:

```bash
pip install -r requirements.txt