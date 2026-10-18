"""
Translation service module.

Handles interaction with translation APIs, dynamic language loading,
HTTP session pooling, automatic text chunking for large inputs (up to 50k+ chars),
and asynchronous translation via QThread.
"""

import logging
from typing import Optional, Dict, List, Callable
import requests
from PySide6.QtCore import QObject, QThread, Signal, Slot
from deep_translator import GoogleTranslator
import deep_translator.google
from deep_translator.exceptions import (
    NotValidPayload,
    TooManyRequests,
    TranslationNotFound,
    RequestError,
)

logger = logging.getLogger(__name__)

# Complete fallback language list for offline initialization or network failures
FALLBACK_LANGUAGES: Dict[str, str] = {
    "afrikaans": "af",
    "albanian": "sq",
    "amharic": "am",
    "arabic": "ar",
    "armenian": "hy",
    "azerbaijani": "az",
    "basque": "eu",
    "belarusian": "be",
    "bengali": "bn",
    "bosnian": "bs",
    "bulgarian": "bg",
    "catalan": "ca",
    "cebuano": "ceb",
    "chinese (simplified)": "zh-CN",
    "chinese (traditional)": "zh-TW",
    "corsican": "co",
    "croatian": "hr",
    "czech": "cs",
    "danish": "da",
    "dutch": "nl",
    "english": "en",
    "esperanto": "eo",
    "estonian": "et",
    "filipino": "tl",
    "finnish": "fi",
    "french": "fr",
    "frisian": "fy",
    "galician": "gl",
    "georgian": "ka",
    "german": "de",
    "greek": "el",
    "gujarati": "gu",
    "haitian creole": "ht",
    "hausa": "ha",
    "hawaiian": "haw",
    "hebrew": "iw",
    "hindi": "hi",
    "hmong": "hmn",
    "hungarian": "hu",
    "icelandic": "is",
    "igbo": "ig",
    "indonesian": "id",
    "irish": "ga",
    "italian": "it",
    "japanese": "ja",
    "javanese": "jw",
    "kannada": "kn",
    "kazakh": "kk",
    "khmer": "km",
    "korean": "ko",
    "kurdish": "ku",
    "kyrgyz": "ky",
    "lao": "lo",
    "latin": "la",
    "latvian": "lv",
    "lithuanian": "lt",
    "luxembourgish": "lb",
    "macedonian": "mk",
    "malagasy": "mg",
    "malay": "ms",
    "malayalam": "ml",
    "maltese": "mt",
    "maori": "mi",
    "marathi": "mr",
    "mongolian": "mn",
    "myanmar": "my",
    "nepali": "ne",
    "norwegian": "no",
    "odia": "or",
    "pashto": "ps",
    "persian": "fa",
    "polish": "pl",
    "portuguese": "pt",
    "punjabi": "pa",
    "romanian": "ro",
    "russian": "ru",
    "samoan": "sm",
    "scots gaelic": "gd",
    "serbian": "sr",
    "sesotho": "st",
    "shona": "sn",
    "sindhi": "sd",
    "sinhala": "si",
    "slovak": "sk",
    "slovenian": "sl",
    "somali": "so",
    "spanish": "es",
    "sundanese": "su",
    "swahili": "sw",
    "swedish": "sv",
    "tajik": "tg",
    "tamil": "ta",
    "telugu": "te",
    "thai": "th",
    "turkish": "tr",
    "ukrainian": "uk",
    "urdu": "ur",
    "uyghur": "ug",
    "uzbek": "uz",
    "vietnamese": "vi",
    "welsh": "cy",
    "xhosa": "xh",
    "yiddish": "yi",
    "yoruba": "yo",
    "zulu": "zu",
}


def split_text_into_chunks(text: str, max_chunk_size: int = 4000) -> List[str]:
    """
    Split large text into logical chunks (paragraphs, sentences, or words)
    so each chunk remains below Google's 5000-character per-request limit.
    """
    if len(text) <= max_chunk_size:
        return [text]

    chunks: List[str] = []
    paragraphs = text.split("\n")
    current_chunk: List[str] = []
    current_len = 0

    for paragraph in paragraphs:
        p_len = len(paragraph) + 1
        if p_len > max_chunk_size:
            # Paragraph itself exceeds max_chunk_size: split by sentences/words
            words = paragraph.split(" ")
            for word in words:
                w_len = len(word) + 1
                if current_len + w_len > max_chunk_size and current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_len = 0
                current_chunk.append(word)
                current_len += w_len
        else:
            if current_len + p_len > max_chunk_size and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_len = 0
            current_chunk.append(paragraph)
            current_len += p_len

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks if chunks else [text]


