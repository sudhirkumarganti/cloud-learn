from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, Request, Response


def _server():
    import server as server_module

    return server_module


TARGETS = [
    "api_sqs_query",
    "api_sqs_list_queues",
    "api_sqs_create_queue",
    "api_sqs_get_queue",
    "api_sqs_update_queue",
    "api_sqs_delete_queue",
    "api_sqs_list_messages",
    "api_sqs_send_message",
    "api_sqs_receive_message",
    "api_sqs_delete_message",
    "api_sqs_change_visibility",
    "api_sqs_purge",
    "api_sqs_list_tags",
    "api_sqs_tag_queue",
    "api_sqs_untag_queue",
    "api_dynamodb_aws",
    "api_dynamodb_list_tables",
    "api_dynamodb_create_table",
    "api_dynamodb_get_table",
    "api_dynamodb_delete_table",
    "api_dynamodb_list_items",
    "api_dynamodb_put_item",
    "api_dynamodb_update_item",
    "api_dynamodb_delete_item",
    "api_dynamodb_query_items",
    "api_dynamodb_scan_items",
    "api_dynamodb_list_tags",
    "api_dynamodb_tag_table",
    "api_dynamodb_untag_table",
    "api_apigateway_list_apis",
    "api_apigateway_create_api",
    "api_apigateway_get_api",
    "api_apigateway_delete_api",
    "api_apigateway_list_resources",
    "api_apigateway_create_resource",
    "api_apigateway_put_method",
    "api_apigateway_put_integration",
    "api_apigateway_create_deployment",
    "api_apigateway_list_deployments",
    "api_apigateway_create_stage",
    "api_apigateway_list_stages",
    "api_apigateway_list_logs",
    "api_apigateway_invoke_path",
    "api_apigateway_invoke_root",
    "api_lambda_list_functions",
    "api_lambda_create_function",
    "api_lambda_get_function",
    "api_lambda_update_function_code",
    "api_lambda_update_function_configuration",
    "api_lambda_delete_function",
    "api_lambda_get_policy",
    "api_lambda_add_permission",
    "api_lambda_remove_permission",
    "api_lambda_list_invocations",
    "api_lambda_list_versions",
    "api_lambda_publish_version",
    "api_lambda_invoke_function",
    "api_lambda_list_functions_aws",
    "api_lambda_create_function_aws",
    "api_lambda_get_function_aws",
    "api_lambda_delete_function_aws",
    "api_lambda_get_policy_aws",
    "api_lambda_add_permission_aws",
    "api_lambda_remove_permission_aws",
    "api_lambda_update_function_code_aws",
    "api_lambda_update_function_configuration_aws",
    "api_lambda_publish_version_aws",
    "api_lambda_list_versions_aws",
    "api_lambda_invoke_function_aws",
]


async def api_sqs_query(request: Request):
    return await _server().api_sqs_query(request)


def api_sqs_list_queues():
    s = _server()
    queues = [s._sqs_queue_list_view(queue) for queue in s._sqs_list_queues()]
    return {"queues": queues, "count": len(queues)}


def api_sqs_create_queue(req):
    return _server()._sqs_queue_view(_server()._sqs_create_queue_record(req))


def api_sqs_get_queue(queue_name: str):
    s = _server()
    queue = s._sqs_find_queue(queue_name)
    if not queue:
        raise HTTPException(404, detail="QueueNotFound")
    return s._sqs_queue_view(queue)


def api_sqs_update_queue(queue_name: str, req):
    s = _server()
    queue = s._sqs_find_queue(queue_name)
    if not queue:
        raise HTTPException(404, detail="QueueNotFound")
    payload = {
        "VisibilityTimeout": req.visibility_timeout,
        "ReceiveMessageWaitTimeSeconds": req.receive_wait_time_seconds,
        "MessageRetentionPeriod": req.message_retention_period,
        "MaximumMessageSize": req.max_message_size,
        "DelaySeconds": req.delay_seconds,
        "ContentBasedDeduplication": req.content_based_deduplication,
        "RedrivePolicy": req.redrive_policy,
    }
    if req.tags is not None:
        queue["tags"] = dict(req.tags)
    s._sqs_update_queue_attributes(queue, {k: v for k, v in payload.items() if v is not None})
    return s._sqs_queue_view(queue)


