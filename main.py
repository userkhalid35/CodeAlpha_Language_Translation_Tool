"""
Application entry point for CodeAlpha Translation Tool.

Bootstrap the application, configure logging, initialize the MVC architecture,
and launch the PySide6 main window.
"""

import logging
from pathlib import Path
import sys

# Minimum supported Python version check
if sys.version_info < (3, 10):  # noqa: UP036
    sys.stderr.write(
        f"Error: Python {sys.version_info.major}.{sys.version_info.minor} is not supported. "
        "CodeAlpha Translator requires Python 3.10 to 3.15.\n"
    )
    sys.exit(1)

# Ensure project root is in sys.path for robust imports from any cwd
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pyrefly: ignore[missing-import]
from PySide6.QtWidgets import QApplication

from controllers.main_controller import MainController
from ui.main_window import MainWindow


def setup_logging() -> None:
    """Configure application logging with safe Unicode handling."""
    log_file = Path("translation_app.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8", mode="a"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    # Suppress verbose HTTP logs
    logging.getLogger("deep_translator").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def main() -> None:
    """Application entry point."""
    setup_logging()
    logger = logging.getLogger("CodeAlphaTranslator")
    logger.info("Starting CodeAlpha Translation Tool")

    app = QApplication(sys.argv)
    app.setApplicationName("CodeAlpha Translator")
    app.setOrganizationName("CodeAlpha")
    app.setStyle("Fusion")  # Modern cross-platform style

    # Initialize MVC components
    window = MainWindow()
    controller = MainController(window)

    # Ensure application state is saved cleanly on exit
    app.aboutToQuit.connect(controller.save_state)

    # Allow automated smoke test / verification without hanging GUI event loop
    if "--test-init" in sys.argv:
        logger.info("Application initialized successfully in test mode.")
        print("Application initialized successfully in test mode.")
        return

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()