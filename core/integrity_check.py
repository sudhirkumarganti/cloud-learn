"""Runtime file integrity verification.

At build time, a manifest of SHA256 checksums for all .pyc/.so files is
generated. At startup and periodically, the checksums are re-verified.
Tampered files trigger a lockdown to Free tier.
"""
from __future__ import annotations
import hashlib
import json
import os
import threading
import time
import logging
from pathlib import Path

logger = logging.getLogger("cloudlearn.integrity")

_MANIFEST_PATH = Path(os.environ.get(
    "CLOUDLEARN_INTEGRITY_MANIFEST",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), ".integrity_manifest.json")
))

_monitor_thread: threading.Thread | None = None


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def generate_manifest(app_dir: str) -> dict:
    """Compute SHA256 for all .pyc, .so, .pyd files under app_dir.
    Returns {files: {rel_path: sha256_hex}, generated_at: iso}."""
    files = {}
    for root, _dirs, filenames in os.walk(app_dir):
        for fname in filenames:
            if fname.endswith((".pyc", ".so", ".pyd")):
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, app_dir)
                files[rel] = _sha256_file(full)
    return {
        "files": files,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "file_count": len(files),
    }


def save_manifest(manifest: dict, path: str | None = None) -> None:
    target = Path(path) if path else _MANIFEST_PATH
    target.write_text(json.dumps(manifest, indent=2))
    try:
        os.chmod(str(target), 0o444)
    except Exception:
        pass


def load_manifest(path: str | None = None) -> dict | None:
    target = Path(path) if path else _MANIFEST_PATH
    if not target.exists():
        return None
    try:
        return json.loads(target.read_text())
    except Exception:
        return None


def verify_manifest(app_dir: str, manifest: dict | None = None) -> tuple[bool, list[str]]:
    """Verify all files match the manifest checksums.
    Returns (ok, list_of_tampered_file_paths)."""
    if manifest is None:
        manifest = load_manifest()
    if not manifest or not manifest.get("files"):
        return True, []  # No manifest = dev mode, skip check
    tampered = []
    for rel_path, expected_hash in manifest["files"].items():
        full = os.path.join(app_dir, rel_path)
        if not os.path.exists(full):
            tampered.append(rel_path)
            continue
        actual = _sha256_file(full)
        if actual != expected_hash:
            tampered.append(rel_path)
    return len(tampered) == 0, tampered


def _on_tamper_detected(tampered_files: list[str]) -> None:
    """Called when tampered files are detected. Forces Free tier."""
    logger.critical(f"TAMPER DETECTED: {len(tampered_files)} files modified: {tampered_files[:10]}")
    try:
        from core.app_context import STATE, persist_state
        STATE.setdefault("license", {})["tier"] = "free"
        STATE["_tamper_detected"] = True
        STATE["_tamper_files"] = tampered_files[:20]
        STATE["_tamper_detected_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        persist_state()
    except Exception:
        pass
    try:
        from core import security_audit
        security_audit.append_event("tamper.integrity_check_failed", {
            "tampered_files": tampered_files[:20],
            "action": "locked_to_free_tier",
        })
    except Exception:
        pass


def verify_at_startup(app_dir: str | None = None) -> bool:
    """Run integrity check at startup. Returns True if OK."""
    if app_dir is None:
        app_dir = os.path.dirname(os.path.dirname(__file__))
    manifest = load_manifest()
    if not manifest:
        return True  # No manifest = dev/source mode
    ok, tampered = verify_manifest(app_dir, manifest)
    if not ok:
        _on_tamper_detected(tampered)
    return ok


def start_integrity_monitor(app_dir: str | None = None, interval_s: float = 1800) -> None:
    """Daemon thread: re-verify manifest every interval_s seconds."""
    global _monitor_thread
    if _monitor_thread is not None:
        return
    if app_dir is None:
        app_dir = os.path.dirname(os.path.dirname(__file__))
    manifest = load_manifest()
    if not manifest:
        return  # No manifest = dev mode, skip monitoring

    def _loop():
        while True:
            time.sleep(interval_s)
            try:
                ok, tampered = verify_manifest(app_dir, manifest)
                if not ok:
                    _on_tamper_detected(tampered)
            except Exception:
                pass

    _monitor_thread = threading.Thread(target=_loop, daemon=True, name="integrity-monitor")
    _monitor_thread.start()
