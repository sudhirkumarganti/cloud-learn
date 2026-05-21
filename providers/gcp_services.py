from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request


def _server():
    import server as server_module

    return server_module


TARGETS = [
    "api_gcp_storage_list_buckets",
    "api_gcp_storage_create_bucket",
    "api_gcp_storage_get_bucket",
    "api_gcp_storage_delete_bucket",
    "api_gcp_storage_list_objects",
    "api_gcp_storage_create_object",
    "api_gcp_storage_get_object",
    "api_gcp_storage_delete_object",
    "api_gcp_sql_list_instances",
    "api_gcp_sql_create_instance",
    "api_gcp_sql_get_instance",
    "api_gcp_sql_delete_instance",
    "api_gcp_sql_restart_instance",
    "api_gcp_pubsub_list_topics",
    "api_gcp_pubsub_create_topic",
    "api_gcp_pubsub_get_topic",
    "api_gcp_pubsub_update_topic",
    "api_gcp_pubsub_list_topic_messages",
    "api_gcp_pubsub_delete_topic",
    "api_gcp_pubsub_publish",
    "api_gcp_pubsub_list_subscriptions",
    "api_gcp_pubsub_create_subscription",
    "api_gcp_pubsub_get_subscription",
    "api_gcp_pubsub_list_subscription_messages",
    "api_gcp_pubsub_purge_subscription",
    "api_gcp_pubsub_delete_subscription",
    "api_gcp_pubsub_pull",
    "api_gcp_pubsub_ack",
    "api_gcp_pubsub_modify_ack_deadline",
    "api_gcp_pubsub_list_topic_subscriptions",
    "api_gcp_firestore_list_root_documents",
    "api_gcp_firestore_list_documents",
    "api_gcp_firestore_create_document",
    "api_gcp_firestore_get_document",
    "api_gcp_firestore_delete_document",
    "api_gcp_firestore_update_document",
    "api_gcp_firestore_run_query",
    "api_gcp_functions_list",
    "api_gcp_functions_create",
    "api_gcp_functions_update",
    "api_gcp_functions_publish_version",
    "api_gcp_functions_list_versions",
    "api_gcp_functions_list_invocations",
    "api_gcp_functions_get_policy",
    "api_gcp_functions_set_policy",
    "api_gcp_functions_get",
    "api_gcp_functions_delete",
    "api_gcp_functions_call",
    "api_gcp_apigw_list_apis",
    "api_gcp_apigw_create_api",
    "api_gcp_apigw_get_api",
    "api_gcp_apigw_delete_api",
    "api_gcp_apigw_list_configs",
    "api_gcp_apigw_create_config",
    "api_gcp_apigw_list_gateways",
    "api_gcp_apigw_create_gateway",
    "api_gcp_vpc_list_networks",
    "api_gcp_vpc_create_network",
    "api_gcp_vpc_get_network",
    "api_gcp_vpc_delete_network",
    "api_gcp_vpc_list_subnetworks",
    "api_gcp_vpc_create_subnetwork",
    "api_gcp_vpc_list_firewalls",
    "api_gcp_vpc_create_firewall",
]


def api_gcp_storage_list_buckets(request: Request):
    s = _server()
    project = s._gcp_project_name(request.query_params.get("project"))
    buckets = []
    for bucket in s.gcp_storage_state.get("buckets", {}).values():
        if str(bucket.get("project") or project) != project:
            continue
        buckets.append(s._gcp_storage_bucket_view(project, bucket))
    buckets.sort(key=lambda item: item.get("name", ""))
    return {"kind": "storage#buckets", "items": buckets, "prefixes": [], "nextPageToken": ""}


async def api_gcp_storage_create_bucket(request: Request):
    s = _server()
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    project = s._gcp_project_name(request.query_params.get("project") or payload.get("project") or payload.get("projectId"))
    name = str(payload.get("name") or payload.get("bucket") or "").strip()
    if not name:
        raise HTTPException(400, detail="Bucket name is required")
    bucket = s._gcp_storage_bucket_record(project, name, payload)
    s.gcp_storage_state.setdefault("buckets", {})[name] = bucket
    s.gcp_storage_state.setdefault("objects", {}).setdefault(name, {})
    return s._gcp_storage_bucket_view(project, bucket)


def api_gcp_storage_get_bucket(bucket: str):
    s = _server()
    bucket_rec = s.gcp_storage_state.get("buckets", {}).get(bucket)
    if not bucket_rec:
        raise HTTPException(404, detail="Bucket not found")
    project = str(bucket_rec.get("project") or "cloudlearn")
    return s._gcp_storage_bucket_view(project, bucket_rec)


def api_gcp_storage_delete_bucket(bucket: str):
    s = _server()
    if bucket not in s.gcp_storage_state.get("buckets", {}):
        raise HTTPException(404, detail="Bucket not found")
    s.gcp_storage_state.setdefault("buckets", {}).pop(bucket, None)
    s.gcp_storage_state.setdefault("objects", {}).pop(bucket, None)
    return {"kind": "storage#empty", "deleted": True, "bucket": bucket}


def api_gcp_storage_list_objects(bucket: str, request: Request):
    s = _server()
    bucket_rec = s.gcp_storage_state.get("buckets", {}).get(bucket)
    if not bucket_rec:
        raise HTTPException(404, detail="Bucket not found")
    prefix = str(request.query_params.get("prefix") or "")
    objects = []
    for name, obj in s.gcp_storage_state.get("objects", {}).get(bucket, {}).items():
        if prefix and not name.startswith(prefix):
            continue
        objects.append(s._gcp_storage_object_view(str(bucket_rec.get("project") or "cloudlearn"), bucket, name, obj))
    objects.sort(key=lambda item: item.get("name", ""))
    return {"kind": "storage#objects", "items": objects, "prefixes": [], "nextPageToken": ""}


async def api_gcp_storage_create_object(bucket: str, request: Request):
    s = _server()
    bucket_rec = s.gcp_storage_state.get("buckets", {}).get(bucket)
    if not bucket_rec:
        raise HTTPException(404, detail="Bucket not found")
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    name = str(payload.get("name") or payload.get("object") or "").strip()
    if not name:
        raise HTTPException(400, detail="Object name is required")
    obj = s._gcp_storage_object_record(bucket, name, payload)
    s.gcp_storage_state.setdefault("objects", {}).setdefault(bucket, {})[name] = obj
    return s._gcp_storage_object_view(str(bucket_rec.get("project") or "cloudlearn"), bucket, name, obj)


