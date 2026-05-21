from __future__ import annotations

from .._shared import build_pack

PACK = build_pack(
    "cloudlearn.gcp.gcloud.basic",
    "tooling",
    "1.0.0",
    "gcp",
    {
        "protocol": "gcp-like",
        "actions": ["compute", "storage", "sql", "pubsub", "firestore", "functions", "apigateway", "vpc", "iam"],
        "requestSchemas": True,
        "responseSchemas": True,
        "errors": True,
        "pagination": True,
        "regionAware": True,
        "cli": "gcloud",
        "legacyCli": "gcutil",
    },
)
