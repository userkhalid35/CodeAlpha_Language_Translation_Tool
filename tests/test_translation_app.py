"""
Automated unit and integration test suite for CodeAlpha Translation Tool.

Tests cover:
- Data models (HistoryItem, AppState) and serialization
- Helpers (date formatting, config I/O, atomic persistence, network check)
- Translation service (language caching, translation worker, async QThread)
- Main window & controller (offscreen GUI initialization, swap logic, filtering, state save)
"""

import os
import sys
import unittest
import tempfile
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from models.translation_model import HistoryItem, AppState
from utils.helpers import (
    load_state, save_state, get_current_time_iso, sanitize_text, is_connected_to_internet
)
from services.translation_service import (
    TranslationService, TranslationWorker, FALLBACK_LANGUAGES, split_text_into_chunks
)


class TestTranslationModels(unittest.TestCase):
    """Test data models and serialization."""

    def test_history_item_roundtrip(self):
        item = HistoryItem(
            id=1,
            timestamp="2026-10-19T03:00:00Z",
            source_lang="en",
            target_lang="es",
            source_text="Hello",
            target_text="Hola",
            is_favorite=True
        )
        d = item.to_dict()
        self.assertEqual(d["id"], 1)
        self.assertTrue(d["is_favorite"])

        item_back = HistoryItem.from_dict(d)
        self.assertEqual(item_back.id, 1)
        self.assertEqual(item_back.source_text, "Hello")
        self.assertEqual(item_back.target_text, "Hola")
        self.assertTrue(item_back.is_favorite)

    def test_history_item_defensive_from_dict(self):
        # Empty dict fallback
        item = HistoryItem.from_dict({})
        self.assertEqual(item.id, 0)
        self.assertEqual(item.source_lang, "auto")
        self.assertEqual(item.target_lang, "en")
        self.assertFalse(item.is_favorite)

        # None / invalid type fallback
        item_none = HistoryItem.from_dict(None)
        self.assertEqual(item_none.id, 0)

    def test_app_state_roundtrip(self):
        item = HistoryItem(
            id=1,
            timestamp="2026-10-19T03:00:00Z",
            source_lang="auto",
            target_lang="fr",
            source_text="Good morning",
            target_text="Bonjour",
            is_favorite=False
        )
        state = AppState(
            theme="light",
            window_width=1200,
            window_height=800,
            window_x=50,
            window_y=50,
            source_language="auto",
            target_language="fr",
            history=[item],
            favorites=[]
        )
        data = state.to_dict()
        self.assertEqual(data["theme"], "light")
        self.assertEqual(len(data["history"]), 1)

        loaded = AppState.from_dict(data)
        self.assertEqual(loaded.theme, "light")
        self.assertEqual(loaded.window_width, 1200)
        self.assertEqual(len(loaded.history), 1)
        self.assertEqual(loaded.history[0].source_text, "Good morning")

    def test_app_state_defensive_bounds(self):
        bad_data = {
            "window_width": 10,
            "window_height": -20,
            "window_x": -100,
            "window_y": -50,
            "history": "not-a-list"
        }
        state = AppState.from_dict(bad_data)
        self.assertGreaterEqual(state.window_width, 600)
        self.assertGreaterEqual(state.window_height, 450)
        self.assertGreaterEqual(state.window_x, 0)
        self.assertGreaterEqual(state.window_y, 0)
        self.assertEqual(state.history, [])


class TestHelpers(unittest.TestCase):
    """Test helper functions."""

    def test_get_current_time_iso(self):
        ts = get_current_time_iso()
        self.assertTrue(ts.endswith("Z"))
        self.assertIn("T", ts)
        self.assertEqual(len(ts), 20)  # YYYY-MM-DDTHH:MM:SSZ

    def test_sanitize_text(self):
        self.assertEqual(sanitize_text("  hello world  \n"), "hello world")
        self.assertEqual(sanitize_text(""), "")
        self.assertEqual(sanitize_text(None), "")

    def test_save_and_load_state_atomic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_config = os.path.join(tmpdir, "config", "settings.json")
            with patch("utils.helpers.CONFIG_PATH", test_config):
                init_state = load_state()
                self.assertEqual(init_state["theme"], "dark")
                self.assertFalse(os.path.exists(test_config))

                init_state["theme"] = "light"
                init_state["source_language"] = "de"
                save_state(init_state)

                self.assertTrue(os.path.exists(test_config))
                reloaded = load_state()
                self.assertEqual(reloaded["theme"], "light")
                self.assertEqual(reloaded["source_language"], "de")

    def test_load_state_corrupted_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_config = os.path.join(tmpdir, "settings.json")
            with open(test_config, "w", encoding="utf-8") as f:
                f.write("{ INVALID JSON CONTENT :::")

            with patch("utils.helpers.CONFIG_PATH", test_config):
                state = load_state()
                self.assertEqual(state["theme"], "dark")
                self.assertEqual(state["window_width"], 1024)

    def test_is_connected_to_internet(self):
        result = is_connected_to_internet(timeout=1)
        self.assertIsInstance(result, bool)