def api_gcp_storage_get_object(bucket: str, object_name: str):
    s = _server()
    bucket_rec = s.gcp_storage_state.get("buckets", {}).get(bucket)
    obj = s.gcp_storage_state.get("objects", {}).get(bucket, {}).get(object_name)
    if not bucket_rec or not obj:
        raise HTTPException(404, detail="Object not found")
    return s._gcp_storage_object_view(str(bucket_rec.get("project") or "cloudlearn"), bucket, object_name, obj)


def api_gcp_storage_delete_object(bucket: str, object_name: str):
    s = _server()
    if bucket not in s.gcp_storage_state.get("objects", {}) or object_name not in s.gcp_storage_state["objects"][bucket]:
        raise HTTPException(404, detail="Object not found")
    del s.gcp_storage_state["objects"][bucket][object_name]
    return {"kind": "storage#empty", "deleted": True, "bucket": bucket, "object": object_name}


def api_gcp_sql_list_instances(project: str, request: Request):
    s = _server()
    project = s._gcp_project_name(project)
    instances = []
    for inst in s.gcp_sql_state.get("instances", {}).values():
        if str(inst.get("project") or project) != project:
            continue
        instances.append(s._gcp_sql_instance_view(project, inst))
    instances.sort(key=lambda item: item.get("name", ""))
    return {"kind": "sql#instancesList", "items": instances, "warnings": []}


async def api_gcp_sql_create_instance(project: str, request: Request):
    s = _server()
    project = s._gcp_project_name(project)
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    instance = s._gcp_sql_instance_record(project, payload)
    if instance["name"] in s.gcp_sql_state.get("instances", {}):
        raise HTTPException(409, detail="Instance already exists")
    s.gcp_sql_state.setdefault("instances", {})[instance["name"]] = instance
    return s._gcp_sql_instance_view(project, instance)


def api_gcp_sql_get_instance(project: str, instance: str):
    s = _server()
    project = s._gcp_project_name(project)
    rec = s.gcp_sql_state.get("instances", {}).get(instance)
    if not rec or str(rec.get("project") or project) != project:
        raise HTTPException(404, detail="Instance not found")
    return s._gcp_sql_instance_view(project, rec)


def api_gcp_sql_delete_instance(project: str, instance: str):
    s = _server()
    project = s._gcp_project_name(project)
    rec = s.gcp_sql_state.get("instances", {}).get(instance)
    if not rec or str(rec.get("project") or project) != project:
        raise HTTPException(404, detail="Instance not found")
    del s.gcp_sql_state["instances"][instance]
    return {"kind": "sql#operation", "operationType": "DELETE", "status": "DONE", "targetLink": f"{s._gcp_sql_root()}/projects/{project}/instances/{instance}"}


def api_gcp_sql_restart_instance(project: str, instance: str):
    s = _server()
    project = s._gcp_project_name(project)
    rec = s.gcp_sql_state.get("instances", {}).get(instance)
    if not rec or str(rec.get("project") or project) != project:
        raise HTTPException(404, detail="Instance not found")
    rec["state"] = "RUNNABLE"
    rec["updateTime"] = s._now()
    return {"kind": "sql#operation", "operationType": "RESTART", "status": "DONE", "targetLink": f"{s._gcp_sql_root()}/projects/{project}/instances/{instance}"}


def api_gcp_pubsub_list_topics(project: str):
    s = _server()
    project = s._gcp_project_name(project)
    topics = [s._gcp_pubsub_topic_view(project, topic) for topic in s.gcp_pubsub_state.get("topics", {}).values() if str(topic.get("project") or project) == project]
    topics.sort(key=lambda item: item.get("topicId", ""))
    return {"topics": topics, "nextPageToken": "", "kind": "pubsub#topicList"}


async def api_gcp_pubsub_create_topic(project: str, request: Request):
    s = _server()
    project = s._gcp_project_name(project)
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    topic_id = str(payload.get("topicId") or payload.get("name") or payload.get("topic") or "").split("/")[-1].strip()
    if not topic_id:
        raise HTTPException(400, detail="Topic id is required")
    topic = s._gcp_pubsub_topic_record(project, topic_id, payload)
    s.gcp_pubsub_state.setdefault("topics", {})[topic_id] = topic
    default_sub_id = str(payload.get("subscriptionId") or topic_id).split("/")[-1].strip()
    if default_sub_id and default_sub_id not in s.gcp_pubsub_state.setdefault("subscriptions", {}):
        default_sub = s._gcp_pubsub_subscription_record(project, default_sub_id, {"topic": f"projects/{project}/topics/{topic_id}", "labels": payload.get("labels", {}) if isinstance(payload.get("labels"), dict) else {}, "ackDeadlineSeconds": payload.get("ackDeadlineSeconds", 10)})
        s.gcp_pubsub_state.setdefault("subscriptions", {})[default_sub_id] = default_sub
    return s._gcp_pubsub_topic_view(project, topic)


def api_gcp_pubsub_get_topic(project: str, topic: str):
    s = _server()
    project = s._gcp_project_name(project)
    rec = s.gcp_pubsub_state.get("topics", {}).get(topic)
    if not rec or str(rec.get("project") or project) != project:
        raise HTTPException(404, detail="Topic not found")
    return s._gcp_pubsub_topic_view(project, rec)


async def api_gcp_pubsub_update_topic(project: str, topic: str, request: Request):
    s = _server()
    project = s._gcp_project_name(project)
    rec = s.gcp_pubsub_state.get("topics", {}).get(topic)
    if not rec or str(rec.get("project") or project) != project:
        raise HTTPException(404, detail="Topic not found")
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    if isinstance(payload.get("labels"), dict):
        rec["labels"] = payload["labels"]
    if "messageRetentionDuration" in payload:
        rec["messageRetentionDuration"] = str(payload.get("messageRetentionDuration") or rec.get("messageRetentionDuration") or "604800s")
    if "kmsKeyName" in payload:
        rec["kmsKeyName"] = str(payload.get("kmsKeyName") or "")
    rec["updateTime"] = s._now()
    s.gcp_pubsub_state.setdefault("topics", {})[topic] = rec
    return s._gcp_pubsub_topic_view(project, rec)


