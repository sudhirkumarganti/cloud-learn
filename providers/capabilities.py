from __future__ import annotations

import copy

from core.pack_catalog import PROVIDER_PACK_GROUPS, packs_for_provider
from core.provider_registry import get_provider, normalize_provider


AWS_SERVICE_CAPABILITIES: list[dict] = [
    {
        "id": "s3",
        "name": "S3",
        "status": "integrated",
        "summary": "Path-style S3 REST and console flows are available locally.",
        "routes": ["/", "/api/s3/*"],
    },
    {
        "id": "iam",
        "name": "IAM",
        "status": "integrated",
        "summary": "Users, groups, roles, policies, attachments, identity providers, and account settings are available.",
        "routes": ["/api/iam/users", "/api/iam/groups", "/api/iam/roles", "/api/iam/policies", "/api/iam/identity-providers", "/api/iam/account-settings"],
    },
    {
        "id": "ec2",
        "name": "EC2",
        "status": "integrated",
        "summary": "Instances, runtime bootstrap, and console access are available.",
        "routes": ["/api/ec2/amis", "/api/ec2/runtime", "/api/ec2/instances", "/api/ec2/instances/{instance_id}/console"],
    },
    {
        "id": "lambda",
        "name": "Lambda",
        "status": "integrated",
        "summary": "Functions, code/config updates, permissions, versions, and invoke flows are available.",
        "routes": ["/api/lambda/functions", "/2015-03-31/functions", "/api/lambda/functions/{function_name}/invoke", "/2015-03-31/functions/{function_name}/invocations"],
    },
    {
        "id": "vpc",
        "name": "VPC",
        "status": "integrated",
        "summary": "VPCs, subnets, route tables, security groups, and internet gateways are available.",
        "routes": ["/api/vpc/vpcs", "/api/vpc/subnets", "/api/vpc/security-groups", "/api/vpc/route-tables", "/api/vpc/internet-gateways"],
    },
    {
        "id": "rds",
        "name": "RDS",
        "status": "integrated",
        "summary": "Databases, subnet groups, parameter groups, snapshots, and tag management are available.",
        "routes": ["/api/rds/databases", "/api/rds/subnet-groups", "/api/rds/parameter-groups", "/api/rds/snapshots"],
    },
    {
        "id": "sqs",
        "name": "SQS",
        "status": "integrated",
        "summary": "Queues, message delivery, visibility, purge, and tags are available.",
        "routes": ["/api/sqs/queues", "/api/sqs/queues/{queue_name}/messages", "/api/sqs/queues/{queue_name}/receive", "/api/sqs/queues/{queue_name}/tags"],
    },
    {
        "id": "dynamodb",
        "name": "DynamoDB",
        "status": "integrated",
        "summary": "Tables, items, query, scan, and tag management are available.",
        "routes": ["/api/dynamodb/tables", "/api/dynamodb/tables/{table_name}/items", "/api/dynamodb/tables/{table_name}/query", "/api/dynamodb/tables/{table_name}/scan"],
    },
    {
        "id": "apigateway",
        "name": "API Gateway",
        "status": "integrated",
        "summary": "APIs, resources, methods, integrations, deployments, stages, and invoke routes are available.",
        "routes": ["/api/apigateway/apis", "/api/apigateway/apis/{api_id}/resources", "/api/apigateway/apis/{api_id}/deployments", "/api/apigateway/invoke/{api_id}/{stage_name}"],
    },
]


