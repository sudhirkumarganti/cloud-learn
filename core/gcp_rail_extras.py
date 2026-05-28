"""Schemas for GCP console rail items + new services (Eventarc, Secret
Manager, Cloud KMS) backed by the generic /api/gcp/extras endpoints.

Mirrors :mod:`core.aws_rail_extras`. Three categories:
* ``crud``      → filterable table with Create + Delete (per-space items)
* ``analytics`` → read-only (synthesized or derived data)
* ``config``    → single editable record (PUT replaces)
"""
from __future__ import annotations


def crud(label, icon, description, columns, create_fields, seed=None):
    return {"label": label, "icon": icon, "category": "crud",
            "description": description, "columns": columns,
            "create_fields": create_fields, "seed": seed or []}


def analytics(label, icon, description, columns, seed=None, sparklines=None):
    return {"label": label, "icon": icon, "category": "analytics",
            "description": description, "columns": columns or [],
            "seed": seed or [], "sparklines": sparklines or []}


_TIME = "2025-11-01T12:00:00Z"


# ============================================================================
# Eventarc — triggers + channels
# ============================================================================
_EVENTARC = {
    "triggers": crud(
        "Triggers", "rule",
        "Triggers route events from Google Cloud services or third-party providers to destinations (Cloud Run, GKE, Workflows).",
        [["name","Name"],["event_provider","Event provider"],["destination","Destination"],
         ["region","Region"],["state","State"]],
        [{"name":"name","label":"Trigger name","required":True,
          "validate":{"regex":r"^[a-z][a-z0-9-]{0,62}$",
                      "message":"lowercase letters, digits, hyphens; start with a letter"}},
         {"name":"event_provider","label":"Event provider","type":"select","default":"google.cloud.pubsub.topic.v1.messagePublished",
          "options":[{"value":"google.cloud.pubsub.topic.v1.messagePublished","label":"Cloud Pub/Sub"},
                     {"value":"google.cloud.storage.object.v1.finalized","label":"Cloud Storage — object finalized"},
                     {"value":"google.cloud.firestore.document.v1.created","label":"Firestore — document created"},
                     {"value":"google.cloud.bigquery.v2.job.completed","label":"BigQuery — job completed"},
                     {"value":"google.cloud.scheduler.v1.jobs.execute","label":"Cloud Scheduler"}]},
         {"name":"destination","label":"Destination resource","required":True,
          "default":"projects/cloudlearn/locations/us-central1/services/my-service"},
         {"name":"region","label":"Region","default":"us-central1"}],
        seed=[
            {"name":"on-storage-upload","event_provider":"google.cloud.storage.object.v1.finalized",
             "destination":"my-cloud-run-service","region":"us-central1","state":"ACTIVE"},
        ]),
    "channels": crud(
        "Channels", "hub",
        "Channels deliver events from third-party providers (Datadog, Confluent, etc.) into Eventarc.",
        [["name","Name"],["provider","Provider"],["state","State"]],
        [{"name":"name","label":"Channel name","required":True},
         {"name":"provider","label":"Third-party provider","required":True,
          "default":"datadog.com/v1/datadog"}]),
    "providers": analytics(
        "Event providers", "list",
        "All event providers available in this region (read-only catalog).",
        [["provider","Provider"],["event_types","Event types"],["category","Category"]],
        seed=[
            {"provider":"google.cloud.pubsub.topic","event_types":"messagePublished","category":"Google Cloud"},
            {"provider":"google.cloud.storage.object","event_types":"finalized, deleted, archived","category":"Google Cloud"},
            {"provider":"google.cloud.firestore.document","event_types":"created, updated, deleted","category":"Google Cloud"},
            {"provider":"google.cloud.bigquery","event_types":"jobCompleted","category":"Google Cloud"},
            {"provider":"google.cloud.scheduler","event_types":"jobs.execute","category":"Google Cloud"},
        ]),
}


# ============================================================================
# Secret Manager — secrets + versions + rotation
# ============================================================================
_SECRETMANAGER = {
    "secrets": crud(
        "Secrets", "key",
        "Encrypted secrets stored at rest with Google-managed or customer-managed encryption keys (CMEK).",
        [["name","Name"],["replication","Replication"],["created","Created"],
         ["latest_version","Latest version"]],
        [{"name":"name","label":"Name","required":True,
          "validate":{"regex":r"^[A-Za-z0-9_-]{1,255}$","message":"1-255 chars; letters, digits, _-"}},
         {"name":"replication","label":"Replication policy","type":"radio","default":"automatic",
          "options":[{"value":"automatic","label":"Automatic (recommended)"},
                     {"value":"user-managed","label":"User-managed (pick specific regions)"}]},
         {"name":"regions","label":"User-managed regions (comma-separated)",
          "default":"us-central1,us-east1",
          "ifEquals":{"replication":"user-managed"}},
         {"name":"secret_value","label":"Secret value","type":"password",
          "validate":{"regex":r"^.{1,65535}$","message":"1-65535 chars"}}],
        seed=[
            {"name":"prod-db-password","replication":"automatic","created":_TIME,"latest_version":"v3"},
            {"name":"stripe-api-key","replication":"automatic","created":_TIME,"latest_version":"v1"},
        ]),
    "versions": analytics(
        "Versions", "history",
        "All versions across all secrets in this project. Older versions can be disabled or destroyed.",
        [["secret","Secret"],["version","Version"],["state","State"],
         ["created","Created"],["destroyed","Destroyed"]],
        seed=[
            {"secret":"prod-db-password","version":"v3","state":"ENABLED",
             "created":_TIME,"destroyed":"—"},
            {"secret":"prod-db-password","version":"v2","state":"DISABLED",
             "created":"2025-10-15T00:00:00Z","destroyed":"—"},
            {"secret":"prod-db-password","version":"v1","state":"DESTROYED",
             "created":"2025-09-01T00:00:00Z","destroyed":"2025-10-15T00:00:00Z"},
        ]),
    "rotation": crud(
        "Rotation", "autorenew",
        "Automatic rotation schedules — re-create secret versions on a cadence via Cloud Functions.",
        [["secret","Secret"],["rotation_period","Period"],["next_rotation","Next rotation"]],
        [{"name":"secret","label":"Secret name","required":True},
         {"name":"rotation_period","label":"Rotation period (seconds)","type":"number","default":2592000,
          "validate":{"min":86400,"max":31536000}}]),
}


