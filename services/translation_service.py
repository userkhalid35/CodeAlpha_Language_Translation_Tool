"""
Translation service module.

Handles interaction with translation APIs, dynamic language loading,
and asynchronous translation via QThread.
"""

import logging
import sys
from typing import Optional, Dict, List, Tuple
from PySide6.QtCore import QObject, QThread, Signal, Slot
from deep_translator import GoogleTranslator
from deep_translator.exceptions import (
    NotValidPayload,
    TooManyRequests,
    TranslationNotFound,
    RequestError,
)

logger = logging.getLogger(__name__)


class TranslationWorker(QObject):
    """
    Worker object to run translation in a separate thread.
    """
    finished = Signal(str, str)  # source_text, translated_text
    error = Signal(str)          # error message

    def __init__(self, source_text: str, source_lang: str, target_lang: str) -> None:
        super().__init__()
        self.source_text = source_text
        self.source_lang = source_lang
        self.target_lang = target_lang

    @Slot()
    def run(self) -> None:
        """
        Perform translation and emit result or error.
        """
        try:
            # GoogleTranslator expects source and target codes.
            # 'auto' is acceptable.
            translator = GoogleTranslator(
                source=self.source_lang, target=self.target_lang
            )
            # Translate
            result = translator.translate(self.source_text)
            self.finished.emit(self.source_text, result)
        except (NotValidPayload, TooManyRequests, TranslationNotFound, RequestError) as e:
            error_msg = f"Translation error: {str(e)}"
            logger.error(error_msg)
            self.error.emit(error_msg)
        except Exception as e:
            # Catch any other unexpected errors (network, server, etc.)
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            self.error.emit(error_msg)


class TranslationService:
    """
    Service class for translation operations and language management.
    """

    _instance = None
    _supported_languages: Optional[Dict[str, str]] = None

    def __new__(cls) -> "TranslationService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_supported_languages(cls) -> Dict[str, str]:
        """
        Load and cache supported languages from deep_translator.

        Returns:
            Dict mapping language names to codes.
        """
        if cls._supported_languages is None:
            try:
                # deep-translator's BaseTranslator.get_supported_languages is an instance method.
                translator = GoogleTranslator(source='auto', target='en')
                langs = translator.get_supported_languages(as_dict=True)

                # The dict is {name: code} or {code: name}? Actually:
                # In deep_translator, it returns {language_name: language_code}
                # Example: {"english": "en", "spanish": "es", ...}
                # We'll keep as is and sort by name.
                cls._supported_languages = dict(sorted(langs.items()))
            except Exception as e:
                logger.error(f"Failed to load languages: {e}")
                # Fallback to a minimal set
                cls._supported_languages = {
                    "english": "en",
                    "spanish": "es",
                    "french": "fr",
                    "german": "de",
                    "chinese (simplified)": "zh-CN",
                    "japanese": "ja",
                    "russian": "ru",
                    "arabic": "ar",
                }
        return cls._supported_languages

    @classmethod
    def get_language_codes(cls) -> List[str]:
        """Return list of language codes sorted by name."""
        return list(cls.get_supported_languages().values())

    @classmethod
    def get_language_names(cls) -> List[str]:
        """Return list of language names sorted alphabetically."""
        return list(cls.get_supported_languages().keys())

    @classmethod
    def get_language_code_from_name(cls, name: str) -> Optional[str]:
        """Get code for a given language name."""
        return cls.get_supported_languages().get(name)

    @classmethod
    def get_language_name_from_code(cls, code: str) -> Optional[str]:
        """Get name for a given language code."""
        for name, c in cls.get_supported_languages().items():
            if c == code:
                return name
        return None

    @classmethod
    def translate_async(
        cls,
        source_text: str,
        source_lang: str,
        target_lang: str,
        callback_on_finished: callable,
        callback_on_error: callable,
    ) -> QThread:
        """
        Perform translation asynchronously using QThread.

        Args:
            source_text: Text to translate.
            source_lang: Source language code.
            target_lang: Target language code.
            callback_on_finished: Function to call on success (src, target).
            callback_on_error: Function to call on error (error_msg).

        Returns:
            QThread instance (for tracking).
        """
        thread = QThread()
        worker = TranslationWorker(source_text, source_lang, target_lang)
        worker.moveToThread(thread)

        # Ensure thread quits only after worker emits a terminal signal.
        def _on_finished(src_text: str, translated_text: str) -> None:
            try:
                callback_on_finished(src_text, translated_text)
            finally:
                if thread.isRunning():
                    thread.quit()

        def _on_error(error_msg: str) -> None:
            try:
                callback_on_error(error_msg)
            finally:
                if thread.isRunning():
                    thread.quit()

        worker.finished.connect(_on_finished)
        worker.error.connect(_on_error)

        thread.started.connect(worker.run)

        # Cleanup
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        # Keep a reference to avoid premature destruction
        thread._worker = worker  # type: ignore[attr-defined]

        thread.start()
        return thread
