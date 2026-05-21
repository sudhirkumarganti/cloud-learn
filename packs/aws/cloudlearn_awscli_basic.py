from __future__ import annotations

from .._shared import build_pack

PACK = build_pack(
    "cloudlearn.awscli.basic",
    "tooling",
    "1.0.0",
    "aws",
    {
        "protocol": "aws-like",
        "actions": ["s3", "ec2", "iam", "vpc", "rds", "lambda", "sqs", "dynamodb", "apigateway"],
        "requestSchemas": True,
        "responseSchemas": True,
        "errors": True,
        "pagination": True,
        "regionAware": True,
        "cli": "aws",
        "sdk": "botocore/boto3",
    },
)
