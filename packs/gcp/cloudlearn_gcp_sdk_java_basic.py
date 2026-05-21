from __future__ import annotations

from .._shared import build_pack

PACK = build_pack(
    "cloudlearn.gcp.sdk.java.basic",
    "tooling",
    "1.0.0",
    "gcp",
    {
        "protocol": "gcp-like",
        "actions": ["ComputeEngineClient", "Storage", "SqlInstances", "Publisher", "FirestoreClient", "FunctionsServiceClient", "ProjectsClient", "IamPolicy"],
        "requestSchemas": True,
        "responseSchemas": True,
        "errors": True,
        "pagination": True,
        "regionAware": True,
        "language": "java",
        "sdk": "google-cloud-java",
    },
)
