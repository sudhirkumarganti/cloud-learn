#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _host_os() -> str:
    return str(platform.system()).strip().lower()


def _supported_backends() -> list[str]:
    host_os = _host_os()
    if host_os in {"windows", "darwin"}:
        return ["multipass"]
    return ["multipass", "lxd"]


def _cli_for(backend: str) -> str | None:
    backend = (backend or "").strip().lower()
    if backend == "multipass":
        return shutil.which("multipass")
    if backend == "lxd":
        return shutil.which("lxc")
    return None


def _available(backend: str) -> bool:
    binary = _cli_for(backend)
    if not binary:
        return False
    try:
        if backend == "multipass":
            completed = subprocess.run([binary, "list", "--format", "json"], capture_output=True, text=True, timeout=15)
        else:
            completed = subprocess.run([binary, "info"], capture_output=True, text=True, timeout=15)
        return completed.returncode == 0
    except Exception:
        return False


def _bootstrap_commands(backend: str) -> tuple[str, list[list[str]], str]:
    backend = (backend or "").strip().lower()
    host_os = _host_os()
    if backend == "multipass":
        if host_os == "windows":
            return ("manual-multipass", [], "Multipass is required on the host. Install Multipass and retry.")
        if host_os == "darwin":
            return ("manual-multipass", [], "Multipass is required on the host. Install Multipass and retry.")
        if host_os == "linux":
            return ("manual-multipass", [], "Multipass is required on the host. Install Multipass and retry.")
        return ("manual-multipass", [], "Multipass is required on the host. Install Multipass and retry.")
    if backend == "lxd":
        if host_os == "linux":
            return ("manual-lxd", [], "LXD is required on the host. Install and initialize LXD, then retry.")
        return ("manual-lxd", [], "LXD is required on the host. Install and initialize LXD on a Linux host, then retry.")
    return ("manual", [], f"{backend or 'runtime'} is required on the host.")


def _status_payload(backend: str | None = None) -> dict:
    if backend:
        backend = backend.strip().lower()
        helper, _, message = _bootstrap_commands(backend)
        available = _available(backend)
        status = "ready" if available else "missing"
        return {
            "backend": backend,
            "available": available,
            "status": status,
            "message": f"{backend.upper()} is available." if available else message,
            "helper": helper,
            "label": backend.upper() if backend != "multipass" else "Multipass",
            "host_os": _host_os(),
            "checked_at": _now(),
        }

    backends = {backend: _status_payload(backend) for backend in _supported_backends()}
    return {
        "available": any(item.get("available") for item in backends.values()),
        "backends": backends,
        "host_os": _host_os(),
        "preferred_backend": "multipass" if _host_os() in {"windows", "darwin"} else ("multipass" if _available("multipass") else "lxd"),
        "checked_at": _now(),
    }


def _run_backend(backend: str, args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    binary = _cli_for(backend)
    if backend == "host":
        try:
            return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        except Exception as exc:
            return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr=str(exc))
    if not binary:
        return subprocess.CompletedProcess(args=[backend, *args], returncode=1, stdout="", stderr=f"{backend} is unavailable on the host")
    try:
        return subprocess.run([binary, *args], capture_output=True, text=True, timeout=timeout)
    except Exception as exc:
        return subprocess.CompletedProcess(args=[binary, *args], returncode=1, stdout="", stderr=str(exc))


def _bootstrap_backend(backend: str) -> dict:
    helper, _, message = _bootstrap_commands(backend)
    if _available(backend):
        payload = _status_payload(backend)
        payload["status"] = "ready"
        payload["message"] = f"{payload['label']} is available."
        return payload
    payload = _status_payload(backend)
    payload["status"] = "manual"
    payload["message"] = message
    payload["helper"] = helper
    return payload


def _host_ssh_identity() -> dict:
    home = Path.home()
    ssh_dir = home / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    private_key = ssh_dir / "cloudlearn_multipass_ed25519"
    public_key = private_key.with_suffix(private_key.suffix + ".pub") if private_key.suffix else Path(str(private_key) + ".pub")
    if not private_key.exists() or not public_key.exists():
        private_key.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(private_key), "-C", "cloudlearn"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except Exception:
            pass
    if not private_key.exists() or not public_key.exists():
        return {"available": False, "message": "Unable to create host SSH identity."}
    try:
        public_value = public_key.read_text(encoding="utf-8").strip()
    except Exception:
        public_value = ""
    return {
        "available": bool(public_value),
        "private_key_path": str(private_key),
        "public_key_path": str(public_key),
        "public_key": public_value,
    }


class BridgeHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in {"/health", "/healthz"}:
            self._send(200, {"ok": True, "host_os": _host_os(), "backends": _status_payload().get("backends", {})})
            return
        if parsed.path == "/status":
            params = parse_qs(parsed.query)
            backend = params.get("backend", [""])[0]
            self._send(200, _status_payload(backend or None))
            return
        if parsed.path == "/ssh-identity":
            self._send(200, _host_ssh_identity())
            return
        self._send(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length).decode("utf-8", errors="ignore") if length else "{}"
        try:
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = {}
        if parsed.path == "/bootstrap":
            backend = str(payload.get("backend") or "").strip().lower()
            if backend not in _supported_backends():
                self._send(400, {"error": "unsupported_backend", "backend": backend, "host_os": _host_os()})
                return
            self._send(200, _bootstrap_backend(backend))
            return
        if parsed.path == "/run":
            backend = str(payload.get("backend") or "").strip().lower()
            args = payload.get("args") or []
            timeout = int(payload.get("timeout") or 60)
            if backend not in {"multipass", "lxd", "host"}:
                self._send(400, {"error": "unsupported_backend", "backend": backend})
                return
            if not isinstance(args, list):
                self._send(400, {"error": "invalid_args"})
                return
            completed = _run_backend(backend, [str(arg) for arg in args], timeout=timeout)
            self._send(200, {
                "backend": backend,
                "returncode": int(completed.returncode),
                "stdout": completed.stdout or "",
                "stderr": completed.stderr or "",
            })
            return
        self._send(404, {"error": "not_found"})

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="CloudLearn runtime bridge")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9170)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), BridgeHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
