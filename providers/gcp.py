from __future__ import annotations

from core.provider_registry import get_provider, provider_matrix
from core.pack_catalog import packs_for_provider


def matrix() -> dict:
    packs = packs_for_provider("gcp")
    matrix_data = provider_matrix("gcp", packs)
    matrix_data["catalog"] = {
        "service": [pack for pack in packs if pack.get("type") == "service"],
        "tooling": [pack for pack in packs if pack.get("type") == "tooling"],
    }
    return matrix_data


def tool_response(tool: str) -> dict:
    tool = tool.lower()
    provider_info = get_provider("gcp")
    endpoint = "http://127.0.0.1:9000"
    if tool == "gcloud":
        return {
            "provider": "gcp",
            "tool": "gcloud",
            "status": "planned",
            "endpoint": endpoint,
            "help": [
                "Simulated gcloud will point at local Google-style endpoints.",
                "Commands will translate to local REST calls per service pack.",
            ],
            "provider_surface": provider_info.get("surface", {}),
        }
    if tool == "gcutil":
        return {
            "provider": "gcp",
            "tool": "gcutil",
            "status": "planned",
            "endpoint": endpoint,
            "help": [
                "Legacy gcutil compatibility will be simulated locally.",
                "This remains a tracked gap alongside gcloud parity.",
            ],
            "provider_surface": provider_info.get("surface", {}),
        }
    if tool == "sdk/java":
        return {
            "provider": "gcp",
            "tool": "google-cloud-java",
            "status": "planned",
            "endpoint": endpoint,
            "dependency": "com.google.cloud:*",
            "help": ["Future adapter will expose Google Cloud client defaults against the simulator endpoint."],
            "provider_surface": provider_info.get("surface", {}),
        }
    if tool == "sdk/go":
        return {
            "provider": "gcp",
            "tool": "google-cloud-go",
            "status": "planned",
            "endpoint": endpoint,
            "dependency": "cloud.google.com/go",
            "help": ["Future adapter will point the Go client at local GCP-style REST endpoints."],
            "provider_surface": provider_info.get("surface", {}),
        }
    raise KeyError(tool)
