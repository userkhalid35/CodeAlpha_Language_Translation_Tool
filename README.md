# CodeAlpha Language Translation Tool

[![Python 3.15](https://img.shields.io/badge/Python-3.15%20%7C%203.14%20%7C%203.13%20%7C%203.12%20%7C%203.11%20%7C%203.10-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20%28Qt%206%29-41cd52.svg)](https://wiki.qt.io/Qt_for_Python)
[![Architecture](https://img.shields.io/badge/Architecture-MVC%20%2B%20QThread-orange.svg)]()
[![License](https://img.shields.io/badge/License-MIT%20%2F%20Educational-purple.svg)]()
[![Tests](https://img.shields.io/badge/Tests-27%20Passed-brightgreen.svg)]()

A modern, production-grade desktop language translation application built with **Python 3.15**, **PySide6 (Qt 6)**, and **`deep-translator`**. 

Engineered strictly following the **Model-View-Controller (MVC)** architectural pattern, the application provides a smooth, non-blocking GUI experience with dedicated background `QThread` workers, automatic text chunking for texts up to 50,000+ characters, real-time debouncing, multi-engine rate-limit fallback, searchable history, favorites management, and dark/light themes.

---

## Table of Contents

- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Concurrency & Stability Engineering](#concurrency--stability-engineering)
- [Prerequisites](#prerequisites)
- [Quick Start (1-Click Setup & Run)](#quick-start-1-click-setup--run)
- [Batch Scripts Workflow](#batch-scripts-workflow)
- [Supported Python Versions](#supported-python-versions)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Running Automated Tests](#running-automated-tests)
- [Project Structure](#project-structure)
- [Troubleshooting & FAQ](#troubleshooting--faq)
- [License](#license)

---

## Key Features

- **100+ Languages Supported**: Translate between over 100 languages powered by Google Translate via `deep-translator`.
- **Automatic Language Detection**: Detect source language automatically or select from an alphabetically indexed list.
- **True Non-Blocking GUI (Zero Freeze)**: Translation requests execute on background `QThread` workers using Qt signal-slot mechanisms (`QueuedConnection`). The user interface remains 100% responsive without Windows "Not Responding" dialogs.
- **Automatic Text Chunking (Up to 50,000+ Characters)**: Automatically divides long texts into intelligent paragraph/sentence chunks (< 4,000 characters per chunk) so requests never violate Google's 5,000-character single-request ceiling or trigger `NotValidLength` errors.
- **Smart Rate-Limit Fallback (HTTP 429 Protection)**: Features primary execution via `deep_translator.GoogleTranslator` with automatic fallback to Google's Client API endpoint (`translate.googleapis.com`) if mobile scrape endpoints return HTTP 429 (`TooManyRequests`).
- **Debounce & Busy Lock**: Prevents thread collisions and race conditions when users rapidly trigger `Ctrl+Enter`. Disables the Translate button and indicates `"Translating..."` until the worker finishes.
- **Non-Blocking Network Health Monitoring**: Background connectivity checks monitor internet connectivity periodically without stalling the GUI event loop.
- **Searchable History**: Automatically records all translations with ISO-8601 UTC timestamps. Filter history in real time by keyword.
- **Favorites System**: Star key translations (★) and filter with a single toggle.
- **Double-Click Reuse**: Double-click any history item or use the right-click context menu to repopulate translation inputs instantly.
- **Dual Polished Themes**: Seamlessly toggle between Dark (IDE-styled) and Light themes.
- **Live Character Counter**: Real-time character count feedback as you type.
- **Persistent State**: Window geometry, active languages, theme, history, and favorites are automatically persisted to `config/settings.json` via atomic disk writes.

---

## System Architecture

The application strictly implements the **Model-View-Controller (MVC)** architectural pattern to separate concerns:

```
┌────────────────────────────────────────────────────────┐
│                   View (PySide6 GUI)                  │
│  - MainWindow: Vertical layout with source/target     │
│    panels, controls, and searchable history list       │
│  - Emits Qt signals (translate_requested, etc.)       │
└───────────────────────────▲────────────────────────────┘
                            │ Qt Signals & Slots
┌───────────────────────────▼────────────────────────────┐
│              Controller (MainController)               │
│  - Debounce lock (is_translating flag)                 │
│  - Strong worker/thread instance references            │
│  - Spawns and manages non-blocking QThread workers    │
│  - Syncs AppState and coordinates atomic persistence   │
└───────────────────▲─────────────────▲──────────────────┘
                    │                 │
┌───────────────────▼───────┐ ┌───────▼──────────────────┐
│          Models           │ │         Services         │
│  - HistoryItem (dataclass)│ │  - TranslationService    │
│  - AppState (dataclass)   │ │  - TranslationWorker     │
│  - config/settings.json   │ │  - Text chunking & HTTP  │
│  - utils/helpers.py       │ │    session pooling       │
└───────────────────────────┘ └──────────────────────────┘
```

---

## Concurrency & Stability Engineering

### 1. True Non-Blocking `QThread` Workers
Translation requests and network connectivity checks **never** run on the main Qt GUI thread:
- Neither `thread.wait()` nor `worker.run()` are ever called directly during request dispatch; all threads are started via `thread.start()`.
- Strong instance references (`self.worker`, `self.thread`) are maintained on `MainController` to prevent Python's garbage collector from destroying threads mid-flight.
- Communication between threads utilizes Qt's thread-safe signal/slot mechanism (`finished` and `error` signals).

### 2. Auto-Chunking Engine for Large Inputs
Google Translate imposes an API limit of 5,000 characters per single request. The auto-chunking engine (`split_text_into_chunks`):
- Splits long texts by paragraphs (`\n\n`), sentences (`. `, `! `, `? `), or words.
- Guarantees each chunk remains `<= 4000` characters.
- Translates chunks sequentially within the background worker thread.
- Merges the chunks seamlessly with identical formatting.

### 3. Dual-Engine HTTP 429 Fallback
When data center or cloud networks encounter temporary rate limits on Google Translate's mobile web endpoint:
- The worker catches `TooManyRequests` (HTTP 429).
- Seamlessly falls back to Google's Client API endpoint (`https://translate.googleapis.com/translate_a/single?client=gtx`).
- Employs persistent connection pooling (`requests.Session`) with a 10-second timeout.

---

## Prerequisites

- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **Python**: Python 3.10 to 3.15 (64-bit) installed from [python.org](https://www.python.org/downloads/)
  - *Important*: When installing Python, make sure **"Add python.exe to PATH"** is checked.
- **Git**: Git for Windows installed.
- **Internet Connection**: Required for live translation API requests.

---

## Quick Start (1-Click Setup & Run)

Virtual environments are **never** committed to Git. Anyone cloning the repository can generate an isolated `.venv` and run the app with a single click.

### ⚡ 1-Click Setup & Launch (Fastest)

Open **Command Prompt (cmd)** or **PowerShell** and run:

```cmd
git clone https://github.com/userkhalid35/CodeAlpha_Language_Translation_Tool.git
cd CodeAlpha_Language_Translation_Tool
setup_and_run.bat
```
*(In PowerShell: `.\setup_and_run.bat`)*

`setup_and_run.bat` automatically configures the Python virtual environment, installs dependencies, and launches the desktop app.

---

## Batch Scripts Workflow

| Script | Purpose | Command |
| :--- | :--- | :--- |
| **`setup_and_run.bat`** | **1-Click**: Checks Python, configures `.venv`, installs requirements, and launches app. | `setup_and_run.bat` |
| **`setup.bat`** | Configures isolated `.venv` and installs dependencies from `requirements.txt`. | `setup.bat` |
| **`run.bat`** | Launches the application using `.venv\Scripts\python.exe`. Auto-runs setup if `.venv` is missing. | `run.bat` |

### Manual Terminal Setup (Alternative)

If you prefer using manual shell commands instead of batch scripts:

```powershell
# 1. Create virtual environment
python -m venv .venv

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Run the application
python main.py
```

---

## Supported Python Versions

| Python Version | Status | Notes |
| :--- | :--- | :--- |
| **Python 3.15** | ✅ **Fully Supported** | Verified with PySide6 6.12.0+ (Windows 64-bit) |
| **Python 3.14** | ✅ **Supported** | Compatible with PySide6 6.10.0+ |
| **Python 3.13** | ✅ **Supported** | Compatible with PySide6 6.8.0.2+ |
| **Python 3.12** | ✅ **Supported** | Compatible with PySide6 6.6.0+ |
| **Python 3.11** | ✅ **Supported** | Compatible with PySide6 6.4.0+ |
| **Python 3.10** | ✅ **Supported** | Minimum supported version |

---

## Keyboard Shortcuts

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| **`Ctrl + Enter`** | **Translate** | Translates current source text into target language |
| **`Ctrl + L`** | **Clear All** | Clears both source and target text areas |
| **`Ctrl + Shift + C`** | **Copy Output** | Copies translated text to clipboard |
| **`Ctrl + T`** | **Toggle Theme** | Swaps between Dark and Light themes |
| **`Enter` on keypad** | **Translate** | Keypad Enter also triggers translation |

---

## Running Automated Tests

The repository includes a comprehensive automated test suite of **27 unit and integration tests** covering models, helpers, text chunking, debounce locks, offscreen GUI interactions, and fallback services.

To execute the test suite:

```cmd
.venv\Scripts\python.exe -m unittest discover -v -s tests -p "test_*.py"
```

Expected result:
```text
Ran 27 tests in ~1.0s
OK
```

---

## Project Structure

```text
CodeAlpha_Language_Translation_Tool/
├── config/
│   └── settings.json           # User configuration (theme, window geometry, history, favorites)
├── controllers/
│   └── main_controller.py      # MVC Controller: binds UI signals, background threads, debounce lock
├── models/
│   └── translation_model.py    # MVC Models: HistoryItem and AppState dataclasses
├── services/
│   └── translation_service.py  # QThread worker, chunking engine, session pooling, Google fallback
├── tests/
│   └── test_translation_app.py # Automated test suite (27 unit and integration tests)
├── ui/
│   ├── main_window.py          # PySide6 main window layout, panels, shortcuts, and dialogs
│   └── styles.py               # Modern Dark and Light CSS/QSS stylesheets
├── utils/
│   └── helpers.py              # Atomic config I/O, network check, timezone-aware UTC dates
├── main.py                     # Entry point: bootstrap, logging, version guard
├── requirements.txt            # Dependency specifications with Python 3.15 support
├── setup.bat                   # Automated Windows setup script
├── run.bat                     # Application launch script
├── setup_and_run.bat           # Combined 1-click setup and launch script
├── .gitignore                  # Git exclusions (.venv, caches, logs, temp files)
├── TODO.md                     # Development tracking and milestones
└── README.md                   # Project documentation
```

---

## Troubleshooting & FAQ

### 1. `[ERROR] No supported Python installation found!`
- **Cause**: Python is either not installed or not added to your Windows `PATH` environment variable.
- **Solution**: Download Python 3.15 from [python.org](https://www.python.org/downloads/). During installation, ensure you select **"Add python.exe to PATH"**.

### 2. `Network: Offline ❌`
- **Cause**: Your machine is disconnected from the internet, or a corporate firewall/VPN blocks outbound DNS/HTTPS requests.
- **Solution**: Verify your internet connection. The app continues to provide full offline language lists, but translation requires network connectivity.

### 3. `Source and target languages cannot be identical`
- **Cause**: The same language was selected in both dropdowns.
- **Solution**: Select different languages or set the source dropdown to **Auto Detect**.

### 4. Resetting Application Settings
- **Procedure**: If you wish to reset your configuration, history, and window geometry to fresh factory defaults, delete `config/settings.json`. The application will regenerate a clean settings file automatically on the next launch.

---

## License

Created for the **CodeAlpha Software Engineering Internship**. Free to use and modify for educational purposes.