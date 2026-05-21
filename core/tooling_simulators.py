from __future__ import annotations

import shlex
from typing import Any


def _result(provider: str, tool: str, command: str, service: str, operation: str, route: str, args: list[str], notes: str) -> dict[str, Any]:
    return {
        "provider": provider,
        "tool": tool,
        "command": command,
        "service": service,
        "operation": operation,
        "route": route,
        "args": args,
        "notes": notes,
    }


def aws_cli_resolve(command: str) -> dict[str, Any]:
    tokens = shlex.split(command or "")
    if not tokens or tokens[0] != "aws":
        return _result("aws", "awscli", command, "", "", "", tokens, "Command must start with `aws`.")
    args = tokens[1:]
    if len(args) >= 2 and args[0] == "s3" and args[1] == "ls":
        return _result("aws", "awscli", command, "s3", "ListBuckets", "GET /", args, "Simulator local S3 root list.")
    if len(args) >= 3 and args[0] == "s3" and args[1] == "mb":
        return _result("aws", "awscli", command, "s3", "CreateBucket", "PUT /{bucket}", args, "Create a bucket in the local simulator.")
    if len(args) >= 3 and args[0] == "s3" and args[1] == "rb":
        return _result("aws", "awscli", command, "s3", "DeleteBucket", "DELETE /{bucket}", args, "Delete a bucket in the local simulator.")
    if len(args) >= 2 and args[0] == "ec2" and args[1] == "describe-instances":
        return _result("aws", "awscli", command, "ec2", "DescribeInstances", "GET /api/ec2/instances", args, "List simulator EC2 instances.")
    if len(args) >= 2 and args[0] == "ec2" and args[1] == "run-instances":
        return _result("aws", "awscli", command, "ec2", "RunInstances", "POST /api/ec2/instances", args, "Launch an EC2 instance locally.")
    if len(args) >= 2 and args[0] == "lambda" and args[1] == "list-functions":
        return _result("aws", "awscli", command, "lambda", "ListFunctions", "GET /api/lambda/functions", args, "List simulator Lambda functions.")
    return _result("aws", "awscli", command, "", "", "", args, "No translation rule exists yet.")


def gcp_gcloud_resolve(command: str) -> dict[str, Any]:
    tokens = shlex.split(command or "")
    if not tokens or tokens[0] != "gcloud":
        return _result("gcp", "gcloud", command, "", "", "", tokens, "Command must start with `gcloud`.")
    args = tokens[1:]
    if len(args) >= 3 and args[0] == "compute" and args[1] == "instances" and args[2] == "list":
        return _result("gcp", "gcloud", command, "compute", "instances.list", "GET /compute/v1/projects/{project}/zones/{zone}/instances", args, "List Compute Engine instances in the local simulator.")
    if len(args) >= 3 and args[0] == "compute" and args[1] == "instances" and args[2] == "create":
        return _result("gcp", "gcloud", command, "compute", "instances.insert", "POST /compute/v1/projects/{project}/zones/{zone}/instances", args, "Create a Compute Engine instance locally.")
    if len(args) >= 3 and args[0] == "compute" and args[1] == "instances" and args[2] == "describe":
        return _result("gcp", "gcloud", command, "compute", "instances.get", "GET /compute/v1/projects/{project}/zones/{zone}/instances/{instance}", args, "Describe a Compute Engine instance locally.")
    if len(args) >= 3 and args[0] == "compute" and args[1] == "instances" and args[2] == "start":
        return _result("gcp", "gcloud", command, "compute", "instances.start", "POST /compute/v1/projects/{project}/zones/{zone}/instances/{instance}/start", args, "Start a Compute Engine instance locally.")
    if len(args) >= 3 and args[0] == "compute" and args[1] == "instances" and args[2] == "stop":
        return _result("gcp", "gcloud", command, "compute", "instances.stop", "POST /compute/v1/projects/{project}/zones/{zone}/instances/{instance}/stop", args, "Stop a Compute Engine instance locally.")
    if len(args) >= 3 and args[0] == "compute" and args[1] == "instances" and args[2] == "delete":
        return _result("gcp", "gcloud", command, "compute", "instances.delete", "DELETE /compute/v1/projects/{project}/zones/{zone}/instances/{instance}", args, "Delete a Compute Engine instance locally.")
    if len(args) >= 3 and args[0] == "storage" and args[1] == "buckets" and args[2] == "list":
        return _result("gcp", "gcloud", command, "storage", "buckets.list", "GET /storage/v1/b", args, "List Cloud Storage buckets locally.")
    if len(args) >= 3 and args[0] == "sql" and args[1] == "instances" and args[2] == "list":
        return _result("gcp", "gcloud", command, "sql", "instances.list", "GET /sql/v1beta4/projects/{project}/instances", args, "List Cloud SQL instances locally.")
    if len(args) >= 3 and args[0] == "pubsub" and args[1] == "topics" and args[2] == "list":
        return _result("gcp", "gcloud", command, "pubsub", "topics.list", "GET /v1/projects/{project}/topics", args, "List Pub/Sub topics locally.")
    return _result("gcp", "gcloud", command, "", "", "", args, "No translation rule exists yet.")