def api_sqs_delete_queue(queue_name: str):
    _server()._sqs_delete_queue(queue_name)
    return {"deleted": True, "queue_name": queue_name}


def api_sqs_list_messages(queue_name: str):
    s = _server()
    queue = s._sqs_find_queue(queue_name)
    if not queue:
        raise HTTPException(404, detail="QueueNotFound")
    return {
        "queue_name": queue["queue_name"],
        "messages": [s._sqs_view_message(queue, msg) for msg in queue.get("messages", []) if not msg.get("deleted")],
        "count": len(queue.get("messages", [])),
    }


def api_sqs_send_message(queue_name: str, req):
    s = _server()
    queue = s._sqs_find_queue(queue_name)
    if not queue:
        raise HTTPException(404, detail="QueueNotFound")
    message = s._sqs_enqueue_message(
        queue,
        req.message_body,
        req.message_attributes or req.message_attributes_map or {},
        req.message_attributes_map or {},
        req.message_group_id,
        req.message_deduplication_id,
        source="api_send_message",
    )
    return {"message": s._sqs_view_message(queue, message), "queue_name": queue["queue_name"], "queue_url": queue.get("queue_url")}


def api_sqs_receive_message(queue_name: str, req):
    s = _server()
    queue = s._sqs_find_queue(queue_name)
    if not queue:
        raise HTTPException(404, detail="QueueNotFound")
    deliveries = s._sqs_extract_messages_for_delivery(queue, max(1, min(int(req.max_number_of_messages or 1), 10)))
    if req.visibility_timeout is not None:
        for message in deliveries:
            message["visible_at"] = (datetime.now(timezone.utc) + timedelta(seconds=max(0, int(req.visibility_timeout)))).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return {"queue_name": queue["queue_name"], "messages": [s._sqs_view_message(queue, msg) for msg in deliveries], "count": len(deliveries)}


def api_sqs_delete_message(queue_name: str, receipt_handle: str):
    s = _server()
    queue = s._sqs_find_queue(queue_name)
    if not queue:
        raise HTTPException(404, detail="QueueNotFound")
    if not s._sqs_delete_message(queue, receipt_handle):
        raise HTTPException(400, detail="ReceiptHandleIsInvalid")
    return {"deleted": True, "queue_name": queue["queue_name"], "receipt_handle": receipt_handle}


def api_sqs_change_visibility(queue_name: str, receipt_handle: str, req):
    s = _server()
    queue = s._sqs_find_queue(queue_name)
    if not queue:
        raise HTTPException(404, detail="QueueNotFound")
    if not s._sqs_change_message_visibility(queue, receipt_handle, req.visibility_timeout):
        raise HTTPException(400, detail="ReceiptHandleIsInvalid")
    return {"updated": True, "queue_name": queue["queue_name"], "receipt_handle": receipt_handle, "visibility_timeout": req.visibility_timeout}


def api_sqs_purge(queue_name: str):
    s = _server()
    queue = s._sqs_find_queue(queue_name)
    if not queue:
        raise HTTPException(404, detail="QueueNotFound")
    s._sqs_purge_queue(queue)
    return {"purged": True, "queue_name": queue["queue_name"]}


def api_sqs_list_tags(queue_name: str):
    s = _server()
    queue = s._sqs_find_queue(queue_name)
    if not queue:
        raise HTTPException(404, detail="QueueNotFound")
    return {"queue_name": queue["queue_name"], "tags": s._sqs_tags_view(queue)}


def api_sqs_tag_queue(queue_name: str, payload: dict[str, str]):
    s = _server()
    queue = s._sqs_find_queue(queue_name)
    if not queue:
        raise HTTPException(404, detail="QueueNotFound")
    current = s._sqs_tags_view(queue)
    current.update({str(k): str(v) for k, v in payload.items()})
    s._sqs_set_tags(queue, current)
    return {"tagged": True, "queue_name": queue["queue_name"], "tags": s._sqs_tags_view(queue)}


