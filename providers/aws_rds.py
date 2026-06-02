from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from core.app_context import rds_state, vpc_state


def _server():
    import server as server_module

    return server_module


def api_rds_list_databases():
    s = _server()
    return s._rds_list_databases_view()


def api_rds_create_database(req):
    s = _server()
    db = s._rds_prepare_db_instance(req)
    return s._rds_db_view(db)


def api_rds_get_database(db_instance_identifier: str):
    s = _server()
    db = s._rds_find_db_instance(db_instance_identifier)
    if not db:
        raise HTTPException(404, detail="DBInstanceNotFound")
    return s._rds_db_view(db)


def api_rds_start_database(db_instance_identifier: str):
    s = _server()
    db = s._rds_find_db_instance(db_instance_identifier)
    if not db:
        raise HTTPException(404, detail="DBInstanceNotFound")
    if s._rds_db_status(db) == "available":
        return s._rds_db_view(db)
    db = s._rds_runtime_start(db)
    s._rds_emit_event("StartDBInstance", {"db_instance_identifier": db_instance_identifier})
    return s._rds_db_view(db)


def api_rds_stop_database(db_instance_identifier: str):
    s = _server()
    db = s._rds_find_db_instance(db_instance_identifier)
    if not db:
        raise HTTPException(404, detail="DBInstanceNotFound")
    db = s._rds_runtime_stop(db)
    s._rds_emit_event("StopDBInstance", {"db_instance_identifier": db_instance_identifier})
    return s._rds_db_view(db)


def api_rds_reboot_database(db_instance_identifier: str):
    s = _server()
    db = s._rds_find_db_instance(db_instance_identifier)
    if not db:
        raise HTTPException(404, detail="DBInstanceNotFound")
    db = s._rds_runtime_reboot(db)
    s._rds_emit_event("RebootDBInstance", {"db_instance_identifier": db_instance_identifier})
    return s._rds_db_view(db)


def api_rds_modify_database(db_instance_identifier: str, req):
    s = _server()
    db = s._rds_find_db_instance(db_instance_identifier)
    if not db:
        raise HTTPException(404, detail="DBInstanceNotFound")
    modified = s._rds_update_db_instance(db, req)
    return s._rds_db_view(modified)


def api_rds_delete_database(db_instance_identifier: str, skip_final_snapshot: bool = True, final_snapshot_identifier: str = ""):
    s = _server()
    s._rds_delete_db_instance(db_instance_identifier, skip_final_snapshot=skip_final_snapshot, final_snapshot_identifier=final_snapshot_identifier)
    return {"deleted": True, "db_instance_identifier": db_instance_identifier}


def api_rds_list_subnet_groups():
    s = _server()
    return {"db_subnet_groups": list(sorted(rds_state["db_subnet_groups"].values(), key=lambda item: item.get("db_subnet_group_name", ""))), "count": len(rds_state["db_subnet_groups"])}


def api_rds_create_subnet_group(req):
    s = _server()
    name = req.db_subnet_group_name.strip().lower()
    if not name:
        raise HTTPException(400, detail="MissingParameter: DBSubnetGroupName")
    if name in rds_state["db_subnet_groups"]:
        raise HTTPException(400, detail="DBSubnetGroupAlreadyExists")
    vpc_id = req.vpc_id or s._rds_vpc_id()
    if not vpc_id:
        raise HTTPException(400, detail="NoSuchVpc")
    subnet_ids = [sid for sid in req.subnet_ids if sid in vpc_state.get("subnets", {}) and vpc_state["subnets"][sid].get("vpc_id") == vpc_id]
    if not subnet_ids:
        subnet_ids = s._rds_default_subnet_ids(vpc_id)
    return s._rds_make_db_subnet_group(name, req.db_subnet_group_description or name, vpc_id, subnet_ids, req.tags or [])


def api_rds_delete_subnet_group(db_subnet_group_name: str):
    s = _server()
    name = db_subnet_group_name.lower()
    for db in rds_state["db_instances"].values():
        if db.get("db_subnet_group_name") == name:
            raise HTTPException(409, detail="InvalidDBSubnetGroupState")
    if name not in rds_state["db_subnet_groups"]:
        raise HTTPException(404, detail="DBSubnetGroupNotFound")
    del rds_state["db_subnet_groups"][name]
    return {"deleted": True, "db_subnet_group_name": name}


def api_rds_list_parameter_groups():
    s = _server()
    return {"db_parameter_groups": list(sorted(rds_state["db_parameter_groups"].values(), key=lambda item: item.get("db_parameter_group_name", ""))), "count": len(rds_state["db_parameter_groups"])}


def api_rds_create_parameter_group(req):
    s = _server()
    name = req.db_parameter_group_name.strip().lower()
    if not name:
        raise HTTPException(400, detail="MissingParameter: DBParameterGroupName")
    if name in rds_state["db_parameter_groups"]:
        raise HTTPException(400, detail="DBParameterGroupAlreadyExists")
    return s._rds_make_db_parameter_group(name, req.family, req.description or name, req.tags or [])


def api_rds_delete_parameter_group(db_parameter_group_name: str):
    s = _server()
    name = db_parameter_group_name.lower()
    for db in rds_state["db_instances"].values():
        if db.get("db_parameter_group_name") == name:
            raise HTTPException(409, detail="InvalidDBParameterGroupState")
    if name not in rds_state["db_parameter_groups"]:
        raise HTTPException(404, detail="DBParameterGroupNotFound")
    del rds_state["db_parameter_groups"][name]
    return {"deleted": True, "db_parameter_group_name": name}


def api_rds_list_snapshots():
    s = _server()
    return {"db_snapshots": [s._rds_db_snapshot_view(snapshot) for snapshot in sorted(rds_state["db_snapshots"].values(), key=lambda item: item.get("created", ""))], "count": len(rds_state["db_snapshots"])}


def api_rds_create_snapshot(db_instance_identifier: str, req):
    s = _server()
    db = s._rds_find_db_instance(db_instance_identifier)
    if not db:
        raise HTTPException(404, detail="DBInstanceNotFound")
    snapshot = s._rds_create_snapshot_from_db(db, req.db_snapshot_identifier, req.tags or [])
    return s._rds_db_snapshot_view(snapshot)


def api_rds_restore_snapshot(db_snapshot_identifier: str, req):
    s = _server()
    snapshot = s._rds_find_db_snapshot(db_snapshot_identifier)
    if not snapshot:
        raise HTTPException(404, detail="DBSnapshotNotFound")
    db = s._rds_restore_snapshot(snapshot, req)
    return s._rds_db_view(db)


def api_rds_add_tags(db_instance_identifier: str, payload: dict[str, Any]):
    s = _server()
    db = s._rds_find_db_instance(db_instance_identifier)
    if not db:
        raise HTTPException(404, detail="DBInstanceNotFound")
    tags = []
    for key, value in payload.items():
        if key.lower().startswith("tag") and isinstance(value, dict):
            tags.append({"key": str(value.get("key", "")), "value": str(value.get("value", ""))})
    s._rds_set_tags(db, tags)
    return s._rds_db_view(db)


def api_rds_list_tags(db_instance_identifier: str):
    s = _server()
    db = s._rds_find_db_instance(db_instance_identifier)
    if not db:
        raise HTTPException(404, detail="DBInstanceNotFound")
    return {"tags": list(db.get("tags", []))}