def api_gcp_pubsub_list_topic_messages(project: str, topic: str):
    s = _server()
    project = s._gcp_project_name(project)
    rec = s.gcp_pubsub_state.get("topics", {}).get(topic)
    if not rec or str(rec.get("project") or project) != project:
        raise HTTPException(404, detail="Topic not found")
    messages = list(s.gcp_pubsub_state.setdefault("messages", {}).get(topic, []))
    return {"messages": messages, "kind": "pubsub#messageList"}


def api_gcp_pubsub_delete_topic(project: str, topic: str):
    s = _server()
    project = s._gcp_project_name(project)
    rec = s.gcp_pubsub_state.get("topics", {}).get(topic)
    if not rec or str(rec.get("project") or project) != project:
        raise HTTPException(404, detail="Topic not found")
    del s.gcp_pubsub_state["topics"][topic]
    for sub_id, sub in list(s.gcp_pubsub_state.get("subscriptions", {}).items()):
        if str(sub.get("project") or project) == project and str(sub.get("topic") or "") == f"projects/{project}/topics/{topic}":
            del s.gcp_pubsub_state["subscriptions"][sub_id]
            s.gcp_pubsub_state.get("messages", {}).pop(sub_id, None)
    s.gcp_pubsub_state.get("messages", {}).pop(topic, None)
    return {"done": True}


async def api_gcp_pubsub_publish(project: str, topic: str, request: Request):
    s = _server()
    project = s._gcp_project_name(project)
    rec = s.gcp_pubsub_state.get("topics", {}).get(topic)
    if not rec or str(rec.get("project") or project) != project:
        raise HTTPException(404, detail="Topic not found")
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    messages = payload.get("messages", []) if isinstance(payload, dict) else []
    if not isinstance(messages, list):
        messages = []
    message_ids = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        message_id = s._id("msg")
        entry = {"messageId": message_id, "data": str(message.get("data") or ""), "attributes": message.get("attributes", {}) if isinstance(message.get("attributes"), dict) else {}, "publishTime": s._now(), "topic": topic}
        message_ids.append(message_id)
        s.gcp_pubsub_state.setdefault("messages", {}).setdefault(topic, []).append(entry)
        for sub in s.gcp_pubsub_state.get("subscriptions", {}).values():
            if str(sub.get("project") or project) != project or str(sub.get("topic") or "") != f"projects/{project}/topics/{topic}":
                continue
            s.gcp_pubsub_state.setdefault("messages", {}).setdefault(str(sub.get("subscriptionId")), []).append({**entry, "ackId": s._id("ack"), "subscription": str(sub.get("subscriptionId"))})
    return {"messageIds": message_ids}


def api_gcp_pubsub_list_subscriptions(project: str):
    s = _server()
    project = s._gcp_project_name(project)
    subs = [s._gcp_pubsub_subscription_view(project, sub) for sub in s.gcp_pubsub_state.get("subscriptions", {}).values() if str(sub.get("project") or project) == project]
    subs.sort(key=lambda item: item.get("subscriptionId", ""))
    return {"subscriptions": subs, "nextPageToken": "", "kind": "pubsub#subscriptionList"}


async def api_gcp_pubsub_create_subscription(project: str, request: Request, queue_name: str = ""):
    s = _server()
    project = s._gcp_project_name(project)
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    sub_id = str(payload.get("subscriptionId") or payload.get("name") or queue_name or "").split("/")[-1].strip()
    if not sub_id:
        raise HTTPException(400, detail="Subscription id is required")
    sub = s._gcp_pubsub_subscription_record(project, sub_id, payload)
    if not sub.get("topic"):
        raise HTTPException(400, detail="Topic is required")
    s.gcp_pubsub_state.setdefault("subscriptions", {})[sub_id] = sub
    return s._gcp_pubsub_subscription_view(project, sub)


def api_gcp_pubsub_get_subscription(project: str, subscription: str):
    s = _server()
    project = s._gcp_project_name(project)
    rec = s.gcp_pubsub_state.get("subscriptions", {}).get(subscription)
    if not rec or str(rec.get("project") or project) != project:
        raise HTTPException(404, detail="Subscription not found")
    return s._gcp_pubsub_subscription_view(project, rec)


def api_gcp_pubsub_list_subscription_messages(project: str, subscription: str):
    s = _server()
    project = s._gcp_project_name(project)
    rec = s.gcp_pubsub_state.get("subscriptions", {}).get(subscription)
    if not rec or str(rec.get("project") or project) != project:
        raise HTTPException(404, detail="Subscription not found")
    messages = list(s.gcp_pubsub_state.setdefault("messages", {}).get(subscription, []))
    return {"receivedMessages": messages, "kind": "pubsub#receivedMessageList"}


def api_gcp_pubsub_purge_subscription(project: str, subscription: str):
    s = _server()
    project = s._gcp_project_name(project)
    rec = s.gcp_pubsub_state.get("subscriptions", {}).get(subscription)
    if not rec or str(rec.get("project") or project) != project:
        raise HTTPException(404, detail="Subscription not found")
    s.gcp_pubsub_state.setdefault("messages", {})[subscription] = []
    return {"done": True}


def api_gcp_pubsub_delete_subscription(project: str, subscription: str):
    s = _server()
    project = s._gcp_project_name(project)
    rec = s.gcp_pubsub_state.get("subscriptions", {}).get(subscription)
    if not rec or str(rec.get("project") or project) != project:
        raise HTTPException(404, detail="Subscription not found")
    del s.gcp_pubsub_state["subscriptions"][subscription]
    s.gcp_pubsub_state.get("messages", {}).pop(subscription, None)
    return {"done": True}


