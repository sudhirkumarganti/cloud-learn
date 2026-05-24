#!/usr/bin/env python3
"""
CloudLearn conformance harness.

Points the *real* AWS SDK (boto3) at the simulator and exercises real client
lifecycles. This is the judge for fidelity work: it tells us whether an
unmodified application can deploy/test/validate against the sim.

Usage:
    .venv/bin/python tests/conformance/run_conformance.py [--endpoint URL] [--service s3,iam,ec2]

Exit code is non-zero if any check FAILs (errors that would break a real client).
Shape DEVIATIONS (a real client tolerated it, but it diverges from the provider
contract) are reported as warnings and do not fail the run.
"""
from __future__ import annotations

import argparse
import sys
import traceback
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError

PASS, FAIL, WARN, SKIP = "PASS", "FAIL", "WARN", "SKIP"
RESULTS: list[tuple[str, str, str, str]] = []  # (service, check, status, note)


def record(service: str, check: str, status: str, note: str = "") -> None:
    RESULTS.append((service, check, status, note))
    icon = {PASS: "✓", FAIL: "✗", WARN: "!", SKIP: "-"}[status]
    print(f"  [{icon}] {service}:{check} {status}" + (f" — {note}" if note else ""))


def client(service: str, endpoint: str):
    cfg = Config(
        region_name="us-east-1",
        signature_version="v4",
        retries={"max_attempts": 1, "mode": "standard"},
        s3={"addressing_style": "path"},
    )
    return boto3.client(
        service,
        endpoint_url=endpoint,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        config=cfg,
    )


# ---------------------------------------------------------------- S3 (data plane)
def check_s3(endpoint: str) -> None:
    print("\n== S3 (control + data plane) ==")
    s3 = client("s3", endpoint)
    bucket = f"conf-{uuid.uuid4().hex[:12]}"
    key = "hello/world.txt"
    body = b"cloudlearn-conformance-payload"

    try:
        s3.list_buckets()
        record("s3", "ListBuckets", PASS)
    except Exception as exc:  # noqa: BLE001
        record("s3", "ListBuckets", FAIL, repr(exc))

    try:
        s3.create_bucket(Bucket=bucket)
        record("s3", "CreateBucket", PASS)
    except Exception as exc:  # noqa: BLE001
        record("s3", "CreateBucket", FAIL, repr(exc))
        return

    # read-after-write: the new bucket must appear
    try:
        names = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
        record("s3", "CreateBucket.readAfterWrite", PASS if bucket in names else FAIL,
               "" if bucket in names else "bucket missing from ListBuckets after create")
    except Exception as exc:  # noqa: BLE001
        record("s3", "CreateBucket.readAfterWrite", FAIL, repr(exc))

    # idempotency: AWS returns 200/BucketAlreadyOwnedByYou for same-owner re-create
    try:
        s3.create_bucket(Bucket=bucket)
        record("s3", "CreateBucket.idempotent", PASS)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        ok = code in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}
        record("s3", "CreateBucket.idempotent", PASS if ok else WARN,
               f"re-create returned {code or 'error'} (AWS: 200 or BucketAlreadyOwnedByYou)")

    # data plane: PUT object
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=body)
        record("s3", "PutObject", PASS)
    except Exception as exc:  # noqa: BLE001
        record("s3", "PutObject", FAIL, repr(exc))

    # data plane: GET object must return the exact bytes
    try:
        got = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        record("s3", "GetObject.bytes", PASS if got == body else FAIL,
               "" if got == body else f"body mismatch: {got!r}")
    except Exception as exc:  # noqa: BLE001
        record("s3", "GetObject.bytes", FAIL, repr(exc))

    try:
        h = s3.head_object(Bucket=bucket, Key=key)
        clen = int(h.get("ContentLength", -1))
        record("s3", "HeadObject.ContentLength", PASS if clen == len(body) else WARN,
               "" if clen == len(body) else f"ContentLength={clen}, expected {len(body)}")
    except Exception as exc:  # noqa: BLE001
        record("s3", "HeadObject", FAIL, repr(exc))

    try:
        lo = s3.list_objects_v2(Bucket=bucket)
        keys = [o["Key"] for o in lo.get("Contents", [])]
        record("s3", "ListObjectsV2", PASS if key in keys else FAIL,
               "" if key in keys else f"key not listed; got {keys}")
    except Exception as exc:  # noqa: BLE001
        record("s3", "ListObjectsV2", FAIL, repr(exc))

    # error shape: GET a missing key must raise NoSuchKey
    try:
        s3.get_object(Bucket=bucket, Key="does/not/exist")
        record("s3", "GetObject.404", FAIL, "missing key did not raise")
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        record("s3", "GetObject.404", PASS if code == "NoSuchKey" else WARN,
               f"got {code} (AWS: NoSuchKey)")
    except Exception as exc:  # noqa: BLE001
        record("s3", "GetObject.404", FAIL, repr(exc))

    # error shape: HEAD/GET a missing bucket
    try:
        client("s3", endpoint).get_object(Bucket=f"missing-{uuid.uuid4().hex[:8]}", Key="x")
        record("s3", "GetObject.NoSuchBucket", FAIL, "missing bucket did not raise")
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        record("s3", "GetObject.NoSuchBucket", PASS if code == "NoSuchBucket" else WARN,
               f"got {code} (AWS: NoSuchBucket)")
    except Exception as exc:  # noqa: BLE001
        record("s3", "GetObject.NoSuchBucket", FAIL, repr(exc))

    # cleanup
    try:
        s3.delete_object(Bucket=bucket, Key=key)
        record("s3", "DeleteObject", PASS)
    except Exception as exc:  # noqa: BLE001
        record("s3", "DeleteObject", FAIL, repr(exc))
    try:
        s3.delete_bucket(Bucket=bucket)
        record("s3", "DeleteBucket", PASS)
    except Exception as exc:  # noqa: BLE001
        record("s3", "DeleteBucket", FAIL, repr(exc))