class TestTranslationService(unittest.TestCase):
    """Test translation service and languages."""

    def test_supported_languages_non_empty(self):
        langs = TranslationService.get_supported_languages()
        self.assertIsInstance(langs, dict)
        self.assertGreater(len(langs), 50)
        self.assertIn("english", langs)
        self.assertIn("spanish", langs)
        self.assertEqual(langs["english"], "en")

    def test_code_and_name_conversions(self):
        code = TranslationService.get_language_code_from_name("english")
        self.assertEqual(code, "en")

        name = TranslationService.get_language_name_from_code("en")
        self.assertEqual(name, "english")

        invalid = TranslationService.get_language_code_from_name("non_existent_lang_xyz")
        self.assertIsNone(invalid)

    @patch("services.translation_service.GoogleTranslator")
    def test_translation_worker_success(self, mock_translator_cls):
        mock_instance = MagicMock()
        mock_instance.translate.return_value = "Hola"
        mock_translator_cls.return_value = mock_instance

        worker = TranslationWorker("Hello", "en", "es")
        results = []
        worker.finished.connect(lambda s, t: results.append((s, t)))
        worker.run()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], ("Hello", "Hola"))

    @patch("services.translation_service.GoogleTranslator")
    def test_translation_worker_error(self, mock_translator_cls):
        mock_instance = MagicMock()
        mock_instance.translate.side_effect = Exception("API rate limited")
        mock_translator_cls.return_value = mock_instance

        worker = TranslationWorker("Hello", "en", "es")
        errors = []
        worker.error.connect(lambda msg: errors.append(msg))
        worker.run()

        self.assertEqual(len(errors), 1)
        self.assertIn("Unexpected translation error", errors[0])