async def api_gcp_pubsub_pull(project: str, subscription: str, request: Request):
    s = _server()
    project = s._gcp_project_name(project)
    rec = s.gcp_pubsub_state.get("subscriptions", {}).get(subscription)
    if not rec or str(rec.get("project") or project) != project:
        raise HTTPException(404, detail="Subscription not found")
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    max_messages = int(payload.get("maxMessages") or payload.get("max_messages") or 10)
    items = list(s.gcp_pubsub_state.get("messages", {}).get(subscription, []))[:max_messages]
    received = []
    for item in items:
        received.append({"ackId": item.get("ackId", s._id("ack")), "message": {"data": item.get("data", ""), "messageId": item.get("messageId", s._id("msg")), "publishTime": item.get("publishTime", s._now()), "attributes": item.get("attributes", {})}})
    return {"receivedMessages": received}


async def api_gcp_pubsub_ack(project: str, subscription: str, request: Request, receipt_handle: str = ""):
    s = _server()
    project = s._gcp_project_name(project)
    if subscription not in s.gcp_pubsub_state.get("subscriptions", {}):
        raise HTTPException(404, detail="Subscription not found")
    body = await request.json() if request is not None else {}
    body = body if isinstance(body, dict) else {}
    ack_ids = body.get("ackIds") if isinstance(body, dict) else []
    if not isinstance(ack_ids, list):
        ack_ids = []
    queue = s.gcp_pubsub_state.setdefault("messages", {}).get(subscription, [])
    s.gcp_pubsub_state.setdefault("messages", {})[subscription] = [item for item in queue if item.get("ackId") not in set(map(str, ack_ids)) and item.get("ackId") != receipt_handle]
    return {"acknowledged": True}


async def api_gcp_pubsub_modify_ack_deadline(project: str, subscription: str, request: Request):
    s = _server()
    project = s._gcp_project_name(project)
    if subscription not in s.gcp_pubsub_state.get("subscriptions", {}):
        raise HTTPException(404, detail="Subscription not found")
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    ack_ids = payload.get("ackIds") if isinstance(payload, dict) else []
    if not isinstance(ack_ids, list):
        ack_ids = []
    ack_ids = [str(ack_id) for ack_id in ack_ids if ack_id]
    deadline = int(payload.get("ackDeadlineSeconds") or 0) if isinstance(payload, dict) else 0
    queue = s.gcp_pubsub_state.setdefault("messages", {}).get(subscription, [])
    if deadline == 0:
        for item in queue:
            if item.get("ackId") in ack_ids:
                item["visibleAt"] = s._now()
                item["inFlight"] = False
    return {}


def api_gcp_pubsub_list_topic_subscriptions(project: str, topic: str):
    s = _server()
    project = s._gcp_project_name(project)
    topic_name = f"projects/{project}/topics/{topic}"
    subscriptions = []
    for sub in s.gcp_pubsub_state.get("subscriptions", {}).values():
        if str(sub.get("project") or project) != project:
            continue
        if str(sub.get("topic") or "") != topic_name:
            continue
        subscriptions.append(f"projects/{project}/subscriptions/{sub.get('subscriptionId') or sub.get('name')}")
    subscriptions.sort()
    return {"subscriptions": subscriptions, "nextPageToken": ""}


def api_gcp_firestore_list_root_documents(project: str, database: str):
    s = _server()
    project = s._gcp_project_name(project)
    database = str(database or "(default)")
    docs = s._gcp_firestore_engine().list_root_documents(project, database)
    return {"documents": docs, "nextPageToken": "", "kind": "firestore#documents"}


def api_gcp_firestore_list_documents(project: str, database: str, collection: str):
    s = _server()
    project = s._gcp_project_name(project)
    database = str(database or "(default)")
    docs = s._gcp_firestore_engine().list_documents(project, database, collection)
    return {"documents": docs, "nextPageToken": "", "kind": "firestore#documents"}


async def api_gcp_firestore_create_document(project: str, database: str, collection: str, request: Request):
    s = _server()
    project = s._gcp_project_name(project)
    database = str(database or "(default)")
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    doc_id = str(payload.get("name") or payload.get("documentId") or s._id("doc"))
    if "/" in doc_id:
        doc_id = doc_id.rsplit("/", 1)[-1]
    fields = payload.get("fields", {}) if isinstance(payload.get("fields"), dict) else {}
    return s._gcp_firestore_engine().create_document(project, database, collection, s._gcp_firestore_normalize_fields(fields), doc_id)


def api_gcp_firestore_get_document(project: str, database: str, collection: str, doc_id: str):
    s = _server()
    project = s._gcp_project_name(project)
    database = str(database or "(default)")
    doc = s._gcp_firestore_engine().get_document(project, database, collection, doc_id)
    if not doc:
        raise HTTPException(404, detail="Document not found")
    return doc


def api_gcp_firestore_delete_document(project: str, database: str, collection: str, doc_id: str):
    s = _server()
    project = s._gcp_project_name(project)
    database = str(database or "(default)")
    try:
        s._gcp_firestore_engine().delete_document(project, database, collection, doc_id)
    except KeyError:
        raise HTTPException(404, detail="Document not found")
    return {"done": True}


async def api_gcp_firestore_update_document(project: str, database: str, collection: str, doc_id: str, request: Request):
    s = _server()
    project = s._gcp_project_name(project)
    database = str(database or "(default)")
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
    try:
        doc = s._gcp_firestore_engine().update_document(project, database, collection, doc_id, s._gcp_firestore_normalize_fields(fields))
    except KeyError:
        raise HTTPException(404, detail="Document not found")
    return doc


async def api_gcp_firestore_run_query(project: str, database: str, request: Request, collection: str = ""):
    s = _server()
    project = s._gcp_project_name(project)
    database = str(database or "(default)")
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    query = payload.get("structuredQuery", {}) if isinstance(payload, dict) else {}
    query = query if isinstance(query, dict) else {}
    selectors = query.get("from", [])
    if collection:
        collection_id = collection
    elif isinstance(selectors, list) and selectors and isinstance(selectors[0], dict):
        collection_id = str(selectors[0].get("collectionId") or "")
    else:
        collection_id = ""
    limit = int(query.get("limit") or payload.get("limit") or 50)
    where = query.get("where") if isinstance(query.get("where"), dict) else {}
    field_name = ""
    field_value = None
    if isinstance(where, dict):
        field_filter = where.get("fieldFilter") if isinstance(where.get("fieldFilter"), dict) else {}
        if isinstance(field_filter, dict):
            field = field_filter.get("field") if isinstance(field_filter.get("field"), dict) else {}
            field_name = str(field.get("fieldPath") or "")
            field_value = s._gcp_firestore_plain_value(field_filter.get("value")) if field_name else None
    return s._gcp_firestore_engine().run_query(project, database, collection_id, field_name=field_name, field_value=field_value, limit=limit)