GCP_SERVICE_CAPABILITIES: list[dict] = [
    {
        "id": "compute",
        "name": "Compute Engine",
        "status": "integrated",
        "summary": "Instances, project/zone routing, start/stop/reset, and delete flows are available.",
        "routes": ["/compute/v1/projects/{project}/zones/{zone}/instances", "/api/gcp/compute/v1/projects/{project}/zones/{zone}/instances"],
    },
    {
        "id": "storage",
        "name": "Cloud Storage",
        "status": "integrated",
        "summary": "Buckets and object CRUD are available through Google-style REST endpoints.",
        "routes": ["/storage/v1/b", "/storage/v1/b/{bucket}/o", "/api/gcp/storage/v1/b/{bucket}/o/{object_name:path}"],
    },
    {
        "id": "sql",
        "name": "Cloud SQL",
        "status": "integrated",
        "summary": "Instances, restarts, and lifecycle operations are available.",
        "routes": ["/sql/v1beta4/projects/{project}/instances", "/sql/v1beta4/projects/{project}/instances/{instance}/restart"],
    },
    {
        "id": "pubsub",
        "name": "Pub/Sub",
        "status": "integrated",
        "summary": "Topics, subscriptions, publish, pull, acknowledge, and ack deadline changes are available.",
        "routes": ["/v1/projects/{project}/topics", "/v1/projects/{project}/subscriptions", "/v1/projects/{project}/subscriptions/{subscription}:pull", "/v1/projects/{project}/subscriptions/{subscription}:acknowledge"],
    },
    {
        "id": "firestore",
        "name": "Firestore",
        "status": "integrated",
        "summary": "Documents, collection listing, and query endpoints are available.",
        "routes": ["/firestore/v1/projects/{project}/databases/{database}/documents", "/firestore/v1/projects/{project}/databases/{database}/documents:runQuery"],
    },
    {
        "id": "functions",
        "name": "Cloud Functions",
        "status": "integrated",
        "summary": "Functions, IAM policy, invocations, and call flows are available.",
        "routes": ["/v1/projects/{project}/locations/{location}/functions", "/v1/projects/{project}/locations/{location}/functions/{function}:call"],
    },
    {
        "id": "apigateway",
        "name": "API Gateway",
        "status": "integrated",
        "summary": "APIs, configs, and gateways are available.",
        "routes": ["/v1/projects/{project}/locations/{location}/apis", "/v1/projects/{project}/locations/{location}/apiConfigs", "/v1/projects/{project}/locations/{location}/gateways"],
    },
    {
        "id": "vpc",
        "name": "VPC Network",
        "status": "integrated",
        "summary": "Networks, subnetworks, and firewall rules are available.",
        "routes": ["/compute/v1/projects/{project}/global/networks", "/compute/v1/projects/{project}/regions/{region}/subnetworks", "/compute/v1/projects/{project}/global/firewalls"],
    },
    {
        "id": "iam",
        "name": "IAM",
        "status": "integrated",
        "summary": "Project IAM policy, test permissions, service accounts, and account settings are available.",
        "routes": ["/v1/projects/{project}:getIamPolicy", "/v1/projects/{project}/serviceAccounts", "/api/gcp/iam/users", "/api/gcp/iam/groups"],
    },
]


SERVICE_CAPABILITIES = {
    "aws": AWS_SERVICE_CAPABILITIES,
    "gcp": GCP_SERVICE_CAPABILITIES,
    "azure": [],
    "other": [],
}


def provider_services(provider: str | None) -> dict:
    provider_key = normalize_provider(provider)
    provider_info = get_provider(provider_key)
    services = copy.deepcopy(SERVICE_CAPABILITIES.get(provider_key, []))
    return {
        "provider": provider_info["id"],
        "display_name": provider_info["name"],
        "surface": provider_info.get("surface", {}),
        "services": services,
        "count": len(services),
        "integrated": len([service for service in services if service.get("status") == "integrated"]),
        "partial": len([service for service in services if service.get("status") == "partial"]),
    }


def provider_capabilities(provider: str | None) -> dict:
    provider_key = normalize_provider(provider)
    provider_info = get_provider(provider_key)
    services = provider_services(provider_key)
    packs = packs_for_provider(provider_key) if provider_key in PROVIDER_PACK_GROUPS else []
    return {
        "provider": provider_info["id"],
        "display_name": provider_info["name"],
        "surface": provider_info.get("surface", {}),
        "navigation": provider_info.get("navigation", {}),
        "native_services": provider_info.get("native_services", []),
        "space_facts": provider_info.get("space_facts", []),
        "tooling": provider_info.get("tooling", {}),
        "services": services["services"],
        "service_counts": {
            "total": services["count"],
            "integrated": services["integrated"],
            "partial": services["partial"],
        },
        "gaps": provider_info.get("gaps", []),
        "packs": {
            "total": len(packs),
            "service": len([pack for pack in packs if pack.get("type") == "service"]),
            "tooling": len([pack for pack in packs if pack.get("type") == "tooling"]),
            "runtime": len([pack for pack in packs if pack.get("type") == "runtime"]),
        },
    }
