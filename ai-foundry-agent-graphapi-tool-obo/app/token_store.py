import time
from typing import Optional, Dict, Any
from threading import RLock

class SecureTokenStore:
    """
    In-memory  token store.
    Production: replace with Redis / Azure Cache + encryption + TTL.
    Stores: access_token, expires_at, refresh_token (opsiyonel).
    """
    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}
        self._lock = RLock()

    def save_tokens(self, session_id: str, tokens: Dict[str, Any]):
        with self._lock:
            self._data[session_id] = {
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "expires_at": time.time() + tokens.get("expires_in", 0)
            }

    def get_access_token(self, session_id: str) -> Optional[str]:
        with self._lock:
            entry = self._data.get(session_id)
            if not entry:
                return None
            # (Opsiyonel) expiry kontrolü burada yapılabilir
            return entry.get("access_token")

    def delete(self, session_id: str):
        with self._lock:
            self._data.pop(session_id, None)

token_store = SecureTokenStore()