def api_sqs_untag_queue(queue_name: str, payload: dict[str, Any]):
    s = _server()
    queue = s._sqs_find_queue(queue_name)
    if not queue:
        raise HTTPException(404, detail="QueueNotFound")
    keys = payload.get("keys") if isinstance(payload, dict) else []
    current = s._sqs_tags_view(queue)
    for key in keys or []:
        current.pop(str(key), None)
    s._sqs_set_tags(queue, current)
    return {"untagged": True, "queue_name": queue["queue_name"], "tags": s._sqs_tags_view(queue)}


async def api_dynamodb_aws(request: Request):
    return await _server().api_dynamodb_aws(request)


def api_dynamodb_list_tables():
    return _server()._ddb_list_tables_response()


def api_dynamodb_create_table(req):
    s = _server()
    table = s._ddb_create_table_record(
        {
            "table_name": req.table_name,
            "partition_key_name": req.partition_key_name,
            "partition_key_type": req.partition_key_type,
            "sort_key_name": req.sort_key_name,
            "sort_key_type": req.sort_key_type,
            "billing_mode": req.billing_mode,
            "read_capacity_units": req.read_capacity_units,
            "write_capacity_units": req.write_capacity_units,
            "tags": req.tags or {},
        }
    )
    return s._ddb_table_response(table, include_items=False)


def api_dynamodb_get_table(table_name: str):
    s = _server()
    table = s._ddb_find_table(table_name)
    if not table:
        raise HTTPException(404, detail="TableNotFound")
    return s._ddb_table_response(table, include_items=True)


def api_dynamodb_delete_table(table_name: str):
    _server()._ddb_delete_table_record(table_name)
    return {"deleted": True, "table_name": table_name}


def api_dynamodb_list_items(table_name: str):
    s = _server()
    table = s._ddb_find_table(table_name)
    if not table:
        raise HTTPException(404, detail="TableNotFound")
    rows = s._ddb_table_view(table, include_items=True)["item_rows"]
    return {"table_name": table_name, "items": rows, "count": len(rows)}


def api_dynamodb_put_item(table_name: str, req):
    s = _server()
    table = s._ddb_find_table(table_name)
    if not table:
        raise HTTPException(404, detail="TableNotFound")
    old = s._ddb_put_item_record(table, {"item": req.item})
    native_item = s._ddb_item_to_native_item(req.item)
    key = s._ddb_item_key_string(table, native_item)
    record = table.get("items", {}).get(key, {})
    return {"table_name": table_name, "item": s._ddb_item_record_view(table, key, record), "previous": old.get("item", {}) if old else {}}


def api_dynamodb_update_item(table_name: str, req):
    s = _server()
    table = s._ddb_find_table(table_name)
    if not table:
        raise HTTPException(404, detail="TableNotFound")
    updated = s._ddb_update_item_record(
        table,
        {
            "key": req.key,
            "attribute_updates": req.attribute_updates or {},
            "update_expression": req.update_expression,
            "expression_attribute_values": req.expression_attribute_values or {},
        },
    )
    return {"table_name": table_name, "item": updated.get("item", {})}


def api_dynamodb_delete_item(table_name: str, req):
    s = _server()
    table = s._ddb_find_table(table_name)
    if not table:
        raise HTTPException(404, detail="TableNotFound")
    removed = s._ddb_delete_item_record(table, {"key": req.key})
    return {"table_name": table_name, "deleted": True, "item": removed.get("item", {})}


def api_dynamodb_query_items(table_name: str, req):
    s = _server()
    table = s._ddb_find_table(table_name)
    if not table:
        raise HTTPException(404, detail="TableNotFound")
    payload = {
        "partition_key_value": req.partition_key_value,
        "sort_key_equals": req.sort_key_equals,
        "sort_key_begins_with": req.sort_key_begins_with,
        "sort_key_between": req.sort_key_between or [],
        "limit": req.limit,
        "key_condition_expression": req.key_condition_expression,
        "expression_attribute_values": req.expression_attribute_values or {},
        "expression_attribute_names": req.expression_attribute_names or {},
    }
    rows, count = s._ddb_query_filter(table, payload)
    return {"table_name": table_name, "items": [s._ddb_item_record_view(table, row.get("key", ""), row) for row in rows], "count": len(rows), "scanned_count": count}


