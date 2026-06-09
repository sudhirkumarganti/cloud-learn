"""Tenant CRUD routes extracted from server.py."""
from __future__ import annotations

import re
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from core import app_context as ctx


def register(app: FastAPI) -> None:

    @app.get("/api/tenants")
    def api_list_tenants():
        ts = ctx._tenants_state()
        out = []
        for tid, tenant in (ts.get("tenants") or {}).items():
            if not isinstance(tenant, dict):
                continue
            out.append({**tenant, "usage": _tenant_usage(tid)})
        return {"active_tenant_id": ts.get("active_tenant_id", ""),
                "tenants": out,
                "default_tenant_id": ctx.DEFAULT_TENANT_ID}

    @app.get("/api/tenants/active")
    def api_active_tenant():
        tid = ctx._active_tenant_id()
        return {"tenant_id": tid, "tenant": ctx._tenant_dict(tid)}

    @app.post("/api/tenants")
    def api_create_tenant(payload: dict[str, Any], request: Request):
        from core.admin_auth import require_admin_key
        require_admin_key(request)
        spec = dict(payload or {})
        name = str(spec.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name required")
        ts = ctx._tenants_state()
        tenants = ts.setdefault("tenants", {})

        # Tier max_tenants cap
        try:
            from core import tier_policy as _tp
            tier = ctx._active_tier()
            p = _tp.policy_for(tier)
            cap = p.get("max_tenants")
            UNLIMITED = _tp.UNLIMITED if hasattr(_tp, "UNLIMITED") else -1
            if cap is not None and cap != UNLIMITED and len(tenants) >= int(cap):
                raise HTTPException(status_code=403, detail={
                    "ok": False, "code": "tier_max_tenants",
                    "reason": f"{tier} tier allows {cap} tenant(s); you have {len(tenants)}",
                    "active_tier": tier,
                    "limit": int(cap), "current": len(tenants),
                    "upgrade_to": _tp._next_tier(_tp.normalize_tier(tier)),
                    "docs": "https://cloudlearn.io/docs/tiers",
                })
        except HTTPException:
            raise
        except Exception:
            pass  # fail-open on policy lookup errors

        tid = str(spec.get("tenant_id") or "").strip()
        if not tid:
            tid = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-") or uuid.uuid4().hex[:12]
        if tid in tenants:
            raise HTTPException(status_code=409, detail=f"tenant '{tid}' already exists")
        tenant = {
            "tenant_id": tid, "name": name,
            "license_tier": str(spec.get("license_tier", "free")),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            "settings": {"max_spaces": int(spec.get("max_spaces", 6))},
        }
        tenants[tid] = tenant
        ctx._persist_state()
        try:
            from core import security_audit
            security_audit.append_event("tenant.created", {
                "tenant_id": tid, "name": name,
                "license_tier": tenant.get("license_tier", "free"),
            })
        except Exception:
            pass
        return {"message": "Tenant created", "tenant": tenant}

    @app.post("/api/tenants/{tid}/switch")
    def api_switch_tenant(tid: str):
        ts = ctx._tenants_state()
        if tid not in (ts.get("tenants") or {}):
            raise HTTPException(status_code=404, detail="TenantNotFound")
        ts["active_tenant_id"] = tid
        spaces_state = ctx._spaces_state()
        active_sid = spaces_state.get("active_space_id", "")
        if active_sid:
            sp = spaces_state.get("spaces", {}).get(active_sid)
            if isinstance(sp, dict) and (sp.get("tenant_id") or ctx.DEFAULT_TENANT_ID) != tid:
                spaces_state["active_space_id"] = ""
        ctx._persist_state()
        return {"message": "Active tenant switched", "tenant_id": tid,
                "tenant": ts["tenants"][tid]}

    @app.delete("/api/tenants/{tid}")
    def api_delete_tenant(tid: str, request: Request):
        from core.admin_auth import require_admin_key
        require_admin_key(request)
        if tid == ctx.DEFAULT_TENANT_ID:
            raise HTTPException(status_code=400, detail="cannot delete the default tenant")
        ts = ctx._tenants_state()
        if tid not in (ts.get("tenants") or {}):
            raise HTTPException(status_code=404, detail="TenantNotFound")
        spaces = (ctx._spaces_state().get("spaces") or {})
        if any(isinstance(s, dict) and (s.get("tenant_id") or ctx.DEFAULT_TENANT_ID) == tid for s in spaces.values()):
            raise HTTPException(status_code=400,
                detail="tenant still owns spaces; delete or migrate them first")
        del ts["tenants"][tid]
        if ts.get("active_tenant_id") == tid:
            ts["active_tenant_id"] = ctx.DEFAULT_TENANT_ID
        ctx._persist_state()
        try:
            from core import security_audit
            security_audit.append_event("tenant.deleted", {
                "tenant_id": tid,
            }, request=request)
        except Exception:
            pass
        return {"message": "Tenant deleted", "tenant_id": tid}


def _tenant_usage(tid: str) -> dict:
    spaces = (ctx._spaces_state().get("spaces") or {})
    tenant = ctx._tenant_dict(tid) or {}
    spaces_count = sum(1 for s in spaces.values()
                       if isinstance(s, dict) and (s.get("tenant_id") or ctx.DEFAULT_TENANT_ID) == tid)
    max_spaces = int((tenant.get("settings") or {}).get("max_spaces", 6))
    return {"spaces_count": spaces_count, "max_spaces": max_spaces,
            "spaces_remaining": max(0, max_spaces - spaces_count)}
