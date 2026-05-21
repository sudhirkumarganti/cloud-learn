from __future__ import annotations

from .._shared import build_pack

PACK = build_pack(
    "cloudlearn.gcp.sdk.go.basic",
    "tooling",
    "1.0.0",
    "gcp",
    {
        "protocol": "gcp-like",
        "actions": ["ComputeEngine", "Storage", "CloudSQL", "PubSub", "Firestore", "CloudFunctions", "IAM"],
        "requestSchemas": True,
        "responseSchemas": True,
        "errors": True,
        "pagination": True,
        "regionAware": True,
        "language": "go",
        "sdk": "google-cloud-go",
    },
)