def api_gcp_functions_list(project: str, location: str = "us-central1"):
    s = _server()
    project = s._gcp_project_name(project)
    location = s._gcp_location_name(location)
    functions = []
    for fn in s.gcp_functions_state.get("functions", {}).values():
        if str(fn.get("project") or project) != project or str(fn.get("location") or location) != location:
            continue
        functions.append(s._gcp_functions_view(project, location, fn))
    functions.sort(key=lambda item: item.get("name", ""))
    return {"functions": functions, "nextPageToken": "", "kind": "cloudfunctions#listFunctionsResponse"}


async def api_gcp_functions_create(project: str, request: Request, location: str = "us-central1"):
    s = _server()
    project = s._gcp_project_name(project)
    location = s._gcp_location_name(location)
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    fn = s._gcp_functions_record(project, location, payload)
    s.gcp_functions_state.setdefault("functions", {})[fn["name"]] = fn
    return s._gcp_functions_view(project, location, fn)


async def api_gcp_functions_update(project: str, location: str, function: str, request: Request):
    s = _server()
    project = s._gcp_project_name(project)
    location = s._gcp_location_name(location)
    fn = s.gcp_functions_state.get("functions", {}).get(function)
    if not fn or str(fn.get("project") or project) != project or str(fn.get("location") or location) != location:
        raise HTTPException(404, detail="Function not found")
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    if "code" in payload:
        fn["code"] = str(payload.get("code") or "")
    if "runtime" in payload:
        fn["runtime"] = str(payload.get("runtime") or fn.get("runtime") or "python311")
        fn.setdefault("buildConfig", {})["runtime"] = fn["runtime"]
    if "handler" in payload:
        fn["entryPoint"] = str(payload.get("handler") or payload.get("entryPoint") or fn.get("entryPoint") or "handler")
        fn.setdefault("buildConfig", {})["entryPoint"] = fn["entryPoint"]
    if "description" in payload:
        fn["description"] = str(payload.get("description") or "")
    if "role" in payload:
        fn["role"] = str(payload.get("role") or "")
    if "timeout" in payload or "timeoutSeconds" in payload:
        timeout = int(payload.get("timeout") or payload.get("timeoutSeconds") or fn.get("serviceConfig", {}).get("timeoutSeconds") or 60)
        fn.setdefault("serviceConfig", {})["timeoutSeconds"] = timeout
        fn["timeout"] = timeout
    if "memory_size" in payload or "availableMemory" in payload:
        memory = str(payload.get("memory_size") or payload.get("availableMemory") or fn.get("serviceConfig", {}).get("availableMemory") or "256M")
        fn.setdefault("serviceConfig", {})["availableMemory"] = memory if memory.endswith("M") or memory.endswith("Mi") else f"{memory}M"
        fn["memory_size"] = int(str(memory).rstrip("MmIi")) if str(memory).rstrip("MmIi").isdigit() else 256
    if isinstance(payload.get("environmentVariables"), dict):
        fn["environmentVariables"] = payload["environmentVariables"]
    if isinstance(payload.get("labels"), dict):
        fn["labels"] = payload["labels"]
    fn["updateTime"] = s._now()
    s.gcp_functions_state.setdefault("functions", {})[function] = fn
    return s._gcp_functions_view(project, location, fn)


async def api_gcp_functions_publish_version(project: str, location: str, function: str, request: Request):
    s = _server()
    project = s._gcp_project_name(project)
    location = s._gcp_location_name(location)
    fn = s.gcp_functions_state.get("functions", {}).get(function)
    if not fn or str(fn.get("project") or project) != project or str(fn.get("location") or location) != location:
        raise HTTPException(404, detail="Function not found")
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    version_id = str(len(fn.get("versions", [])) + 1)
    version = {"version": version_id, "state": "Active", "description": str(payload.get("description") or ""), "created": s._now(), "code_sha256": s._id("sha"), "is_latest": True}
    versions = [v for v in fn.get("versions", []) if isinstance(v, dict)]
    for item in versions:
        item["is_latest"] = False
    versions.append(version)
    fn["versions"] = versions
    fn["updateTime"] = s._now()
    s.gcp_functions_state.setdefault("functions", {})[function] = fn
    return {"version": version}


def api_gcp_functions_list_versions(project: str, location: str, function: str):
    s = _server()
    project = s._gcp_project_name(project)
    location = s._gcp_location_name(location)
    fn = s.gcp_functions_state.get("functions", {}).get(function)
    if not fn or str(fn.get("project") or project) != project or str(fn.get("location") or location) != location:
        raise HTTPException(404, detail="Function not found")
    return {"versions": list(fn.get("versions", []) if isinstance(fn.get("versions"), list) else [])}


def api_gcp_functions_list_invocations(project: str, location: str, function: str):
    s = _server()
    project = s._gcp_project_name(project)
    location = s._gcp_location_name(location)
    fn = s.gcp_functions_state.get("functions", {}).get(function)
    if not fn or str(fn.get("project") or project) != project or str(fn.get("location") or location) != location:
        raise HTTPException(404, detail="Function not found")
    return {"invocations": list(fn.get("invocations", []) if isinstance(fn.get("invocations"), list) else [])}


def api_gcp_functions_get_policy(project: str, location: str, function: str):
    s = _server()
    project = s._gcp_project_name(project)
    location = s._gcp_location_name(location)
    fn = s.gcp_functions_state.get("functions", {}).get(function)
    if not fn or str(fn.get("project") or project) != project or str(fn.get("location") or location) != location:
        raise HTTPException(404, detail="Function not found")
    return {"version": 1, "etag": "", "bindings": fn.get("permissions", []) if isinstance(fn.get("permissions"), list) else []}


