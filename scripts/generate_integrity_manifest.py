"""Build-time integrity manifest generator.

Run during Docker build after .pyc compilation:
    python scripts/generate_integrity_manifest.py /app
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.integrity_check import generate_manifest, save_manifest

if __name__ == "__main__":
    app_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manifest = generate_manifest(app_dir)
    save_manifest(manifest)
    print(f"Integrity manifest: {manifest['file_count']} files checksummed")
