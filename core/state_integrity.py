"""State file integrity protection via HMAC-SHA256.

Signs the serialized state JSON on every persist and verifies on every load.
The HMAC key is derived from an install-specific secret stored at a separate
location from the state file, so editing the SQLite directly doesn't help
without also knowing the key.

On tamper detection: the caller (cloudlearn_platform.py) forces tier="free"
and re-persists the cleaned state.
"""
from __future__ import annotations
import hashlib
import hmac
import os
import secrets
from pathlib import Path


# Install key lives on the data volume, separate from the state database.
_INSTALL_KEY_PATH = Path(os.environ.get("CLOUDLEARN_INSTALL_KEY_FILE", "/data/.cloudlearn_install_key"))
# Fallback for dev/local environments where /data doesn't exist
_INSTALL_KEY_PATH_LOCAL = Path(__file__).parent.parent / ".cloudlearn_install_key"

_cached_key: bytes | None = None


def _key_path() -> Path:
    """Return the install key file path, preferring /data for Docker."""
    if _INSTALL_KEY_PATH.parent.exists():
        return _INSTALL_KEY_PATH
    return _INSTALL_KEY_PATH_LOCAL


def get_or_create_install_key() -> bytes:
    """Return the 32-byte install-specific HMAC key.
    Generated once on first boot; persists across restarts."""
    global _cached_key
    if _cached_key is not None:
        return _cached_key
    path = _key_path()
    if path.exists():
        try:
            raw = path.read_bytes().strip()
            if len(raw) >= 32:
                _cached_key = raw[:64]  # hex-encoded 32 bytes = 64 chars
                return _cached_key
        except Exception:
            pass
    # Generate new key
    key_hex = secrets.token_hex(32)  # 64 hex chars = 32 bytes
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(key_hex)
        os.chmod(str(path), 0o600)  # owner-only
    except Exception:
        pass  # in-memory only if filesystem is read-only
    _cached_key = key_hex.encode()
    return _cached_key


def derive_hmac_key(install_key: bytes, salt: bytes = b"cloudlearn-state-integrity-v1") -> bytes:
    """Derive the HMAC signing key from the install key using HKDF-like derivation.
    Uses PBKDF2 with 1 iteration as a simple KDF (cryptography lib may not be available)."""
    return hashlib.pbkdf2_hmac("sha256", install_key, salt, iterations=1, dklen=32)


def sign_state(state_json_bytes: bytes) -> str:
    """Compute HMAC-SHA256 over the state JSON. Returns hex digest."""
    key = derive_hmac_key(get_or_create_install_key())
    return hmac.new(key, state_json_bytes, hashlib.sha256).hexdigest()


def verify_state(state_json_bytes: bytes, signature: str) -> bool:
    """Verify HMAC-SHA256 signature. Returns True if valid."""
    if not signature:
        return False
    key = derive_hmac_key(get_or_create_install_key())
    expected = hmac.new(key, state_json_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