async def api_gcp_functions_set_policy(project: str, location: str, function: str, request: Request):
    s = _server()
    project = s._gcp_project_name(project)
    location = s._gcp_location_name(location)
    fn = s.gcp_functions_state.get("functions", {}).get(function)
    if not fn or str(fn.get("project") or project) != project or str(fn.get("location") or location) != location:
        raise HTTPException(404, detail="Function not found")
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    bindings = payload.get("bindings", []) if isinstance(payload.get("bindings"), list) else []
    fn["permissions"] = bindings
    fn["updateTime"] = s._now()
    return {"version": int(payload.get("version") or 1), "etag": str(payload.get("etag") or ""), "bindings": bindings}


def api_gcp_functions_get(project: str, location: str, function: str):
    s = _server()
    project = s._gcp_project_name(project)
    location = s._gcp_location_name(location)
    fn = s.gcp_functions_state.get("functions", {}).get(function)
    if not fn or str(fn.get("project") or project) != project or str(fn.get("location") or location) != location:
        raise HTTPException(404, detail="Function not found")
    return s._gcp_functions_view(project, location, fn)


def api_gcp_functions_delete(project: str, location: str, function: str):
    s = _server()
    project = s._gcp_project_name(project)
    location = s._gcp_location_name(location)
    fn = s.gcp_functions_state.get("functions", {}).get(function)
    if not fn or str(fn.get("project") or project) != project or str(fn.get("location") or location) != location:
        raise HTTPException(404, detail="Function not found")
    del s.gcp_functions_state["functions"][function]
    return {"done": True}


async def api_gcp_functions_call(project: str, location: str, function: str, request: Request):
    s = _server()
    project = s._gcp_project_name(project)
    location = s._gcp_location_name(location)
    fn = s.gcp_functions_state.get("functions", {}).get(function)
    if not fn or str(fn.get("project") or project) != project or str(fn.get("location") or location) != location:
        raise HTTPException(404, detail="Function not found")
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    invocation = {"id": s._id("inv"), "timestamp": s._now(), "request": payload, "response": {"ok": True}, "status": "SUCCESS"}
    fn.setdefault("invocations", []).append(invocation)
    return {"executionId": invocation["id"], "result": invocation["response"]}


def api_gcp_apigw_list_apis(project: str, location: str = "global"):
    s = _server()
    project = s._gcp_project_name(project)
    location = s._gcp_location_name(location, "global")
    apis = [s._gcp_apigateway_api_view(project, location, api) for api in s.gcp_apigw_state.get("apis", {}).values() if str(api.get("project") or project) == project and str(api.get("location") or location) == location]
    apis.sort(key=lambda item: item.get("name", ""))
    return {"apis": apis, "nextPageToken": "", "kind": "apigateway#listApisResponse"}


async def api_gcp_apigw_create_api(project: str, request: Request, location: str = "global"):
    s = _server()
    project = s._gcp_project_name(project)
    location = s._gcp_location_name(location, "global")
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    api = s._gcp_apigw_api_record(project, location, payload)
    s.gcp_apigw_state.setdefault("apis", {})[api["name"]] = api
    return s._gcp_apigateway_api_view(project, location, api)


def api_gcp_apigw_get_api(project: str, location: str, api: str):
    s = _server()
    project = s._gcp_project_name(project)
    location = s._gcp_location_name(location, "global")
    rec = s.gcp_apigw_state.get("apis", {}).get(api)
    if not rec or str(rec.get("project") or project) != project or str(rec.get("location") or location) != location:
        raise HTTPException(404, detail="API not found")
    return s._gcp_apigateway_api_view(project, location, rec)


def api_gcp_apigw_delete_api(project: str, location: str, api: str):
    s = _server()
    project = s._gcp_project_name(project)
    location = s._gcp_location_name(location, "global")
    rec = s.gcp_apigw_state.get("apis", {}).get(api)
    if not rec or str(rec.get("project") or project) != project or str(rec.get("location") or location) != location:
        raise HTTPException(404, detail="API not found")
    del s.gcp_apigw_state["apis"][api]
    return {"done": True}


def api_gcp_apigw_list_configs(project: str, location: str = "global", api: str = ""):
    s = _server()
    project = s._gcp_project_name(project)
    location = s._gcp_location_name(location, "global")
    cfgs = [s._gcp_apigateway_config_view(project, location, cfg) for cfg in s.gcp_apigw_state.get("configs", {}).values() if str(cfg.get("project") or project) == project and str(cfg.get("location") or location) == location and (not api or str(cfg.get("api") or "") == api)]
    cfgs.sort(key=lambda item: item.get("name", ""))
    return {"apiConfigs": cfgs, "nextPageToken": ""}


async def api_gcp_apigw_create_config(project: str, request: Request, location: str = "global", api: str = ""):
    s = _server()
    project = s._gcp_project_name(project)
    location = s._gcp_location_name(location, "global")
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    if api and not payload.get("api"):
        payload["api"] = api
    cfg = s._gcp_apigw_cfg_record(project, location, payload)
    s.gcp_apigw_state.setdefault("configs", {})[cfg["name"]] = cfg
    return s._gcp_apigateway_config_view(project, location, cfg)


def api_gcp_apigw_list_gateways(project: str, location: str = "global", api: str = ""):
    s = _server()
    project = s._gcp_project_name(project)
    location = s._gcp_location_name(location, "global")
    gws = [s._gcp_apigateway_gateway_view(project, location, gw) for gw in s.gcp_apigw_state.get("gateways", {}).values() if str(gw.get("project") or project) == project and str(gw.get("location") or location) == location and (not api or str(gw.get("apiConfig") or "") == api)]
    gws.sort(key=lambda item: item.get("name", ""))
    return {"gateways": gws, "nextPageToken": ""}


async def api_gcp_apigw_create_gateway(project: str, request: Request, location: str = "global", api: str = ""):
    s = _server()
    project = s._gcp_project_name(project)
    location = s._gcp_location_name(location, "global")
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    if api and not payload.get("apiConfig"):
        payload["apiConfig"] = api
    gw = s._gcp_apigw_gateway_record(project, location, payload)
    s.gcp_apigw_state.setdefault("gateways", {})[gw["name"]] = gw
    return s._gcp_apigateway_gateway_view(project, location, gw)


