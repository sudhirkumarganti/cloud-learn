from __future__ import annotations

from .._shared import build_pack

PACK = build_pack(
    "cloudlearn.aws.sdk.java.basic",
    "tooling",
    "1.0.0",
    "aws",
    {
        "protocol": "aws-like",
        "actions": ["AmazonS3", "AmazonEC2", "AmazonDynamoDB", "AmazonSQS", "AmazonRDS", "AWSLambda", "AmazonApiGateway", "AmazonVPC"],
        "requestSchemas": True,
        "responseSchemas": True,
        "errors": True,
        "pagination": True,
        "regionAware": True,
        "language": "java",
        "sdk": "aws-java-sdk-v2",
    },
)
