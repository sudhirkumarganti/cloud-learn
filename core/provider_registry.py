from __future__ import annotations

import copy

from core.surface_registry import get_surface

PROVIDER_REGISTRY: dict[str, dict] = {
    "aws": {
        "id": "aws",
        "name": "AWS",
        "console_name": "CloudLearn Console",
        "surface": get_surface("aws"),
        "theme": {
            "accent": "#ff9900",
            "accent_dark": "#eb5f07",
            "surface": "#f8fbff",
            "border": "#b8d7f2",
        },
        "navigation": {
            "title": "AWS services",
            "items": [
                ["IAM", "iam"],
                ["EC2", "ec2"],
                ["DynamoDB", "dynamodb"],
                ["SQS", "sqs"],
                ["RDS", "rds"],
                ["Lambda", "lambda"],
                ["VPC", "vpc"],
                ["API Gateway", "apigateway"],
                ["S3", "s3-buckets"],
            ],
            "icons": {
                "iam": "admin_panel_settings",
                "ec2": "computer",
                "dynamodb": "database",
                "sqs": "queue",
                "rds": "database",
                "lambda": "bolt",
                "vpc": "lan",
                "apigateway": "api",
                "s3-buckets": "storage",
            },
        },
        "native_services": ["S3", "IAM", "EC2", "Lambda", "RDS", "SQS", "DynamoDB", "API Gateway", "VPC"],
        "tooling": {
            "cli": [
                {"name": "AWS CLI", "status": "integrated", "notes": "Path-style S3, query-style AWS APIs, and major service command translations are simulated locally."},
            ],
            "sdk": [
                {"name": "Java SDK", "status": "partial", "notes": "Service routes exist, but provider-specific SDK request shaping remains to be wired."},
                {"name": "Go SDK", "status": "partial", "notes": "Service routes exist, but provider-specific SDK request shaping remains to be wired."},
            ],
        },
        "space_facts": [
            {"key": "ec2_count", "label": "EC2"},
            {"key": "lambda_count", "label": "Lambda"},
            {"key": "rds_count", "label": "RDS"},
            {"key": "sqs_count", "label": "SQS"},
            {"key": "dynamodb_count", "label": "DynamoDB"},
        ],
    },
    "azure": {
        "id": "azure",
        "name": "Azure",
        "console_name": "CloudLearn Console",
        "surface": get_surface("azure"),
        "theme": {
            "accent": "#0078d4",
            "accent_dark": "#005fa3",
            "surface": "#f8fbff",
            "border": "#b8dcf7",
        },
        "navigation": {
            "title": "Azure services",
            "items": [
                ["Entra ID", "iam"],
                ["Virtual Machines", "ec2"],
                ["Cosmos DB", "dynamodb"],
                ["Service Bus", "sqs"],
                ["SQL Database", "rds"],
                ["Functions", "lambda"],
                ["Virtual Network", "vpc"],
                ["API Management", "apigateway"],
                ["Blob Storage", "s3-buckets"],
            ],
            "icons": {
                "iam": "admin_panel_settings",
                "ec2": "computer",
                "dynamodb": "database",
                "sqs": "queue",
                "rds": "database",
                "lambda": "bolt",
                "vpc": "lan",
                "apigateway": "api",
                "s3-buckets": "storage",
            },
        },
        "native_services": ["Virtual Machines", "Functions", "SQL Database", "Service Bus", "Cosmos DB"],
        "tooling": {
            "cli": [
                {"name": "gcloud / gcutil", "status": "partial", "notes": "Native REST routes exist; provider-specific CLI shape adapters remain to be added."},
            ],
            "sdk": [
                {"name": "Java SDK", "status": "partial", "notes": "Service routes exist; exact client compatibility layer is still missing."},
                {"name": "Go SDK", "status": "partial", "notes": "Service routes exist; exact client compatibility layer is still missing."},
            ],
        },
        "space_facts": [
            {"key": "ec2_count", "label": "Virtual Machines"},
            {"key": "lambda_count", "label": "Functions"},
            {"key": "rds_count", "label": "SQL Database"},
            {"key": "sqs_count", "label": "Service Bus"},
            {"key": "dynamodb_count", "label": "Cosmos DB"},
        ],
    },
    "gcp": {
        "id": "gcp",
        "name": "GCP",
        "console_name": "CloudLearn Console",
        "surface": get_surface("gcp"),
        "theme": {
            "accent": "#4285f4",
            "accent_dark": "#174ea6",
            "surface": "#f8fbff",
            "border": "#d2e3fc",
        },
        "navigation": {
            "title": "GCP services",
            "items": [
                ["IAM", "iam"],
                ["Compute Engine", "ec2"],
                ["Firestore", "dynamodb"],
                ["Pub/Sub", "sqs"],
                ["Cloud SQL", "rds"],
                ["Cloud Functions", "lambda"],
                ["VPC Network", "vpc"],
                ["API Gateway", "apigateway"],
                ["Cloud Storage", "s3-buckets"],
            ],
            "icons": {
                "iam": "admin_panel_settings",
                "ec2": "computer",
                "dynamodb": "database",
                "sqs": "queue",
                "rds": "database",
                "lambda": "bolt",
                "vpc": "lan",
                "apigateway": "api",
                "s3-buckets": "storage",
            },
        },
        "native_services": ["Compute Engine", "Cloud Storage", "Cloud SQL", "Pub/Sub", "Firestore", "Cloud Functions", "API Gateway", "VPC Network", "IAM"],
        "tooling": {
            "cli": [
                {"name": "gcloud / gsutil", "status": "partial", "notes": "Native Google-style REST routes exist, and core command translations cover compute, storage, SQL, Pub/Sub, Firestore, Functions, API Gateway, VPC, and IAM. `gsutil` is treated as legacy storage compatibility while `gcloud storage` is the preferred modern path."},
            ],
            "sdk": [
                {"name": "Java SDK", "status": "partial", "notes": "Compute, Storage, SQL, Pub/Sub, Firestore, Functions and IAM are present, but client wrappers are still missing."},
                {"name": "Go SDK", "status": "partial", "notes": "Compute, Storage, SQL, Pub/Sub, Firestore, Functions and IAM are present, but client wrappers are still missing."},
            ],
        },
        "space_facts": [
            {"key": "ec2_count", "label": "Compute Engine"},
            {"key": "lambda_count", "label": "Cloud Functions"},
            {"key": "rds_count", "label": "Cloud SQL"},
            {"key": "sqs_count", "label": "Pub/Sub"},
            {"key": "dynamodb_count", "label": "Firestore"},
        ],
    },
    "other": {
        "id": "other",
        "name": "Other",
        "console_name": "CloudLearn Console",
        "surface": get_surface("other"),
        "theme": {
            "accent": "#879596",
            "accent_dark": "#687078",
            "surface": "#fcfcfc",
            "border": "#dce3e8",
        },
        "navigation": {
            "title": "Services",
            "items": [
                ["Resources", "ec2"],
                ["Queues", "sqs"],
                ["Databases", "rds"],
                ["Functions", "lambda"],
                ["Network", "vpc"],
                ["API", "apigateway"],
                ["Storage", "s3-buckets"],
            ],
            "icons": {
                "ec2": "computer",
                "sqs": "queue",
                "rds": "database",
                "lambda": "bolt",
                "vpc": "lan",
                "apigateway": "api",
                "s3-buckets": "storage",
            },
        },
        "native_services": ["Compute", "Functions", "Database", "Queue", "Storage"],
        "tooling": {
            "cli": [],
            "sdk": [],
        },
        "space_facts": [
            {"key": "ec2_count", "label": "Compute"},
            {"key": "lambda_count", "label": "Functions"},
            {"key": "rds_count", "label": "Database"},
            {"key": "sqs_count", "label": "Queue"},
            {"key": "dynamodb_count", "label": "Storage"},
        ],
    },
}


