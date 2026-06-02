"""Route modules extracted from the server.py monolith.

Each module follows the pattern:

    from routes import aws_ec2
    aws_ec2.register(app)

Modules:
    aws_ec2       - EC2 instance CRUD, AMI catalog, runtime, console, WebSocket
    aws_vpc       - VPC, subnet, security group, route table, IGW
    aws_rds       - RDS database CRUD, snapshots, parameter groups, subnet groups
    aws_lambda    - Lambda function CRUD, invocation, versioning, permissions
    aws_sqs       - SQS queue CRUD, message send/receive/delete, query API
    aws_apigw     - API Gateway REST API CRUD, deployment, stages, invocation
    aws_dynamodb  - DynamoDB table CRUD, item ops, query/scan, tagging, JSON-RPC
    aws_s3        - S3 REST API (bucket/object CRUD, versioning, multipart, notifications)
    aws_extras    - AWS rail extras stub-driven CRUD (EBS, EIP, key pairs, etc.)
    gcp_extras    - GCP rail extras stub-driven CRUD + API Gateway handlers
    gcp_console   - GCP console summary, consolidation, VPC reconcile, enforcement
    spaces        - Simulation-space CRUD, providers, runtime budget, cloud-shell, CI
    runtime       - Runtime bundles, deployments, service-action router
    console       - Console pages, docs, healthz, startup, /ui, /product
    tenants       - Tenant CRUD, switch, active tenant
    config        - Audit sinks, notifications, custom domain, branding, SSO, scaffolding, xt-rbac, helm
    licensing     - Catalog, packs, providers, license signup/status/activate, host info, budget toggle
    terraform     - Terraform export, import, status, plan, apply
    azure_console - Azure console summary
    cloudsim      - CloudSim current, summary, reconcile, events
"""
