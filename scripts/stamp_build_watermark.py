"""Stamp a build watermark into compiled modules for leak traceability.

Usage: python scripts/stamp_build_watermark.py --customer-id CUS123 --build-id B456
"""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path


def stamp(app_dir: str, customer_id: str, build_id: str) -> dict:
    """Write a .build_watermark.json manifest into the app directory."""
    watermark = {
        "customer_id": customer_id,
        "build_id": build_id,
        "build_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "fingerprint": hashlib.sha256(f"{customer_id}:{build_id}:{time.time()}".encode()).hexdigest()[:16],
    }
    path = Path(app_dir) / ".build_watermark.json"
    path.write_text(json.dumps(watermark, indent=2))
    os.chmod(str(path), 0o444)  # read-only
    return watermark


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stamp build watermark")
    parser.add_argument("--customer-id", default="dev")
    parser.add_argument("--build-id", default="local")
    parser.add_argument("--app-dir", default=".")
    args = parser.parse_args()
    result = stamp(args.app_dir, args.customer_id, args.build_id)
    print(f"Watermark stamped: {result}")
