import os
import socket
import hashlib
import base64
import threading
from typing import Callable

from google import genai
from google.genai import types
from cryptography.fernet import Fernet, InvalidToken

from .settings import get_setting, set_setting

# ── Available models ──────────────────────────────────────────────────────────
AVAILABLE_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]
DEFAULT_MODEL = "gemini-2.5-flash"


def fetch_available_models(api_key: str | None = None, db_path=None) -> list[str]:
    """
    Dynamically queries Google GenAI API with the user's API key to discover all
    currently active, supported Gemini chat/generation models.
    Filters out embedding, video, and audio-only models, prioritizing modern flash & pro models.
    Falls back to curated AVAILABLE_MODELS if the API call fails or is offline.
    """
    key = api_key or load_api_key(db_path)
    if not key:
        return AVAILABLE_MODELS

    try:
        client = genai.Client(api_key=key, http_options={'api_version': 'v1'})
        pager = client.models.list(config={'query_base': True})
        discovered = []
        for m in pager:
            m_name = getattr(m, 'name', '') or ''
            clean_id = m_name.split("/")[-1]
            if not clean_id.startswith("gemini"):
                continue
            lower = clean_id.lower()
            if any(x in lower for x in ["embedding", "imagen", "aqa", "realtime", "tts", "learnlm"]):
                continue
            if clean_id not in discovered:
                discovered.append(clean_id)

        if discovered:
            def _sort_key(name):
                # Put flash first, then pro
                is_flash = 0 if "flash" in name else 1
                return (is_flash, name)

            discovered.sort(key=_sort_key)
            return discovered
    except Exception:
        pass

    return AVAILABLE_MODELS





# ── Encryption helpers ────────────────────────────────────────────────────────

def _derive_fernet_key() -> bytes:
    """
    Derives a deterministic, machine-specific Fernet key from the hostname
    and a fixed app salt. The key never leaves memory and is never stored.
    """
    machine_id = socket.gethostname()
    salt = b"budgetapp-ai-v1"
    raw = hashlib.sha256(machine_id.encode() + salt).digest()
    # Fernet needs a 32-byte url-safe base64-encoded key
    return base64.urlsafe_b64encode(raw)


_FERNET = Fernet(_derive_fernet_key())


def encrypt_api_key(plaintext: str) -> str:
    """Encrypts the API key and returns a base64-encoded ciphertext string."""
    return _FERNET.encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    """
    Decrypts the stored ciphertext and returns the plaintext API key.
    Raises ValueError if decryption fails (wrong machine or corrupted value).
    """
    try:
        return _FERNET.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        raise ValueError(
            "Could not decrypt the stored API key. "
            "If you moved the database to another machine, please re-enter your key in Settings."
        )


# ── Settings helpers ──────────────────────────────────────────────────────────

def save_api_key(plaintext_key: str, db_path=None) -> None:
    """Encrypts and persists the API key to the settings table."""
    encrypted = encrypt_api_key(plaintext_key.strip())
    set_setting("gemini_api_key_enc", encrypted, db_path)


def load_api_key(db_path=None) -> str | None:
    """
    Loads and decrypts the stored API key. Returns None if no key is saved.
    Raises ValueError if decryption fails.
    """
    enc = get_setting("gemini_api_key_enc", db_path)
    if not enc:
        return None
    return decrypt_api_key(enc)


def save_model(model: str, db_path=None) -> None:
    set_setting("gemini_model", model, db_path)


def load_model(db_path=None) -> str:
    return get_setting("gemini_model", db_path) or DEFAULT_MODEL


def has_api_key(db_path=None) -> bool:
    """Returns True if an encrypted API key exists in settings."""
    return bool(get_setting("gemini_api_key_enc", db_path))


# ── Chat engine ───────────────────────────────────────────────────────────────

class GeminiChat:
    """
    Wraps google.genai for multi-turn chat.
    Each instance holds its own conversation history.
    """

    def __init__(self, db_path=None):
        self.db_path = db_path
        self._history: list[dict] = []  # [{"role": "user"|"model", "parts": [{"text": str}]}]
        self._lock = threading.Lock()

    def _get_client_and_model(self):
        api_key = load_api_key(self.db_path)
        if not api_key:
            raise ValueError("No API key configured. Please set your Gemini API key in Settings → AI Assistant.")
        model_name = load_model(self.db_path)
        
        # Clean potential environment variable conflicts
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
            
        client = genai.Client(api_key=api_key, http_options={'api_version': 'v1'})
        return client, model_name

    def send(
        self,
        user_message: str,
        system_prompt: str,
        on_done: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """
        Sends a message asynchronously in a background thread.
        Calls on_done(response_text) on success or on_error(message) on failure.
        The UI thread stays responsive while waiting.
        """
        def _worker():
            try:
                client, model_name = self._get_client_and_model()

                with self._lock:
                    # Build messages history + new user message
                    messages = []
                    for h in self._history:
                        messages.append(
                            types.Content(
                                role=h["role"],
                                parts=[types.Part.from_text(text=h["parts"][0]["text"])]
                            )
                        )
                    messages.append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=user_message)]
                        )
                    )

                config = types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                )

                response = client.models.generate_content(
                    model=model_name,
                    contents=messages,
                    config=config,
                )
                
                reply = response.text.strip()

                with self._lock:
                    self._history.append({"role": "user", "parts": [{"text": user_message}]})
                    self._history.append({"role": "model", "parts": [{"text": reply}]})
                    # Keep history bounded (last 20 turns = 40 messages)
                    if len(self._history) > 40:
                        self._history = self._history[-40:]

                on_done(reply)

            except Exception as e:
                on_error(str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    @property
    def turn_count(self) -> int:
        return len(self._history) // 2