# ---------------------------------------------------------------- IAM (control plane)
def check_iam(endpoint: str) -> None:
    print("\n== IAM (control plane) ==")
    iam = client("iam", endpoint)
    uname = f"conf-user-{uuid.uuid4().hex[:8]}"
    try:
        iam.list_users()
        record("iam", "ListUsers", PASS)
    except Exception as exc:  # noqa: BLE001
        record("iam", "ListUsers", FAIL, repr(exc))
    try:
        resp = iam.create_user(UserName=uname)
        arn = resp.get("User", {}).get("Arn", "")
        ok = arn.startswith("arn:aws:iam::") and arn.endswith(f":user/{uname}")
        record("iam", "CreateUser.arn", PASS if ok else WARN, f"arn={arn!r}")
    except Exception as exc:  # noqa: BLE001
        record("iam", "CreateUser", FAIL, repr(exc))
    try:
        names = [u["UserName"] for u in iam.list_users().get("Users", [])]
        record("iam", "CreateUser.readAfterWrite", PASS if uname in names else FAIL,
               "" if uname in names else "user missing after create")
    except Exception as exc:  # noqa: BLE001
        record("iam", "CreateUser.readAfterWrite", FAIL, repr(exc))
    try:
        iam.delete_user(UserName=uname)
        record("iam", "DeleteUser", PASS)
    except Exception as exc:  # noqa: BLE001
        record("iam", "DeleteUser", WARN, repr(exc))


# ---------------------------------------------------------------- EC2 (control, light)
def check_ec2(endpoint: str) -> None:
    print("\n== EC2 (control plane, describe-only) ==")
    ec2 = client("ec2", endpoint)
    try:
        ec2.describe_instances()
        record("ec2", "DescribeInstances", PASS)
    except Exception as exc:  # noqa: BLE001
        record("ec2", "DescribeInstances", FAIL, repr(exc))
    try:
        ec2.describe_vpcs()
        record("ec2", "DescribeVpcs", PASS)
    except Exception as exc:  # noqa: BLE001
        record("ec2", "DescribeVpcs", WARN, repr(exc))


