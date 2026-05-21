from __future__ import annotations

import copy

SURFACE_REGISTRY: dict[str, dict] = {
    "aws": {
        "id": "aws",
        "shell_class": "aws-shell-surface",
        "page_class": "aws-page-surface",
        "header_class": "aws-header-surface",
        "docs_class": "aws-docs-surface",
        "accent": "#ff9900",
        "accent_dark": "#eb5f07",
        "surface": "#f8fbff",
        "panel": "#ffffff",
        "border": "#b8d7f2",
    },
    "azure": {
        "id": "azure",
        "shell_class": "azure-shell-surface",
        "page_class": "azure-page-surface",
        "header_class": "azure-header-surface",
        "docs_class": "azure-docs-surface",
        "accent": "#0078d4",
        "accent_dark": "#005fa3",
        "surface": "#f8fbff",
        "panel": "#ffffff",
        "border": "#b8dcf7",
    },
    "gcp": {
        "id": "gcp",
        "shell_class": "gcp-shell-surface",
        "page_class": "gcp-page-surface",
        "header_class": "gcp-header-surface",
        "docs_class": "gcp-docs-surface",
        "accent": "#4285f4",
        "accent_dark": "#174ea6",
        "surface": "#f8fbff",
        "panel": "#ffffff",
        "border": "#d2e3fc",
    },
    "other": {
        "id": "other",
        "shell_class": "other-shell-surface",
        "page_class": "other-page-surface",
        "header_class": "other-header-surface",
        "docs_class": "other-docs-surface",
        "accent": "#879596",
        "accent_dark": "#687078",
        "surface": "#fcfcfc",
        "panel": "#ffffff",
        "border": "#dce3e8",
    },
}


def normalize_surface(provider: str | None) -> str:
    key = str(provider or "aws").lower().strip()
    return key if key in SURFACE_REGISTRY else "other"


def get_surface(provider: str | None) -> dict:
    return copy.deepcopy(SURFACE_REGISTRY[normalize_surface(provider)])


def list_surfaces() -> dict[str, dict]:
    return {key: copy.deepcopy(value) for key, value in SURFACE_REGISTRY.items()}
