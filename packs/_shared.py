from __future__ import annotations

from typing import Any


def build_pack(
    pack_id: str,
    pack_type: str,
    version: str,
    provider: str,
    api: dict[str, Any],
    *,
    core_provider_neutral: bool = False,
) -> dict[str, Any]:
    return {
        "id": pack_id,
        "type": pack_type,
        "version": version,
        "provider": provider,
        "coreProviderNeutral": core_provider_neutral,
        "state": "available",
        "active": False,
        "api": api,
        "surfaceProvider": provider if provider != "agnostic" else "other",
    }