class TestGUIAndController(unittest.TestCase):
    """Integration test for GUI widgets and MVC controller in offscreen mode."""

    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(["test_app"])

    def setUp(self):
        from ui.main_window import MainWindow
        from controllers.main_controller import MainController
        from PySide6.QtWidgets import QMessageBox

        # Mock modal dialogs to prevent blocking headless test runners
        self.patcher_info = patch.object(QMessageBox, "information", return_value=QMessageBox.Ok)
        self.patcher_warn = patch.object(QMessageBox, "warning", return_value=QMessageBox.Ok)
        self.patcher_about = patch.object(QMessageBox, "about", return_value=None)
        self.patcher_info.start()
        self.patcher_warn.start()
        self.patcher_about.start()

        self.window = MainWindow()
        self.controller = MainController(self.window)
        # Clear existing history for test isolation
        self.controller.app_state.history = []
        self.controller._refresh_history_list()

    def tearDown(self):
        self.patcher_info.stop()
        self.patcher_warn.stop()
        self.patcher_about.stop()
        self.window.close()

    def test_window_initialization(self):
        self.assertEqual(self.window.windowTitle(), "CodeAlpha Translator")
        self.assertGreater(self.window.source_lang_combo.count(), 10)
        self.assertGreater(self.window.target_lang_combo.count(), 10)

    def test_character_counter(self):
        self.window.source_text_edit.setPlainText("Hello World!")
        self.assertEqual(self.window.char_counter_label.text(), "12 characters")

    def test_clear_button(self):
        self.window.source_text_edit.setPlainText("Some text")
        self.window.target_text_edit.setPlainText("Quelque texte")
        self.window._on_clear_clicked()
        self.assertEqual(self.window.source_text_edit.toPlainText(), "")
        self.assertEqual(self.window.target_text_edit.toPlainText(), "")

    def test_swap_with_auto_detect_blocked(self):
        self.window._set_combo_by_code(self.window.source_lang_combo, "auto")
        self.window._set_combo_by_code(self.window.target_lang_combo, "es")
        self.window._on_swap_clicked()

        self.assertEqual(self.window.source_lang_combo.currentData(), "auto")
        self.assertEqual(self.window.target_lang_combo.currentData(), "es")

    def test_swap_languages_and_text(self):
        self.window._set_combo_by_code(self.window.source_lang_combo, "en")
        self.window._set_combo_by_code(self.window.target_lang_combo, "es")
        self.window.source_text_edit.setPlainText("Hello")
        self.window.target_text_edit.setPlainText("Hola")

        self.window._on_swap_clicked()

        self.assertEqual(self.window.source_lang_combo.currentData(), "es")
        self.assertEqual(self.window.target_lang_combo.currentData(), "en")
        self.assertEqual(self.window.source_text_edit.toPlainText(), "Hola")
        self.assertEqual(self.window.target_text_edit.toPlainText(), "Hello")

    def test_theme_toggle(self):
        initial_theme = self.window.current_theme
        self.window._toggle_theme()
        expected = "light" if initial_theme == "dark" else "dark"
        self.assertEqual(self.window.current_theme, expected)

    def test_history_filtering_and_favorite(self):
        self.controller._add_history_item("Apple", "Manzana", "en", "es")
        self.controller._add_history_item("Car", "Coche", "en", "es")
        self.controller._refresh_history_list()
        self.assertEqual(self.window.history_list.count(), 2)

        # Toggle favorite on first item
        item_id = self.controller.app_state.history[0].id
        self.controller.handle_history_toggle_favorite(item_id)
        self.assertTrue(self.controller.app_state.history[0].is_favorite)

        # Filter by search
        self.window.search_line.setText("Apple")
        self.assertEqual(self.window.history_list.count(), 1)

        # Clear search
        self.window.search_line.setText("")
        self.assertEqual(self.window.history_list.count(), 2)

        # Filter favorites only
        self.window.show_favorites_check.setChecked(True)
        self.assertEqual(self.window.history_list.count(), 1)

        # Delete item
        self.controller.handle_history_delete(item_id)
        self.assertEqual(len(self.controller.app_state.history), 1)

    def test_history_double_click_reuse(self):
        self.controller._add_history_item("Test Reuse", "Tester la réutilisation", "en", "fr")
        self.controller._refresh_history_list()

        list_item = self.window.history_list.item(0)
        self.assertIsNotNone(list_item)

        self.window.history_list._on_item_double_clicked(list_item)
        self.assertEqual(self.window.source_text_edit.toPlainText(), "Test Reuse")
        self.assertEqual(self.window.source_lang_combo.currentData(), "en")
        self.assertEqual(self.window.target_lang_combo.currentData(), "fr")

    def test_session_reuse(self):
        import requests
        session1 = TranslationService.get_session()
        session2 = TranslationService.get_session()
        self.assertIsInstance(session1, requests.Session)
        self.assertIs(session1, session2)
        self.assertIn("User-Agent", session1.headers)

    def test_controller_cleanup_active_thread(self):
        from PySide6.QtCore import QThread
        mock_thread = MagicMock(spec=QThread)
        mock_thread.isRunning.return_value = True
        mock_thread.wait.return_value = True
        self.controller.current_translation_thread = mock_thread

        self.controller.cleanup()
        mock_thread.quit.assert_called_once()
        mock_thread.wait.assert_called_once()
        self.assertIsNone(self.controller.current_translation_thread)

    def test_ui_set_translating_state(self):
        self.window.set_translating(True)
        self.assertFalse(self.window.translate_btn.isEnabled())
        self.assertEqual(self.window.translate_btn.text(), "Translating...")

        self.window.set_translating(False)
        self.assertTrue(self.window.translate_btn.isEnabled())
        self.assertEqual(self.window.translate_btn.text(), "Translate (Ctrl+Enter)")

    def test_debounce_lock_prevents_duplicate_requests(self):
        self.controller.is_translating = True
        with patch.object(self.controller, "thread", None):
            self.controller.handle_translate_request("Some text", "en", "es")
            # Thread should not have been spawned because is_translating was True
            self.assertIsNone(self.controller.thread)

    def test_split_text_into_chunks_50000_chars(self):
        # Generate 50,000 characters of text with paragraphs
        paragraph = "This is a sentence that will be repeated to test automatic chunking logic. " * 15
        full_text = "\n\n".join([paragraph for _ in range(50)])
        self.assertGreater(len(full_text), 50000)

        chunks = split_text_into_chunks(full_text, max_chunk_size=4000)
        self.assertGreater(len(chunks), 10)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 4000)
            self.assertTrue(len(chunk.strip()) > 0)

    @patch("services.translation_service.GoogleTranslator")
    def test_google_client_api_fallback_on_too_many_requests(self, mock_translator_cls):
        from deep_translator.exceptions import TooManyRequests

        mock_instance = MagicMock()
        mock_instance.translate.side_effect = TooManyRequests("HTTP 429 Too Many Requests")
        mock_translator_cls.return_value = mock_instance

        # Mock requests.Session.get for Google Client API fallback
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [[["Bonjour monde", "Hello world", None, None]]]

        with patch.object(TranslationService.get_session(), "get", return_value=mock_resp):
            worker = TranslationWorker("Hello world", "en", "fr")
            results = []
            worker.finished.connect(lambda s, t: results.append((s, t)))
            worker.run()

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0], ("Hello world", "Bonjour monde"))


if __name__ == "__main__":
    unittest.main()