def api_gcp_vpc_list_networks(project: str):
    s = _server()
    project = s._gcp_project_name(project)
    networks = []
    for network in s.gcp_vpc_state.get("networks", {}).values():
        if str(network.get("project") or project) != project:
            continue
        network_name = str(network.get("name") or "")
        networks.append({"kind": "compute#network", "id": str(network.get("id") or s._gcp_compute_numeric_id(f"{project}:{network_name}")), "creationTimestamp": network.get("createTime", s._now()), "name": network_name, "description": network.get("description", ""), "IPv4Range": network.get("IPv4Range", ""), "gatewayIPv4": network.get("gatewayIPv4", ""), "selfLink": f"{s._gcp_compute_network_root()}/projects/{project}/global/networks/{network_name}", "selfLinkWithId": network.get("selfLinkWithId", f"{s._gcp_compute_network_root()}/projects/{project}/global/networks/{network_name}?id={network.get('id') or s._gcp_compute_numeric_id(f'{project}:{network_name}')}"), "autoCreateSubnetworks": bool(network.get("autoCreateSubnetworks", True)), "subnetworks": network.get("subnetworks", []), "peerings": network.get("peerings", []), "routingConfig": {"routingMode": network.get("routingMode", "REGIONAL")}})
    return {"kind": "compute#networkList", "items": networks}


async def api_gcp_vpc_create_network(project: str, request: Request):
    s = _server()
    project = s._gcp_project_name(project)
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    name = str(payload.get("name") or payload.get("network") or "").strip()
    if not name:
        raise HTTPException(400, detail="Network name is required")
    rec = {"id": s._gcp_compute_numeric_id(f"{project}:{name}"), "name": name, "project": project, "description": str(payload.get("description") or ""), "IPv4Range": str(payload.get("IPv4Range") or ""), "gatewayIPv4": str(payload.get("gatewayIPv4") or ""), "autoCreateSubnetworks": bool(payload.get("autoCreateSubnetworks", True)), "routingMode": str(payload.get("routingMode") or "REGIONAL"), "subnetworks": payload.get("subnetworks", []) if isinstance(payload.get("subnetworks"), list) else [], "peerings": payload.get("peerings", []) if isinstance(payload.get("peerings"), list) else [], "createTime": s._now()}
    s.gcp_vpc_state.setdefault("networks", {})[name] = rec
    return {"kind": "compute#network", "id": rec["id"], "creationTimestamp": rec["createTime"], "name": name, "description": rec["description"], "IPv4Range": rec["IPv4Range"], "gatewayIPv4": rec["gatewayIPv4"], "selfLink": f"{s._gcp_compute_network_root()}/projects/{project}/global/networks/{name}", "selfLinkWithId": f"{s._gcp_compute_network_root()}/projects/{project}/global/networks/{name}?id={rec['id']}", "autoCreateSubnetworks": rec["autoCreateSubnetworks"], "subnetworks": rec["subnetworks"], "peerings": rec["peerings"], "routingConfig": {"routingMode": rec["routingMode"]}}


def api_gcp_vpc_get_network(project: str, network: str):
    s = _server()
    project = s._gcp_project_name(project)
    rec = s.gcp_vpc_state.get("networks", {}).get(network)
    if not rec or str(rec.get("project") or project) != project:
        raise HTTPException(404, detail="Network not found")
    return {"kind": "compute#network", "id": rec.get("id", s._gcp_compute_numeric_id(f"{project}:{network}")), "creationTimestamp": rec.get("createTime", s._now()), "name": rec["name"], "description": rec.get("description", ""), "IPv4Range": rec.get("IPv4Range", ""), "gatewayIPv4": rec.get("gatewayIPv4", ""), "selfLink": f"{s._gcp_compute_network_root()}/projects/{project}/global/networks/{network}", "selfLinkWithId": f"{s._gcp_compute_network_root()}/projects/{project}/global/networks/{network}?id={rec.get('id', s._gcp_compute_numeric_id(f'{project}:{network}'))}", "autoCreateSubnetworks": bool(rec.get("autoCreateSubnetworks", True)), "subnetworks": rec.get("subnetworks", []), "peerings": rec.get("peerings", []), "routingConfig": {"routingMode": rec.get("routingMode", "REGIONAL")}}


def api_gcp_vpc_delete_network(project: str, network: str):
    s = _server()
    project = s._gcp_project_name(project)
    rec = s.gcp_vpc_state.get("networks", {}).get(network)
    if not rec or str(rec.get("project") or project) != project:
        raise HTTPException(404, detail="Network not found")
    del s.gcp_vpc_state["networks"][network]
    return {"done": True}


def api_gcp_vpc_list_subnetworks(project: str, region: str):
    s = _server()
    project = s._gcp_project_name(project)
    subnetworks = []
    for subnet in s.gcp_vpc_state.get("subnetworks", {}).values():
        if str(subnet.get("project") or project) != project or str(subnet.get("region") or region) != region:
            continue
        subnetworks.append({"kind": "compute#subnetwork", "id": str(subnet.get("id") or s._gcp_compute_numeric_id(f"{project}:{subnet['name']}")), "creationTimestamp": subnet.get("createTime", s._now()), "name": subnet["name"], "description": subnet.get("description", ""), "region": region, "network": f"{s._gcp_compute_network_root()}/projects/{project}/global/networks/{subnet.get('network','default')}", "ipCidrRange": subnet.get("ipCidrRange", "10.0.0.0/24"), "reservedInternalRange": subnet.get("reservedInternalRange", ""), "gatewayAddress": subnet.get("gatewayAddress", ""), "privateIpGoogleAccess": bool(subnet.get("privateIpGoogleAccess", False)), "secondaryIpRanges": subnet.get("secondaryIpRanges", []), "purpose": subnet.get("purpose", ""), "role": subnet.get("role", ""), "stackType": subnet.get("stackType", "IPV4_ONLY"), "state": subnet.get("state", "READY"), "selfLink": f"{s._gcp_compute_network_root()}/projects/{project}/regions/{region}/subnetworks/{subnet['name']}"})
    return {"kind": "compute#subnetworkList", "items": subnetworks}


