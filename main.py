"""
Application entry point.

Bootstrap the application, set up logging, and launch the main window.
"""

import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from ui.main_window import MainWindow
from controllers.main_controller import MainController


def setup_logging() -> None:
    """Configure logging for the application."""
    log_file = Path("translation_app.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    # Reduce noisy logs from deep_translator/urllib3
    logging.getLogger("deep_translator").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def main() -> None:
    """Application entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting CodeAlpha Translator")

    app = QApplication(sys.argv)
    app.setApplicationName("CodeAlpha Translator")
    app.setOrganizationName("CodeAlpha")
    app.setStyle("Fusion")  # Cross-platform consistent style

    # Create main window
    window = MainWindow()
    # Create controller
    controller = MainController(window)

    # Connect controller save on window close
    def on_close():
        controller.save_state()
        logger.info("Application closed")
    window.destroyed.connect(on_close)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()