def gcp_gcutil_resolve(command: str) -> dict[str, Any]:
    tokens = shlex.split(command or "")
    if not tokens or tokens[0] != "gcutil":
        return _result("gcp", "gcutil", command, "", "", "", tokens, "Command must start with `gcutil`.")
    args = tokens[1:]
    if args and args[0] == "listinstances":
        return _result("gcp", "gcutil", command, "compute", "instances.list", "GET /compute/v1/projects/{project}/zones/{zone}/instances", args, "Legacy gcutil instance listing.")
    if args and args[0] == "addinstance":
        return _result("gcp", "gcutil", command, "compute", "instances.insert", "POST /compute/v1/projects/{project}/zones/{zone}/instances", args, "Legacy gcutil instance creation.")
    if args and args[0] == "getinstance":
        return _result("gcp", "gcutil", command, "compute", "instances.get", "GET /compute/v1/projects/{project}/zones/{zone}/instances/{instance}", args, "Legacy gcutil instance description.")
    if args and args[0] == "startinstance":
        return _result("gcp", "gcutil", command, "compute", "instances.start", "POST /compute/v1/projects/{project}/zones/{zone}/instances/{instance}/start", args, "Legacy gcutil instance start.")
    if args and args[0] == "stopinstance":
        return _result("gcp", "gcutil", command, "compute", "instances.stop", "POST /compute/v1/projects/{project}/zones/{zone}/instances/{instance}/stop", args, "Legacy gcutil instance stop.")
    if args and args[0] == "delinstance":
        return _result("gcp", "gcutil", command, "compute", "instances.delete", "DELETE /compute/v1/projects/{project}/zones/{zone}/instances/{instance}", args, "Legacy gcutil instance deletion.")
    return _result("gcp", "gcutil", command, "", "", "", args, "No translation rule exists yet.")


def sdk_snippet(provider: str, language: str) -> dict[str, Any]:
    provider = provider.lower()
    language = language.lower()
    endpoint = "http://127.0.0.1:9000"
    if provider == "aws" and language == "java":
        return {
            "provider": "aws",
            "language": "java",
            "endpoint": endpoint,
            "snippet": """S3Client client = S3Client.builder()
    .endpointOverride(URI.create("http://127.0.0.1:9000"))
    .region(Region.US_EAST_1)
    .credentialsProvider(StaticCredentialsProvider.create(AwsBasicCredentials.create("test", "test")))
    .build();""",
        }
    if provider == "aws" and language == "go":
        return {
            "provider": "aws",
            "language": "go",
            "endpoint": endpoint,
            "snippet": """cfg, _ := config.LoadDefaultConfig(context.TODO(),
    config.WithRegion("us-east-1"),
    config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider("test", "test")),
)
client := s3.NewFromConfig(cfg, func(o *s3.Options) {
    o.BaseEndpoint = aws.String("http://127.0.0.1:9000")
})""",
        }
    if provider == "gcp" and language == "java":
        return {
            "provider": "gcp",
            "language": "java",
            "endpoint": endpoint,
            "snippet": """Storage storage = StorageOptions.newBuilder()
    .setHost("http://127.0.0.1:9000")
    .setProjectId("cloudlearn")
    .build()
    .getService();""",
        }
    if provider == "gcp" and language == "go":
        return {
            "provider": "gcp",
            "language": "go",
            "endpoint": endpoint,
            "snippet": """client, _ := storage.NewClient(ctx,
    option.WithEndpoint("http://127.0.0.1:9000"),
    option.WithoutAuthentication(),
)""",
        }
    return {"provider": provider, "language": language, "endpoint": endpoint, "snippet": "", "status": "planned"}