# ============================================================================
# Cloud KMS — key rings + keys
# ============================================================================
_KMS = {
    "keys": crud(
        "Keys", "key",
        "Cryptographic keys for encrypt/decrypt/sign/verify. Organized into key rings by region.",
        [["name","Key name"],["keyring","Key ring"],["purpose","Purpose"],
         ["algorithm","Algorithm"],["protection","Protection level"],["state","State"]],
        [{"name":"name","label":"Key name","required":True,
          "validate":{"regex":r"^[a-zA-Z0-9_-]{1,63}$","message":"1-63 chars"}},
         {"name":"keyring","label":"Key ring","required":True,"default":"my-keyring"},
         {"name":"purpose","label":"Purpose","type":"select","default":"ENCRYPT_DECRYPT",
          "options":[{"value":"ENCRYPT_DECRYPT","label":"Symmetric encrypt/decrypt"},
                     {"value":"ASYMMETRIC_DECRYPT","label":"Asymmetric decrypt"},
                     {"value":"ASYMMETRIC_SIGN","label":"Asymmetric sign"},
                     {"value":"MAC","label":"MAC"}]},
         {"name":"algorithm","label":"Algorithm","type":"select","default":"GOOGLE_SYMMETRIC_ENCRYPTION",
          "options":[{"value":"GOOGLE_SYMMETRIC_ENCRYPTION","label":"GOOGLE_SYMMETRIC_ENCRYPTION"},
                     {"value":"AES_256_GCM","label":"AES-256-GCM"},
                     {"value":"RSA_DECRYPT_OAEP_3072_SHA256","label":"RSA-3072 OAEP SHA256"},
                     {"value":"RSA_SIGN_PSS_3072_SHA256","label":"RSA-3072 PSS SHA256"},
                     {"value":"EC_SIGN_P256_SHA256","label":"EC P-256 SHA256"}]},
         {"name":"protection","label":"Protection level","type":"select","default":"SOFTWARE",
          "options":[{"value":"SOFTWARE","label":"Software"},
                     {"value":"HSM","label":"HSM"},
                     {"value":"EXTERNAL","label":"External"}]},
         {"name":"rotation_period","label":"Rotation period (days)","type":"number","default":90,
          "validate":{"min":1,"max":365}}],
        seed=[
            {"name":"app-encryption-key","keyring":"my-keyring","purpose":"ENCRYPT_DECRYPT",
             "algorithm":"GOOGLE_SYMMETRIC_ENCRYPTION","protection":"SOFTWARE","state":"ENABLED"},
        ]),
    "keyrings": crud(
        "Key rings", "vpn_lock",
        "Logical groupings of keys, scoped to a region.",
        [["name","Name"],["location","Location"],["key_count","Keys"]],
        [{"name":"name","label":"Key ring name","required":True},
         {"name":"location","label":"Location","required":True,"default":"us-central1"}],
        seed=[
            {"name":"my-keyring","location":"us-central1","key_count":"1"},
        ]),
    "keyversions": analytics(
        "Key versions", "history",
        "Version history of all keys. Older versions can be disabled or destroyed.",
        [["key","Key"],["version","Version"],["state","State"],["created","Created"]],
        seed=[
            {"key":"app-encryption-key","version":"1","state":"ENABLED","created":_TIME},
        ]),
    "importJobs": crud(
        "Import jobs", "upload",
        "Wrapping jobs that bring your own key material into Cloud KMS.",
        [["name","Name"],["state","State"],["created","Created"],["expire_time","Expires"]],
        [{"name":"name","label":"Import job name","required":True},
         {"name":"protection","label":"Target protection level","type":"select","default":"HSM",
          "options":[{"value":"HSM","label":"HSM"},{"value":"SOFTWARE","label":"SOFTWARE"}]}]),
    "ekmConnections": crud(
        "EKM connections", "vpn_key",
        "External Key Manager connections — keep keys in a third-party HSM.",
        [["name","Name"],["service_resolvers","Service resolvers"],["state","State"]],
        [{"name":"name","label":"Connection name","required":True}]),
}


# ============================================================================
# Combined registry — keyed by "<service>/<stub-key>"
# ============================================================================
def _flatten(svc_dict, svc):
    return {f"{svc}/{k}": v for k, v in svc_dict.items()}


EXTRAS: dict[str, dict] = {
    **_flatten(_EVENTARC, "eventarc"),
    **_flatten(_SECRETMANAGER, "secretmanager"),
    **_flatten(_KMS, "kms"),
}
