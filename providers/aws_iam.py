from __future__ import annotations

import copy
from typing import Any

from fastapi import HTTPException


def _server():
    import server as server_module

    return server_module


def api_iam_list_users():
    s = _server()
    return {"users": list(s.iam_state["users"].values()), "count": len(s.iam_state["users"])}


def api_iam_create_user(req):
    s = _server()
    if not (req.user_name or "").strip():
        raise HTTPException(400, detail="MissingParameter: user_name is required.")
    user_id = s._id("user")
    user = {"user_id": user_id, "user_name": req.user_name, "path": req.path, "created": s._now(), "policies": [], "groups": []}
    s.iam_state["users"][user_id] = user
    s._record_usage("iam.create_user", user)
    return user


def api_iam_delete_user(user_id: str):
    s = _server()
    user = s.iam_state["users"].get(user_id) or s._iam_find_user(user_id)
    if not user:
        raise HTTPException(404, detail="TargetNotFound")
    for group in s.iam_state.get("groups", {}).values():
        group["members"] = [member for member in group.get("members", []) if member != user.get("user_id")]
    s._iam_detach_policy_records("user", user.get("user_id", ""))
    s.iam_state["users"].pop(user["user_id"], None)
    s._record_usage("iam.delete_user", user)
    return {"message": "User deleted", "user": user}


def api_iam_list_groups():
    s = _server()
    return {"groups": list(s.iam_state["groups"].values()), "count": len(s.iam_state["groups"])}


def api_iam_create_group(req):
    s = _server()
    if not (req.group_name or "").strip():
        raise HTTPException(400, detail="MissingParameter: group_name is required.")
    group_id = s._id("group")
    group = {
        "group_id": group_id,
        "group_name": req.group_name,
        "path": req.path,
        "created": s._now(),
        "members": [],
        "policies": [],
    }
    s.iam_state["groups"][group_id] = group
    s._record_usage("iam.create_group", group)
    return group


def api_iam_delete_group(group_id: str):
    s = _server()
    group = s.iam_state["groups"].get(group_id) or s._iam_find_group(group_id)
    if not group:
        raise HTTPException(404, detail="TargetNotFound")
    for user in s.iam_state.get("users", {}).values():
        user["groups"] = [gid for gid in user.get("groups", []) if gid != group.get("group_id")]
    s._iam_detach_policy_records("group", group.get("group_id", ""))
    s.iam_state["groups"].pop(group["group_id"], None)
    s._record_usage("iam.delete_group", group)
    return {"message": "Group deleted", "group": group}


def api_iam_add_user_to_group(group_id: str, payload: dict[str, Any]):
    s = _server()
    group = s.iam_state["groups"].get(group_id) or s._iam_find_group(group_id)
    if not group:
        raise HTTPException(404, detail="TargetNotFound")
    user_id = (payload.get("user_id") or payload.get("user_name") or "").strip()
    user = s._iam_find_user(user_id)
    if not user:
        raise HTTPException(404, detail="TargetNotFound")
    members = group.setdefault("members", [])
    if user["user_id"] not in members:
        members.append(user["user_id"])
    user_groups = user.setdefault("groups", [])
    if group["group_id"] not in user_groups:
        user_groups.append(group["group_id"])
    s._record_usage("iam.add_user_to_group", {"group_id": group["group_id"], "user_id": user["user_id"]})
    return {"message": "User added to group", "group": group, "user": user}


def api_iam_remove_user_from_group(group_id: str, user_id: str):
    s = _server()
    group = s.iam_state["groups"].get(group_id) or s._iam_find_group(group_id)
    if not group:
        raise HTTPException(404, detail="TargetNotFound")
    user = s._iam_find_user(user_id)
    if not user:
        raise HTTPException(404, detail="TargetNotFound")
    group["members"] = [member for member in group.get("members", []) if member != user["user_id"]]
    user["groups"] = [gid for gid in user.get("groups", []) if gid != group["group_id"]]
    s._record_usage("iam.remove_user_from_group", {"group_id": group["group_id"], "user_id": user["user_id"]})
    return {"message": "User removed from group", "group": group, "user": user}


def api_iam_list_roles():
    s = _server()
    return {"roles": list(s.iam_state["roles"].values()), "count": len(s.iam_state["roles"])}


def api_iam_create_role(req):
    s = _server()
    if not (req.role_name or "").strip():
        raise HTTPException(400, detail="MissingParameter: role_name is required.")
    role_id = s._id("role")
    role = {
        "role_id": role_id,
        "role_name": req.role_name,
        "path": req.path,
        "assume_role_policy_document": req.assume_role_policy_document,
        "description": req.description,
        "created": s._now(),
        "policies": [],
    }
    s.iam_state["roles"][role_id] = role
    s._record_usage("iam.create_role", role)
    return role


def api_iam_delete_role(role_id: str):
    s = _server()
    role = s.iam_state["roles"].get(role_id)
    if not role:
        for candidate in s.iam_state.get("roles", {}).values():
            if role_id in {candidate.get("role_id", ""), candidate.get("role_name", ""), s._iam_role_arn(candidate.get("role_name", ""))}:
                role = candidate
                break
    if not role:
        raise HTTPException(404, detail="TargetNotFound")
    s._iam_detach_policy_records("role", role.get("role_id", ""))
    s.iam_state["roles"].pop(role["role_id"], None)
    s._record_usage("iam.delete_role", role)
    return {"message": "Role deleted", "role": role}


