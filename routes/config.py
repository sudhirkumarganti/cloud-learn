"""Runtime configuration routes extracted from server.py.

Covers: audit-sinks, notification-channels, custom-domain, branding, SSO,
scaffolding generator, cross-tenant RBAC, and Helm chart endpoints.
"""
from __future__ import annotations

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
from core import app_context as ctx


def register(app: FastAPI) -> None:

    # ── Audit sinks (Developer+ tier) ─────────────────────────────────────

    @app.get("/api/runtime/audit-sinks")
    def api_audit_sinks_list():
        ctx._enforce_tier_feature("audit_export_sinks")
        from core import audit_sinks as _as
        return {"tier": ctx._active_tier(), "sinks": _as.list_sinks(ctx.STATE, ctx._active_tenant_id())}

    @app.post("/api/runtime/audit-sinks")
    async def api_audit_sinks_register(request: Request):
        ctx._enforce_tier_feature("audit_export_sinks")
        body = await request.json() if await request.body() else {}
        from core import audit_sinks as _as
        try:
            sink = _as.register_sink(ctx.STATE, ctx._active_tenant_id(), body)
            ctx._persist_state()
            return sink
        except ValueError as e:
            raise HTTPException(400, detail=str(e))

    @app.delete("/api/runtime/audit-sinks/{sink_id}")
    def api_audit_sinks_delete(sink_id: str):
        ctx._enforce_tier_feature("audit_export_sinks")
        from core import audit_sinks as _as
        ok = _as.delete_sink(ctx.STATE, ctx._active_tenant_id(), sink_id)
        if not ok:
            raise HTTPException(404, detail="sink not found")
        ctx._persist_state()
        return {"deleted": sink_id}

    # ── Notification channels (Developer+ tier) ───────────────────────────

    @app.get("/api/runtime/notification-channels")
    def api_notif_list():
        ctx._enforce_tier_feature("notifications")
        from core import notifications as _nt
        return {"tier": ctx._active_tier(),
                "channels": _nt.list_channels(ctx.STATE, ctx._active_tenant_id()),
                "known_events": list(_nt.KNOWN_EVENTS)}

    @app.post("/api/runtime/notification-channels")
    async def api_notif_register(request: Request):
        level = ctx._enforce_tier_feature("notifications")
        body = await request.json() if await request.body() else {}
        if level == "webhook" and str(body.get("kind") or "webhook") not in ("webhook",):
            raise HTTPException(403, detail={
                "ok": False, "code": "tier_feature_level",
                "reason": "Developer tier supports webhook channels only; upgrade for Slack/email.",
                "active_tier": ctx._active_tier(), "upgrade_to": "enterprise",
            })
        from core import notifications as _nt
        try:
            ch = _nt.register_channel(ctx.STATE, ctx._active_tenant_id(), body)
            ctx._persist_state()
            return ch
        except ValueError as e:
            raise HTTPException(400, detail=str(e))

    @app.delete("/api/runtime/notification-channels/{channel_id}")
    def api_notif_delete(channel_id: str):
        ctx._enforce_tier_feature("notifications")
        from core import notifications as _nt
        ok = _nt.delete_channel(ctx.STATE, ctx._active_tenant_id(), channel_id)
        if not ok:
            raise HTTPException(404, detail="channel not found")
        ctx._persist_state()
        return {"deleted": channel_id}

    @app.post("/api/runtime/notification-channels/{channel_id}/test")
    def api_notif_test(channel_id: str):
        ctx._enforce_tier_feature("notifications")
        from core import notifications as _nt
        return _nt.send_test(ctx.STATE, ctx._active_tenant_id(), channel_id)

    # ── Custom domain (Enterprise tier) ───────────────────────────────────

    @app.get("/api/runtime/custom-domain")
    def api_custom_domain_get():
        ctx._enforce_tier_feature("custom_domain")
        from core import tenant_theming as _tt
        return {"tier": ctx._active_tier(),
                "tenant_id": ctx._active_tenant_id(),
                "domain": _tt.get_custom_domain(ctx.STATE, ctx._active_tenant_id())}

    @app.post("/api/runtime/custom-domain")
    async def api_custom_domain_set(request: Request):
        ctx._enforce_tier_feature("custom_domain")
        body = await request.json() if await request.body() else {}
        from core import tenant_theming as _tt
        try:
            res = _tt.set_custom_domain(ctx.STATE, ctx._active_tenant_id(), str(body.get("domain") or ""))
            ctx._persist_state()
            return res
        except ValueError as e:
            raise HTTPException(400, detail=str(e))

    @app.delete("/api/runtime/custom-domain")
    def api_custom_domain_delete():
        ctx._enforce_tier_feature("custom_domain")
        from core import tenant_theming as _tt
        removed = _tt.delete_custom_domain(ctx.STATE, ctx._active_tenant_id())
        ctx._persist_state()
        return {"deleted": removed}

    # ── Branding (Enterprise tier) ────────────────────────────────────────

    @app.get("/api/runtime/branding")
    def api_branding_get():
        ctx._enforce_tier_feature("branding")
        from core import tenant_theming as _tt
        return {"tier": ctx._active_tier(),
                "tenant_id": ctx._active_tenant_id(),
                "branding": _tt.get_branding(ctx.STATE, ctx._active_tenant_id())}

    @app.post("/api/runtime/branding")
    async def api_branding_set(request: Request):
        ctx._enforce_tier_feature("branding")
        body = await request.json() if await request.body() else {}
        from core import tenant_theming as _tt
        try:
            res = _tt.set_branding(ctx.STATE, ctx._active_tenant_id(), body)
            ctx._persist_state()
            return res
        except ValueError as e:
            raise HTTPException(400, detail=str(e))

    @app.get("/api/runtime/branding/{tenant_id}.css")
    def api_branding_css(tenant_id: str):
        """Public endpoint — console pages link-rel-stylesheet this."""
        from core import tenant_theming as _tt
        css = _tt.branding_css(ctx.STATE, tenant_id)
        return Response(content=css, media_type="text/css")

    # ── SSO (Enterprise tier) ─────────────────────────────────────────────

    @app.get("/api/runtime/sso")
    def api_sso_get():
        ctx._enforce_tier_feature("sso")
        from core import sso_config as _sso
        return _sso.get_config(ctx.STATE, ctx._active_tenant_id())

    @app.post("/api/runtime/sso/configure")
    async def api_sso_configure(request: Request):
        ctx._enforce_tier_feature("sso")
        body = await request.json() if await request.body() else {}
        from core import sso_config as _sso
        try:
            res = _sso.configure(ctx.STATE, ctx._active_tenant_id(), body)
            ctx._persist_state()
            return res
        except ValueError as e:
            raise HTTPException(400, detail=str(e))

    @app.post("/api/runtime/sso/disable")
    def api_sso_disable():
        ctx._enforce_tier_feature("sso")
        from core import sso_config as _sso
        res = _sso.disable(ctx.STATE, ctx._active_tenant_id())
        ctx._persist_state()
        return res

    @app.post("/api/runtime/sso/validate")
    async def api_sso_validate(request: Request):
        """Probe endpoint — verify a Bearer token without consuming it."""
        ctx._enforce_tier_feature("sso")
        body = await request.json() if await request.body() else {}
        token = str(body.get("token") or "")
        if not token:
            raise HTTPException(400, detail="token required")
        from core import sso_config as _sso
        return _sso.validate_bearer(ctx.STATE, ctx._active_tenant_id(), f"Bearer {token}")

    # ── Scaffolding generator (Developer+ tier) ───────────────────────────

    @app.get("/api/scaffolding/supported")
    def api_scaffolding_supported():
        """List all (provider, service, output) triples this tier can scaffold."""
        ctx._enforce_tier_feature("scaffolding_generator")
        from core import scaffolding_generator as _sg
        return {"tier": ctx._active_tier(), "triples": _sg.supported()}

    @app.get("/api/scaffolding/generate")
    def api_scaffolding_generate(provider: str, service: str, output: str = "terraform",
                                  name: str = "my-resource", endpoint: str | None = None):
        """Generate a copy-paste-ready scaffolding snippet."""
        ctx._enforce_tier_feature("scaffolding_generator")
        from core import scaffolding_generator as _sg
        try:
            ep = endpoint or "http://localhost:9000"
            return _sg.generate(provider, service, output, name=name, endpoint=ep)
        except KeyError as e:
            raise HTTPException(404, detail=str(e))

    # ── Cross-tenant RBAC (Enterprise tier) ───────────────────────────────

    @app.get("/api/runtime/xt-rbac/grants")
    def api_xtrbac_list():
        ctx._enforce_tier_feature("cross_tenant_rbac")
        from core import cross_tenant_rbac as _xt
        return {"tier": ctx._active_tier(),
                "tenant_id": ctx._active_tenant_id(),
                "grants": _xt.list_grants(ctx.STATE, ctx._active_tenant_id())}

    @app.post("/api/runtime/xt-rbac/grants")
    async def api_xtrbac_create(request: Request):
        ctx._enforce_tier_feature("cross_tenant_rbac")
        body = await request.json() if await request.body() else {}
        ts = ctx._tenants_state()
        grantee = str(body.get("grantee_tenant") or "")
        if grantee and grantee not in (ts.get("tenants") or {}):
            raise HTTPException(400, detail=f"grantee_tenant {grantee!r} does not exist")
        from core import cross_tenant_rbac as _xt
        try:
            grant = _xt.create_grant(ctx.STATE, ctx._active_tenant_id(), body)
            ctx._persist_state()
            return grant
        except ValueError as e:
            raise HTTPException(400, detail=str(e))

    @app.delete("/api/runtime/xt-rbac/grants/{grant_id}")
    def api_xtrbac_delete(grant_id: str):
        ctx._enforce_tier_feature("cross_tenant_rbac")
        from core import cross_tenant_rbac as _xt
        ok = _xt.delete_grant(ctx.STATE, grant_id, ctx._active_tenant_id())
        if not ok:
            raise HTTPException(404, detail="grant not found (or you're not the grantor)")
        ctx._persist_state()
        return {"deleted": grant_id}

    # ── Helm chart + air-gapped install (Enterprise tier) ─────────────────

    @app.get("/api/runtime/helm")
    def api_helm_metadata():
        ctx._enforce_tier_feature("helm")
        from core import helm_chart as _hc
        return {"tier": ctx._active_tier(), **_hc.chart_metadata()}

    @app.get("/api/runtime/helm/chart.tar.gz")
    def api_helm_chart():
        ctx._enforce_tier_feature("helm")
        from core import helm_chart as _hc
        data = _hc.build_chart_tarball()
        return Response(
            content=data, media_type="application/gzip",
            headers={"Content-Disposition": f"attachment; filename=cloudlearn-{_hc.CHART_VERSION}.tgz",
                     "Content-Length": str(len(data))},
        )

    @app.get("/api/runtime/helm/values.yaml")
    def api_helm_values():
        ctx._enforce_tier_feature("helm")
        from core import helm_chart as _hc
        return Response(content=_hc._values_yaml(), media_type="application/yaml",
                        headers={"Content-Disposition": 'attachment; filename=values.yaml'})

    @app.get("/api/runtime/helm/airgap-bundle.tar.gz")
    def api_helm_airgap():
        ctx._enforce_tier_feature("helm")
        from core import helm_chart as _hc
        data = _hc.build_airgap_bundle()
        return Response(
            content=data, media_type="application/gzip",
            headers={"Content-Disposition": "attachment; filename=cloudlearn-airgap.tar.gz",
                     "Content-Length": str(len(data))},
        )
