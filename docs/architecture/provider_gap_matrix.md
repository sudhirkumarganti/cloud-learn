# CloudLearn Provider Gap Matrix

This matrix tracks provider service coverage, console parity, and client/library compatibility for the simulator.

## AWS

| Surface | Status | Notes |
|---|---|---|
| Core AWS services | Integrated | EC2, S3, IAM, VPC, RDS, Lambda, SQS, DynamoDB, API Gateway are present. |
| AWS CLI | Integrated | Local AWS-style REST/query surfaces and request translators are available. |
| Boto3 / botocore | Partial | Service routes exist; full client request-shape parity is still pending. |
| Java SDK | Partial | SDK snippet and endpoint metadata are exposed, but full client compatibility glue is still missing. |
| Go SDK | Partial | SDK snippet and endpoint metadata are exposed, but full client compatibility glue is still missing. |
| Console UX | Partial | Main flows are close, but not all views match AWS console behavior exactly. |

## GCP

| Surface | Status | Notes |
|---|---|---|
| Core GCP services | Integrated | Compute Engine, Cloud Storage, Cloud SQL, Pub/Sub, Firestore, Cloud Functions, API Gateway, VPC Network, IAM are present. |
| gcloud / gcutil | Integrated | Native Google-style REST routes and command translators are exposed through the provider tooling layer. |
| Java SDK | Partial | SDK snippet and endpoint metadata are exposed, but exact client compatibility layer is still missing. |
| Go SDK | Partial | SDK snippet and endpoint metadata are exposed, but exact client compatibility layer is still missing. |
| Console UX | Partial | Firestore and Compute Engine are closer; other pages still need provider-native layout refinement. |

## CloudSim Backbone

| Surface | Status | Notes |
|---|---|---|
| Spaces / federation | Integrated | Space isolation, linking, budgets, and reconcile are present. |
| Provider registry / surface registry | Integrated | AWS, Azure, GCP, and Other are separated in metadata and surfaced through the provider matrix API. |
| Provider packs | Integrated | AWS and GCP packs are provider-namespaced; Azure/Other remain reserved surfaces. |
| Provider helpers | Integrated | `providers/aws.py`, `providers/gcp.py`, `providers/capabilities.py`, and `core/tooling_simulators.py` now expose modular provider/tooling entry points. |
| Provider capabilities | Integrated | `/api/providers/{provider}/services` and `/api/providers/{provider}/capabilities` surface the AWS and GCP service catalogs with route maps. |
| Provider routers | Partial | Core service routes still live largely in `server.py`, but provider tooling and capability endpoints now delegate to modular helper modules. |

## Missing Next

- Add strict SDK transport adapters for Java and Go.
- Add AWS CLI and GCP gcloud/gcutil compatibility shims with exact request/response mapping for every command shape.
- Expand advanced AWS and GCP service coverage.
- Tighten remaining provider-specific UX to match official console layouts more closely.