# ---------------------------------------------------------------- SQS (data plane)
def check_sqs(endpoint: str) -> None:
    print("\n== SQS (data plane) ==")
    sqs = client("sqs", endpoint)
    qname = f"conf-q-{uuid.uuid4().hex[:8]}"
    try:
        qurl = sqs.create_queue(QueueName=qname)["QueueUrl"]
        record("sqs", "CreateQueue", PASS if qurl else FAIL, f"url={qurl}")
    except Exception as exc:  # noqa: BLE001
        record("sqs", "CreateQueue", FAIL, repr(exc))
        return
    try:
        urls = sqs.list_queues().get("QueueUrls", [])
        record("sqs", "ListQueues", PASS if any(qname in u for u in urls) else WARN, f"{len(urls)} queue(s)")
    except Exception as exc:  # noqa: BLE001
        record("sqs", "ListQueues", FAIL, repr(exc))
    try:
        sqs.send_message(QueueUrl=qurl, MessageBody="hello")
        record("sqs", "SendMessage", PASS)
    except Exception as exc:  # noqa: BLE001
        record("sqs", "SendMessage", FAIL, repr(exc))
    try:
        msgs = sqs.receive_message(QueueUrl=qurl, MaxNumberOfMessages=1).get("Messages", [])
        ok = bool(msgs) and msgs[0].get("Body") == "hello"
        record("sqs", "ReceiveMessage.body", PASS if ok else FAIL, "" if ok else f"got {msgs}")
        if msgs:
            try:
                sqs.delete_message(QueueUrl=qurl, ReceiptHandle=msgs[0]["ReceiptHandle"])
                record("sqs", "DeleteMessage", PASS)
            except Exception as exc:  # noqa: BLE001
                record("sqs", "DeleteMessage", WARN, repr(exc))
    except Exception as exc:  # noqa: BLE001
        record("sqs", "ReceiveMessage", FAIL, repr(exc))
    try:
        sqs.delete_queue(QueueUrl=qurl)
        record("sqs", "DeleteQueue", PASS)
    except Exception as exc:  # noqa: BLE001
        record("sqs", "DeleteQueue", WARN, repr(exc))


# ---------------------------------------------------------------- RDS (control plane)
def check_rds(endpoint: str) -> None:
    print("\n== RDS (control plane) ==")
    rds = client("rds", endpoint)
    dbid = f"conf-db-{uuid.uuid4().hex[:8]}"
    try:
        rds.describe_db_instances()
        record("rds", "DescribeDBInstances", PASS)
    except Exception as exc:  # noqa: BLE001
        record("rds", "DescribeDBInstances", FAIL, repr(exc))
    try:
        rds.create_db_instance(
            DBInstanceIdentifier=dbid, DBInstanceClass="db.t3.micro", Engine="postgres",
            MasterUsername="admin", MasterUserPassword="password123", AllocatedStorage=20,
        )
        record("rds", "CreateDBInstance", PASS)
    except Exception as exc:  # noqa: BLE001
        record("rds", "CreateDBInstance", FAIL, repr(exc))
        return
    try:
        dbs = rds.describe_db_instances(DBInstanceIdentifier=dbid).get("DBInstances", [])
        ok = bool(dbs) and dbs[0].get("DBInstanceIdentifier") == dbid
        record("rds", "CreateDBInstance.readAfterWrite", PASS if ok else FAIL)
    except Exception as exc:  # noqa: BLE001
        record("rds", "DescribeDBInstances.byId", FAIL, repr(exc))
    try:
        rds.delete_db_instance(DBInstanceIdentifier=dbid, SkipFinalSnapshot=True)
        record("rds", "DeleteDBInstance", PASS)
    except Exception as exc:  # noqa: BLE001
        record("rds", "DeleteDBInstance", WARN, repr(exc))