def api_dynamodb_scan_items(table_name: str, req):
    s = _server()
    table = s._ddb_find_table(table_name)
    if not table:
        raise HTTPException(404, detail="TableNotFound")
    rows, count = s._ddb_scan_filter(table, {"limit": req.limit})
    return {"table_name": table_name, "items": [s._ddb_item_record_view(table, row.get("key", ""), row) for row in rows], "count": len(rows), "scanned_count": count}


def api_dynamodb_list_tags(table_name: str):
    s = _server()
    table = s._ddb_find_table(table_name)
    if not table:
        raise HTTPException(404, detail="TableNotFound")
    return {"table_name": table_name, "tags": s._ddb_tags_view(table)}


def api_dynamodb_tag_table(table_name: str, req):
    s = _server()
    table = s._ddb_find_table(table_name)
    if not table:
        raise HTTPException(404, detail="TableNotFound")
    tags = s._ddb_tags_view(table)
    tags.update({str(k): str(v) for k, v in (req.tags or {}).items()})
    s._ddb_set_tags(table, tags)
    return {"table_name": table_name, "tags": s._ddb_tags_view(table)}


def api_dynamodb_untag_table(table_name: str, payload: dict[str, Any]):
    s = _server()
    table = s._ddb_find_table(table_name)
    if not table:
        raise HTTPException(404, detail="TableNotFound")
    tags = s._ddb_tags_view(table)
    for key in payload.get("keys", []) if isinstance(payload, dict) else []:
        tags.pop(str(key), None)
    s._ddb_set_tags(table, tags)
    return {"table_name": table_name, "tags": s._ddb_tags_view(table)}


def api_apigateway_list_apis():
    return _server().api_apigateway_list_apis()


def api_apigateway_create_api(req):
    return _server().api_apigateway_create_api(req)


def api_apigateway_get_api(api_id: str):
    return _server().api_apigateway_get_api(api_id)


def api_apigateway_delete_api(api_id: str):
    return _server().api_apigateway_delete_api(api_id)


def api_apigateway_list_resources(api_id: str):
    return _server().api_apigateway_list_resources(api_id)


def api_apigateway_create_resource(api_id: str, req):
    return _server().api_apigateway_create_resource(api_id, req)


def api_apigateway_put_method(api_id: str, req):
    return _server().api_apigateway_put_method(api_id, req)


def api_apigateway_put_integration(api_id: str, req):
    return _server().api_apigateway_put_integration(api_id, req)


def api_apigateway_create_deployment(api_id: str, req):
    return _server().api_apigateway_create_deployment(api_id, req)


def api_apigateway_list_deployments(api_id: str):
    return _server().api_apigateway_list_deployments(api_id)


def api_apigateway_create_stage(api_id: str, req):
    return _server().api_apigateway_create_stage(api_id, req)


def api_apigateway_list_stages(api_id: str):
    return _server().api_apigateway_list_stages(api_id)


def api_apigateway_list_logs(api_id: str):
    return _server().api_apigateway_list_logs(api_id)


async def api_apigateway_invoke_path(api_id: str, stage_name: str, proxy_path: str, request: Request):
    return await _server()._apigw_invoke(api_id, stage_name, proxy_path, request)


async def api_apigateway_invoke_root(api_id: str, stage_name: str, request: Request):
    return await _server()._apigw_invoke(api_id, stage_name, "", request)


def api_lambda_list_functions():
    s = _server()
    functions = [s._lambda_function_view(function) for function in s._lambda_list_functions()]
    return {"functions": functions, "count": len(functions)}


def api_lambda_create_function(req):
    return _server()._lambda_function_view(_server()._lambda_create_function_record(req))


def api_lambda_get_function(function_name: str):
    s = _server()
    function = s._lambda_find_function(function_name)
    if not function:
        raise HTTPException(404, detail="ResourceNotFoundException")
    return s._lambda_function_view(function)


def api_lambda_update_function_code(function_name: str, payload: dict[str, Any]):
    s = _server()
    function = s._lambda_find_function(function_name)
    if not function:
        raise HTTPException(404, detail="ResourceNotFoundException")
    updated = s._lambda_update_function_code(function, str(payload.get("code", "")))
    return s._lambda_function_view(updated)