def api_iam_list_policies():
    s = _server()
    return {"policies": list(s.iam_state["policies"].values()), "count": len(s.iam_state["policies"])}


def api_iam_create_policy(req):
    s = _server()
    if not (req.policy_name or "").strip():
        raise HTTPException(400, detail="MissingParameter: policy_name is required.")
    policy_id = s._id("policy")
    policy = {"policy_id": policy_id, "policy_name": req.policy_name, "document": req.document, "created": s._now()}
    s.iam_state["policies"][policy_id] = policy
    s._record_usage("iam.create_policy", policy)
    return policy


def api_iam_delete_policy(policy_id: str):
    s = _server()
    policy = s.iam_state["policies"].get(policy_id)
    if not policy:
        raise HTTPException(404, detail="NoSuchPolicy")
    s._iam_remove_policy_from_all_principals(policy_id)
    s.iam_state["policies"].pop(policy_id, None)
    s.iam_state["attachments"] = [a for a in s.iam_state.get("attachments", []) if a.get("policy_id") != policy_id]
    s._record_usage("iam.delete_policy", policy)
    return {"message": "Policy deleted", "policy": policy}


def api_iam_attach_policy(payload: dict[str, Any]):
    s = _server()
    target_type = payload.get("target_type", "user")
    target_id = payload.get("target_id")
    policy_id = payload.get("policy_id")
    if policy_id not in s.iam_state["policies"]:
        raise HTTPException(404, detail="NoSuchPolicy")
    if target_type == "user":
        target = s.iam_state["users"].get(target_id) or s._iam_find_user(target_id)
    elif target_type == "group":
        target = s.iam_state["groups"].get(target_id) or s._iam_find_group(target_id)
    else:
        target = s.iam_state["roles"].get(target_id)
        if not target:
            for role in s.iam_state["roles"].values():
                if target_id in {role.get("role_name", ""), s._iam_role_arn(role.get("role_name", ""))}:
                    target = role
                    break
    if not target:
        raise HTTPException(404, detail="TargetNotFound")
    target.setdefault("policies", []).append(policy_id)
    s.iam_state["attachments"].append({"target_type": target_type, "target_id": target_id, "policy_id": policy_id, "at": s._now()})
    s._record_usage("iam.attach_policy", {"target_type": target_type, "target_id": target_id, "policy_id": policy_id})
    return {"message": "Policy attached", "target": target, "policy_id": policy_id}


def api_iam_detach_policy(payload: dict[str, Any]):
    s = _server()
    target_type = (payload.get("target_type") or "user").strip().lower()
    target_id = (payload.get("target_id") or "").strip()
    policy_id = (payload.get("policy_id") or "").strip()
    if not target_id or not policy_id:
        raise HTTPException(400, detail="MissingParameter: target_id and policy_id are required.")
    removed = s._iam_detach_policy_records(target_type, target_id, policy_id)
    if not removed:
        raise HTTPException(404, detail="TargetNotFound")
    s._record_usage("iam.detach_policy", {"target_type": target_type, "target_id": target_id, "policy_id": policy_id})
    return {"message": "Policy detached", "target_type": target_type, "target_id": target_id, "policy_id": policy_id}


def api_iam_list_attachments():
    s = _server()
    return {"attachments": list(s.iam_state["attachments"]), "count": len(s.iam_state["attachments"])}


def api_iam_list_identity_providers():
    s = _server()
    return {"identity_providers": list(s.iam_state.get("identity_providers", {}).values()), "count": len(s.iam_state.get("identity_providers", {}))}


def api_iam_create_identity_provider(req):
    s = _server()
    if not (req.provider_name or "").strip():
        raise HTTPException(400, detail="MissingParameter: provider_name is required.")
    provider_id = s._id("idp")
    provider = {
        "provider_id": provider_id,
        "provider_name": req.provider_name,
        "provider_type": req.provider_type,
        "url": req.url,
        "created": s._now(),
        "tags": copy.deepcopy(req.tags or []),
    }
    s.iam_state.setdefault("identity_providers", {})[provider_id] = provider
    s._record_usage("iam.create_identity_provider", provider)
    return provider


def api_iam_delete_identity_provider(provider_id: str):
    s = _server()
    providers = s.iam_state.setdefault("identity_providers", {})
    provider = providers.pop(provider_id, None)
    if not provider:
        raise HTTPException(404, detail="TargetNotFound")
    s._record_usage("iam.delete_identity_provider", provider)
    return {"message": "Identity provider deleted", "identity_provider": provider}


def api_iam_get_account_settings():
    s = _server()
    return {"account_settings": copy.deepcopy(s.iam_state.get("account_settings", {}))}


def api_iam_update_account_settings(req):
    s = _server()
    current = s.iam_state.setdefault("account_settings", {"password_policy": {}})
    if req.password_policy:
        current["password_policy"] = copy.deepcopy(req.password_policy)
    s._record_usage("iam.update_account_settings", current)
    return {"account_settings": copy.deepcopy(current)}