# ---------------------------------------------------------------- DynamoDB (data plane)
def check_dynamodb(endpoint: str) -> None:
    print("\n== DynamoDB (data plane) ==")
    ddb = client("dynamodb", endpoint)
    table = f"conf-t-{uuid.uuid4().hex[:8]}"
    try:
        ddb.list_tables()
        record("dynamodb", "ListTables", PASS)
    except Exception as exc:  # noqa: BLE001
        record("dynamodb", "ListTables", FAIL, repr(exc))
    try:
        ddb.create_table(
            TableName=table,
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
        record("dynamodb", "CreateTable", PASS)
    except Exception as exc:  # noqa: BLE001
        record("dynamodb", "CreateTable", FAIL, repr(exc))
        return
    try:
        ddb.put_item(TableName=table, Item={"id": {"S": "k1"}, "val": {"N": "42"}})
        record("dynamodb", "PutItem", PASS)
    except Exception as exc:  # noqa: BLE001
        record("dynamodb", "PutItem", FAIL, repr(exc))
    try:
        item = ddb.get_item(TableName=table, Key={"id": {"S": "k1"}}).get("Item")
        ok = bool(item) and item.get("val", {}).get("N") == "42"
        record("dynamodb", "GetItem.value", PASS if ok else FAIL, "" if ok else f"got {item}")
    except Exception as exc:  # noqa: BLE001
        record("dynamodb", "GetItem", FAIL, repr(exc))
    try:
        ddb.delete_table(TableName=table)
        record("dynamodb", "DeleteTable", PASS)
    except Exception as exc:  # noqa: BLE001
        record("dynamodb", "DeleteTable", WARN, repr(exc))


# ---------------------------------------------------------------- GCP (native REST lifecycles)
def check_gcp(endpoint: str) -> None:
    import base64 as _b64
    import json as _json
    import urllib.error
    import urllib.request

    print("\n== GCP (native REST lifecycles; Discovery/gcloud-style endpoints) ==")
    project, zone, region, loc, db = "cloudlearn-demo", "us-central1-a", "us-central1", "us-central1", "(default)"

    def call(method: str, path: str, body=None):
        url = endpoint.rstrip("/") + path
        data = _json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            url, data=data, method=method,
            headers={"Content-Type": "application/json", "Authorization": "Bearer fake-token"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status, _json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            try:
                return e.code, _json.loads(e.read().decode() or "{}")
            except Exception:  # noqa: BLE001
                return e.code, {}
        except Exception as e:  # noqa: BLE001
            return 0, {"_err": repr(e)}

    def grade(svc, check, st, ok_cond, note=""):
        status = PASS if ok_cond else (WARN if st and 200 <= st < 500 else FAIL)
        record(svc, check, status, note or f"status={st}")

    # ---- Cloud Storage: bucket + object data plane ----
    bucket = f"conf-gcs-{uuid.uuid4().hex[:8]}"
    st, resp = call("POST", f"/storage/v1/b?project={project}", {"name": bucket})
    grade("gcp.storage", "buckets.insert", st, st in (200, 201) and resp.get("name") == bucket, f"status={st} kind={resp.get('kind')!r}")
    st, resp = call("GET", f"/storage/v1/b?project={project}")
    names = [b.get("name") for b in resp.get("items", [])] if isinstance(resp.get("items"), list) else []
    grade("gcp.storage", "buckets.list", st, bucket in names, f"status={st} kind={resp.get('kind')!r}")
    st, resp = call("POST", f"/storage/v1/b/{bucket}/o?name=hello.txt", {"contents": "hi"})
    grade("gcp.storage", "objects.insert", st, st in (200, 201) and resp.get("name") == "hello.txt", f"status={st} kind={resp.get('kind')!r}")
    st, resp = call("GET", f"/storage/v1/b/{bucket}/o")
    onames = [o.get("name") for o in resp.get("items", [])] if isinstance(resp.get("items"), list) else []
    grade("gcp.storage", "objects.list", st, "hello.txt" in onames, f"status={st}")

    # ---- Compute Engine: networks + instances (control plane, Operation-based) ----
    net = f"conf-net-{uuid.uuid4().hex[:6]}"
    st, resp = call("POST", f"/compute/v1/projects/{project}/global/networks", {"name": net, "autoCreateSubnetworks": False})
    grade("gcp.vpc", "networks.insert", st, st in (200, 201) and (resp.get("kind") in (None, "compute#operation") or resp.get("name")), f"status={st} kind={resp.get('kind')!r}")
    st, resp = call("GET", f"/compute/v1/projects/{project}/global/networks")
    grade("gcp.vpc", "networks.list", st, st == 200 and isinstance(resp.get("items", []), list), f"status={st} kind={resp.get('kind')!r}")
    inst = f"conf-vm-{uuid.uuid4().hex[:6]}"
    body = {
        "name": inst, "machineType": f"zones/{zone}/machineTypes/e2-micro",
        "disks": [{"boot": True, "initializeParams": {"sourceImage": "projects/debian-cloud/global/images/family/debian-12"}}],
        "networkInterfaces": [{"network": f"global/networks/{net}"}],
    }
    st, resp = call("POST", f"/compute/v1/projects/{project}/zones/{zone}/instances", body)
    grade("gcp.compute", "instances.insert", st, st in (200, 201), f"status={st} kind={resp.get('kind')!r}")
    st, resp = call("GET", f"/compute/v1/projects/{project}/zones/{zone}/instances")
    inames = [i.get("name") for i in resp.get("items", [])] if isinstance(resp.get("items"), list) else []
    grade("gcp.compute", "instances.list", st, st == 200, f"status={st} kind={resp.get('kind')!r} found={inst in inames}")

    # ---- Cloud SQL ----
    sql = f"conf-sql-{uuid.uuid4().hex[:6]}"
    st, resp = call("POST", f"/sql/v1beta4/projects/{project}/instances", {"name": sql, "databaseVersion": "POSTGRES_15", "settings": {"tier": "db-f1-micro"}})
    grade("gcp.sql", "instances.insert", st, st in (200, 201), f"status={st} kind={resp.get('kind')!r}")
    st, resp = call("GET", f"/sql/v1beta4/projects/{project}/instances")
    grade("gcp.sql", "instances.list", st, st == 200, f"status={st} kind={resp.get('kind')!r}")

    # ---- Pub/Sub: topic + subscription + publish + pull + ack ----
    topic, sub = f"conf-topic-{uuid.uuid4().hex[:6]}", f"conf-sub-{uuid.uuid4().hex[:6]}"
    st, resp = call("PUT", f"/v1/projects/{project}/topics/{topic}")
    grade("gcp.pubsub", "topics.create", st, st in (200, 201) and str(resp.get("name", "")).endswith(topic), f"status={st}")
    st, resp = call("PUT", f"/v1/projects/{project}/subscriptions/{sub}", {"topic": f"projects/{project}/topics/{topic}"})
    grade("gcp.pubsub", "subscriptions.create", st, st in (200, 201), f"status={st}")
    st, resp = call("POST", f"/v1/projects/{project}/topics/{topic}:publish", {"messages": [{"data": _b64.b64encode(b"hello-pubsub").decode()}]})
    msg_ids = resp.get("messageIds", []) if isinstance(resp, dict) else []
    grade("gcp.pubsub", "topics.publish", st, st == 200 and bool(msg_ids), f"status={st} ids={len(msg_ids)}")
    st, resp = call("POST", f"/v1/projects/{project}/subscriptions/{sub}:pull", {"maxMessages": 1, "returnImmediately": True})
    received = resp.get("receivedMessages", []) if isinstance(resp, dict) else []
    ok_body = bool(received) and _b64.b64decode(received[0].get("message", {}).get("data", "") or "").decode(errors="ignore") == "hello-pubsub"
    grade("gcp.pubsub", "subscriptions.pull", st, ok_body, f"status={st} got={len(received)}")
    if received:
        ack = received[0].get("ackId", "")
        st, _ = call("POST", f"/v1/projects/{project}/subscriptions/{sub}:acknowledge", {"ackIds": [ack]})
        grade("gcp.pubsub", "subscriptions.acknowledge", st, st in (200, 204), f"status={st}")

    # ---- Firestore: document create + get ----
    coll = "conf"
    st, resp = call("POST", f"/firestore/v1/projects/{project}/databases/{db}/documents/{coll}", {"fields": {"k": {"stringValue": "v"}}})
    grade("gcp.firestore", "documents.create", st, st in (200, 201) and "name" in resp, f"status={st}")
    st, resp = call("GET", f"/firestore/v1/projects/{project}/databases/{db}/documents/{coll}")
    grade("gcp.firestore", "documents.list", st, st == 200, f"status={st}")

    # ---- Cloud Functions ----
    fn = f"conf-fn-{uuid.uuid4().hex[:6]}"
    st, resp = call("POST", f"/v1/projects/{project}/locations/{loc}/functions", {"name": f"projects/{project}/locations/{loc}/functions/{fn}", "entryPoint": "main", "runtime": "python311"})
    grade("gcp.functions", "functions.create", st, st in (200, 201), f"status={st}")
    st, resp = call("GET", f"/v1/projects/{project}/locations/{loc}/functions")
    grade("gcp.functions", "functions.list", st, st == 200, f"status={st}")

    # ---- IAM: service accounts + project policy ----
    sa = f"conf-sa-{uuid.uuid4().hex[:6]}"
    st, resp = call("POST", f"/v1/projects/{project}/serviceAccounts", {"accountId": sa})
    grade("gcp.iam", "serviceAccounts.create", st, st in (200, 201), f"status={st}")
    st, resp = call("GET", f"/v1/projects/{project}/serviceAccounts")
    grade("gcp.iam", "serviceAccounts.list", st, st == 200, f"status={st}")
    st, resp = call("POST", f"/v1/projects/{project}:getIamPolicy")
    grade("gcp.iam", "getIamPolicy", st, st == 200 and "bindings" in resp, f"status={st}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="http://127.0.0.1:9000")
    ap.add_argument("--service", default="s3,iam,ec2,sqs,rds,dynamodb,gcp")
    args = ap.parse_args()

    print(f"CloudLearn conformance harness -> {args.endpoint}")
    services = [s.strip() for s in args.service.split(",") if s.strip()]
    runners = {
        "s3": check_s3, "iam": check_iam, "ec2": check_ec2,
        "sqs": check_sqs, "rds": check_rds, "dynamodb": check_dynamodb, "gcp": check_gcp,
    }
    for svc in services:
        runner = runners.get(svc)
        if not runner:
            record(svc, "(unknown service)", SKIP)
            continue
        try:
            runner(args.endpoint)
        except EndpointConnectionError as exc:
            record(svc, "(connect)", FAIL, repr(exc))
        except Exception:  # noqa: BLE001
            record(svc, "(harness error)", FAIL, traceback.format_exc().splitlines()[-1])

    # scoreboard
    print("\n==================== PARITY SCOREBOARD ====================")
    by_svc: dict[str, dict[str, int]] = {}
    for svc, _check, status, _note in RESULTS:
        by_svc.setdefault(svc, {PASS: 0, FAIL: 0, WARN: 0, SKIP: 0})
        by_svc[svc][status] += 1
    total = {PASS: 0, FAIL: 0, WARN: 0, SKIP: 0}
    for svc, counts in by_svc.items():
        gradable = counts[PASS] + counts[FAIL] + counts[WARN]
        pct = (100.0 * counts[PASS] / gradable) if gradable else 0.0
        print(f"  {svc:6s}  parity {pct:5.1f}%   "
              f"pass={counts[PASS]} warn(deviation)={counts[WARN]} fail={counts[FAIL]}")
        for k in total:
            total[k] += counts[k]
    gradable = total[PASS] + total[FAIL] + total[WARN]
    overall = (100.0 * total[PASS] / gradable) if gradable else 0.0
    print(f"  ----  OVERALL parity {overall:5.1f}%  "
          f"pass={total[PASS]} warn={total[WARN]} fail={total[FAIL]} skip={total[SKIP]}")
    print("===========================================================")
    return 1 if total[FAIL] else 0


if __name__ == "__main__":
    raise SystemExit(main())