class TranslationWorker(QObject):
    """
    Worker object executing translation off the main thread with auto-chunking
    and automatic API fallback.
    """
    finished = Signal(str, str)  # source_text, translated_text
    error = Signal(str)          # error message

    def __init__(self, source_text: str, source_lang: str, target_lang: str) -> None:
        super().__init__()
        self.source_text = source_text
        self.source_lang = source_lang
        self.target_lang = target_lang
        self._is_cancelled: bool = False

    def cancel(self) -> None:
        """Signal worker to stop processing remaining chunks."""
        self._is_cancelled = True

    def _translate_chunk(self, chunk: str, timeout: int = 10) -> str:
        """
        Translate a single chunk (< 4500 chars).
        Tries deep_translator.GoogleTranslator first. If rate-limited (429) or failed,
        seamlessly falls back to the Google Client API endpoint (translate.googleapis.com).
        """
        if not chunk.strip():
            return chunk

        # Primary Engine: GoogleTranslator via deep-translator
        try:
            session = TranslationService.get_session()
            orig_requests_get = deep_translator.google.requests.get
            try:
                deep_translator.google.requests.get = lambda url, **kwargs: session.get(url, timeout=timeout, **kwargs)
                translator = GoogleTranslator(source=self.source_lang, target=self.target_lang)
                result = translator.translate(chunk)
                if result is not None and result.strip():
                    return result
            finally:
                deep_translator.google.requests.get = orig_requests_get
        except TooManyRequests:
            logger.info("GoogleTranslator mobile endpoint hit 429; falling back to Google Client API...")
        except requests.exceptions.HTTPError as he:
            if he.response is not None and he.response.status_code == 429:
                logger.info("GoogleTranslator HTTP 429; falling back to Google Client API...")
            else:
                raise

        # Fallback Engine: Google Client API (translate.googleapis.com)
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": self.source_lang,
            "tl": self.target_lang,
            "dt": "t",
            "q": chunk,
        }
        session = TranslationService.get_session()
        resp = session.get(url, params=params, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            translated_pieces = [sentence[0] for sentence in data[0] if sentence and sentence[0]]
            return "".join(translated_pieces)
        elif resp.status_code == 429:
            raise TooManyRequests("Google translation service rate limit reached. Please wait a few seconds.")
        else:
            resp.raise_for_status()
            return chunk

    @Slot()
    def run(self) -> None:
        """
        Execute translation across chunks inside background thread.
        """
        if self._is_cancelled:
            return

        try:
            # Automatic chunking prevents Google 5000-character limit errors
            chunks = split_text_into_chunks(self.source_text, max_chunk_size=4000)
            translated_chunks: List[str] = []

            for chunk in chunks:
                if self._is_cancelled:
                    logger.info("Translation worker cancelled.")
                    return
                translated_part = self._translate_chunk(chunk, timeout=10)
                translated_chunks.append(translated_part)

            final_text = "\n".join(translated_chunks)
            if not self._is_cancelled:
                self.finished.emit(self.source_text, final_text)

        except NotValidPayload:
            err = "Invalid input text provided for translation."
            logger.warning(err)
            self.error.emit(err)
        except TooManyRequests as e:
            err = str(e) or "Translation request limit exceeded. Please wait a moment and try again."
            logger.warning(err)
            self.error.emit(err)
        except TranslationNotFound:
            err = "No translation found for the requested text."
            logger.warning(err)
            self.error.emit(err)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            err = "Network timeout or connection error. Please check your internet connection."
            logger.error(f"{err} ({e})")
            self.error.emit(err)
        except RequestError as e:
            err = f"API communication error: {e}"
            logger.error(err)
            self.error.emit(err)
        except Exception as e:
            err = f"Unexpected translation error: {e}"
            logger.error(err)
            self.error.emit(err)


class TranslationService:
    """
    Service class managing language definitions, cache, HTTP session pooling, and async execution.
    """

    _instance = None
    _supported_languages: Optional[Dict[str, str]] = None
    _session: Optional[requests.Session] = None

    def __new__(cls) -> "TranslationService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_session(cls) -> requests.Session:
        """Return a persistent requests.Session with connection pooling."""
        if cls._session is None:
            cls._session = requests.Session()
            cls._session.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                )
            })
        return cls._session

    @classmethod
    def get_supported_languages(cls) -> Dict[str, str]:
        """
        Load and cache supported languages from deep_translator.
        Falls back to comprehensive pre-populated list if API call fails.
        """
        if cls._supported_languages is None:
            try:
                translator = GoogleTranslator(source="auto", target="en")
                langs = translator.get_supported_languages(as_dict=True)
                if isinstance(langs, dict) and len(langs) > 0:
                    cls._supported_languages = dict(sorted(langs.items()))
                else:
                    cls._supported_languages = FALLBACK_LANGUAGES.copy()
            except Exception as e:
                logger.warning(f"Could not load dynamic language list from deep-translator ({e}); using offline fallback.")
                cls._supported_languages = FALLBACK_LANGUAGES.copy()

        return cls._supported_languages

    @classmethod
    def get_language_codes(cls) -> List[str]:
        """Return list of language codes sorted by language name."""
        return list(cls.get_supported_languages().values())

    @classmethod
    def get_language_names(cls) -> List[str]:
        """Return list of language names sorted alphabetically."""
        return list(cls.get_supported_languages().keys())

    @classmethod
    def get_language_code_from_name(cls, name: str) -> Optional[str]:
        """Get code for a given language name (case-insensitive)."""
        name_lower = name.lower()
        return cls.get_supported_languages().get(name_lower)

    @classmethod
    def get_language_name_from_code(cls, code: str) -> Optional[str]:
        """Get name for a given language code."""
        for name, c in cls.get_supported_languages().items():
            if c.lower() == code.lower():
                return name
        return None