def normalize_provider(provider: str | None) -> str:
    key = str(provider or "aws").lower().strip()
    return key if key in PROVIDER_REGISTRY else "other"


def get_provider(provider: str | None) -> dict:
    return copy.deepcopy(PROVIDER_REGISTRY[normalize_provider(provider)])


def list_providers() -> dict[str, dict]:
    return {key: copy.deepcopy(value) for key, value in PROVIDER_REGISTRY.items()}


def provider_matrix(provider: str | None, packs: list[dict]) -> dict:
    provider_key = normalize_provider(provider)
    info = get_provider(provider_key)
    provider_packs = [pack for pack in packs if pack.get("provider") == provider_key]
    service_packs = [pack for pack in provider_packs if pack.get("type") == "service"]
    tooling_packs = [pack for pack in provider_packs if pack.get("type") == "tooling"]
    planned_packs = [pack for pack in provider_packs if pack.get("status") == "planned"]
    ready_packs = [pack for pack in provider_packs if pack.get("status") != "planned"]
    return {
        "provider": info["id"],
        "display_name": info["name"],
        "description": f"{info['name']} simulator surface.",
        "surface": info["surface"],
        "implemented_services": info.get("native_services", []),
        "tooling": info.get("tooling", {}),
        "gaps": [],
        "packs": {
            "total": len(provider_packs),
            "active": len(ready_packs),
            "services": len(service_packs),
            "tooling": len(tooling_packs),
            "planned": len(planned_packs),
        },
        "pack_ids": [pack.get("id") for pack in provider_packs],
    }