def api_lambda_update_function_configuration(function_name: str, req):
    s = _server()
    function = s._lambda_find_function(function_name)
    if not function:
        raise HTTPException(404, detail="ResourceNotFoundException")
    updated = s._lambda_update_function_configuration(function, req)
    return s._lambda_function_view(updated)


def api_lambda_delete_function(function_name: str):
    _server()._lambda_delete_function(function_name)
    return {"deleted": True, "function_name": function_name}


def api_lambda_get_policy(function_name: str):
    s = _server()
    function = s._lambda_find_function(function_name)
    if not function:
        raise HTTPException(404, detail="ResourceNotFoundException")
    policy = s._lambda_get_policy(function)
    return {"function_name": function["function_name"], "function_arn": function["function_arn"], **policy}


def api_lambda_add_permission(function_name: str, req):
    s = _server()
    function = s._lambda_find_function(function_name)
    if not function:
        raise HTTPException(404, detail="ResourceNotFoundException")
    permission = s._lambda_add_permission(function, req)
    policy = s._lambda_get_policy(function)
    return {"function_name": function["function_name"], "function_arn": function["function_arn"], "statement": permission, **policy}


def api_lambda_remove_permission(function_name: str, statement_id: str):
    s = _server()
    function = s._lambda_find_function(function_name)
    if not function:
        raise HTTPException(404, detail="ResourceNotFoundException")
    s._lambda_remove_permission(function, statement_id)
    return {"deleted": True, "function_name": function["function_name"], "statement_id": statement_id}


def api_lambda_list_invocations(function_name: str):
    s = _server()
    function = s._lambda_find_function(function_name)
    if not function:
        raise HTTPException(404, detail="ResourceNotFoundException")
    invocations = s._lambda_invocations_view(function)
    return {"function_name": function["function_name"], "function_arn": function["function_arn"], "invocations": invocations, "count": len(invocations)}


def api_lambda_list_versions(function_name: str):
    s = _server()
    function = s._lambda_find_function(function_name)
    if not function:
        raise HTTPException(404, detail="ResourceNotFoundException")
    versions = s._lambda_versions_view(function)
    return {"function_name": function["function_name"], "function_arn": function["function_arn"], "versions": versions, "count": len(versions)}


def api_lambda_publish_version(function_name: str, payload):
    s = _server()
    function = s._lambda_find_function(function_name)
    if not function:
        raise HTTPException(404, detail="ResourceNotFoundException")
    version = s._lambda_publish_version(function, payload.description)
    return {"function_name": function["function_name"], "function_arn": function["function_arn"], "version": version}


def api_lambda_invoke_function(function_name: str, payload):
    return _server()._lambda_invoke_response(function_name, payload.payload, invocation_type=payload.invocation_type)


def api_lambda_list_functions_aws():
    return api_lambda_list_functions()


def api_lambda_create_function_aws(req):
    return api_lambda_create_function(req)


def api_lambda_get_function_aws(function_name: str):
    return api_lambda_get_function(function_name)


def api_lambda_delete_function_aws(function_name: str):
    return api_lambda_delete_function(function_name)


def api_lambda_get_policy_aws(function_name: str):
    return api_lambda_get_policy(function_name)


def api_lambda_add_permission_aws(function_name: str, req):
    return api_lambda_add_permission(function_name, req)


def api_lambda_remove_permission_aws(function_name: str, statement_id: str):
    return api_lambda_remove_permission(function_name, statement_id)


def api_lambda_update_function_code_aws(function_name: str, payload: dict[str, Any]):
    return api_lambda_update_function_code(function_name, payload)


def api_lambda_update_function_configuration_aws(function_name: str, req):
    return api_lambda_update_function_configuration(function_name, req)


def api_lambda_publish_version_aws(function_name: str, payload):
    return api_lambda_publish_version(function_name, payload)


def api_lambda_list_versions_aws(function_name: str):
    return api_lambda_list_versions(function_name)


async def api_lambda_invoke_function_aws(function_name: str, request: Request):
    return await _server().api_lambda_invoke_function_aws(function_name, request)
