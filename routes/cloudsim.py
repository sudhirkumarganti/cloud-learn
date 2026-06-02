"""CloudSim current/summary/reconcile/events routes extracted from server.py."""
from __future__ import annotations

from fastapi import FastAPI
from core import app_context as ctx


def register(app: FastAPI) -> None:

    @app.get("/api/cloudsim/current")
    def api_cloudsim_current():
        import server
        level = ctx._enforce_tier_feature("cost_simulation")
        server._refresh_cloudsim_gcp_summary()
        payload = ctx.PLATFORM.cloudsim_current()
        if isinstance(payload, dict):
            spaces_state = ctx._spaces_state()
            active_id = spaces_state.get("active_space_id", "")
            active_space = spaces_state.get("spaces", {}).get(active_id, {}) if active_id else {}
            summary = payload.setdefault("summary", {})
            summary.update(server._cloudsim_gcp_summary_counts(active_space if isinstance(active_space, dict) else None))
            server._cloudsim_compose_layers(payload)
        server._attach_cloudsim_advanced(payload)
        if level == "totals":
            payload = server._redact_cloudsim_for_totals_tier(payload)
        if isinstance(payload, dict):
            payload["cost_simulation_level"] = level
        return payload

    @app.get("/api/cloudsim/summary")
    def api_cloudsim_summary():
        import server
        level = ctx._enforce_tier_feature("cost_simulation")
        server._refresh_cloudsim_gcp_summary()
        payload = ctx.PLATFORM.cloudsim_summary()
        if isinstance(payload, dict):
            spaces_state = ctx._spaces_state()
            active_id = spaces_state.get("active_space_id", "")
            active_space = spaces_state.get("spaces", {}).get(active_id, {}) if active_id else {}
            payload.setdefault("summary", {}).update(server._cloudsim_gcp_summary_counts(active_space if isinstance(active_space, dict) else None))
            server._cloudsim_compose_layers(payload)
        server._attach_cloudsim_advanced(payload)
        if level == "totals":
            payload = server._redact_cloudsim_for_totals_tier(payload)
        if isinstance(payload, dict):
            payload["cost_simulation_level"] = level
        return payload

    @app.post("/api/cloudsim/reconcile")
    def api_cloudsim_reconcile():
        payload = ctx.PLATFORM.cloudsim_reconcile()
        ctx._record_usage("cloudsim.reconcile", {"spaces": len(ctx._spaces_state().get("spaces", {}))})
        ctx._persist_state()
        return payload

    @app.get("/api/cloudsim/events")
    def api_cloudsim_events():
        return ctx.PLATFORM.cloudsim_events()