async def api_gcp_vpc_create_subnetwork(project: str, region: str, request: Request):
    s = _server()
    project = s._gcp_project_name(project)
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(400, detail="Subnetwork name is required")
    rec = {"id": s._gcp_compute_numeric_id(f"{project}:{name}"), "name": name, "description": str(payload.get("description") or ""), "project": project, "region": region, "network": str(payload.get("network") or "default").split("/")[-1], "ipCidrRange": str(payload.get("ipCidrRange") or "10.0.0.0/24"), "reservedInternalRange": str(payload.get("reservedInternalRange") or ""), "gatewayAddress": str(payload.get("gatewayAddress") or ""), "privateIpGoogleAccess": bool(payload.get("privateIpGoogleAccess", False)), "secondaryIpRanges": payload.get("secondaryIpRanges", []) if isinstance(payload.get("secondaryIpRanges"), list) else [], "purpose": str(payload.get("purpose") or ""), "role": str(payload.get("role") or ""), "stackType": str(payload.get("stackType") or "IPV4_ONLY"), "state": str(payload.get("state") or "READY"), "createTime": s._now()}
    s.gcp_vpc_state.setdefault("subnetworks", {})[name] = rec
    return {"kind": "compute#subnetwork", "id": rec["id"], "creationTimestamp": rec["createTime"], "name": name, "description": rec["description"], "region": region, "network": f"{s._gcp_compute_network_root()}/projects/{project}/global/networks/{rec['network']}", "ipCidrRange": rec["ipCidrRange"], "reservedInternalRange": rec["reservedInternalRange"], "gatewayAddress": rec["gatewayAddress"], "privateIpGoogleAccess": rec["privateIpGoogleAccess"], "secondaryIpRanges": rec["secondaryIpRanges"], "purpose": rec["purpose"], "role": rec["role"], "stackType": rec["stackType"], "state": rec["state"], "selfLink": f"{s._gcp_compute_network_root()}/projects/{project}/regions/{region}/subnetworks/{name}"}


def api_gcp_vpc_list_firewalls(project: str):
    s = _server()
    project = s._gcp_project_name(project)
    firewalls = []
    for fw in s.gcp_vpc_state.get("firewalls", {}).values():
        if str(fw.get("project") or project) != project:
            continue
        firewalls.append({"kind": "compute#firewall", "id": str(fw.get("id") or s._gcp_compute_numeric_id(f"{project}:{fw['name']}")), "creationTimestamp": fw.get("createTime", s._now()), "name": fw["name"], "description": fw.get("description", ""), "network": f"{s._gcp_compute_network_root()}/projects/{project}/global/networks/{fw.get('network','default')}", "priority": int(fw.get("priority") or 1000), "direction": fw.get("direction", "INGRESS"), "allowed": fw.get("allowed", [{"IPProtocol": "tcp", "ports": ["22"]}]), "denied": fw.get("denied", []), "sourceRanges": fw.get("sourceRanges", ["0.0.0.0/0"]), "destinationRanges": fw.get("destinationRanges", []), "sourceTags": fw.get("sourceTags", []), "targetTags": fw.get("targetTags", []), "sourceServiceAccounts": fw.get("sourceServiceAccounts", []), "targetServiceAccounts": fw.get("targetServiceAccounts", []), "disabled": bool(fw.get("disabled", False)), "logConfig": fw.get("logConfig", {}), "selfLink": f"{s._gcp_compute_network_root()}/projects/{project}/global/firewalls/{fw['name']}"})
    return {"kind": "compute#firewallList", "items": firewalls}


async def api_gcp_vpc_create_firewall(project: str, request: Request):
    s = _server()
    project = s._gcp_project_name(project)
    payload = await request.json() if request is not None else {}
    payload = payload if isinstance(payload, dict) else {}
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(400, detail="Firewall name is required")
    rec = {"id": s._gcp_compute_numeric_id(f"{project}:{name}"), "name": name, "description": str(payload.get("description") or ""), "project": project, "network": str(payload.get("network") or "default").split("/")[-1], "priority": int(payload.get("priority") or 1000), "direction": str(payload.get("direction") or "INGRESS"), "allowed": payload.get("allowed") if isinstance(payload.get("allowed"), list) else [{"IPProtocol": "tcp", "ports": ["22"]}], "denied": payload.get("denied") if isinstance(payload.get("denied"), list) else [], "sourceRanges": payload.get("sourceRanges") if isinstance(payload.get("sourceRanges"), list) else ["0.0.0.0/0"], "destinationRanges": payload.get("destinationRanges") if isinstance(payload.get("destinationRanges"), list) else [], "sourceTags": payload.get("sourceTags") if isinstance(payload.get("sourceTags"), list) else [], "targetTags": payload.get("targetTags") if isinstance(payload.get("targetTags"), list) else [], "sourceServiceAccounts": payload.get("sourceServiceAccounts") if isinstance(payload.get("sourceServiceAccounts"), list) else [], "targetServiceAccounts": payload.get("targetServiceAccounts") if isinstance(payload.get("targetServiceAccounts"), list) else [], "disabled": bool(payload.get("disabled", False)), "logConfig": payload.get("logConfig") if isinstance(payload.get("logConfig"), dict) else {}, "createTime": s._now()}
    s.gcp_vpc_state.setdefault("firewalls", {})[name] = rec
    return {"kind": "compute#firewall", "id": rec["id"], "creationTimestamp": rec["createTime"], "name": name, "description": rec["description"], "network": f"{s._gcp_compute_network_root()}/projects/{project}/global/networks/{rec['network']}", "priority": rec["priority"], "direction": rec["direction"], "allowed": rec["allowed"], "denied": rec["denied"], "sourceRanges": rec["sourceRanges"], "destinationRanges": rec["destinationRanges"], "sourceTags": rec["sourceTags"], "targetTags": rec["targetTags"], "sourceServiceAccounts": rec["sourceServiceAccounts"], "targetServiceAccounts": rec["targetServiceAccounts"], "disabled": rec["disabled"], "logConfig": rec["logConfig"], "selfLink": f"{s._gcp_compute_network_root()}/projects/{project}/global/firewalls/{name}"}

