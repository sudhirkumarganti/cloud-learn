"""Azure console summary route extracted from server.py."""
from __future__ import annotations

from fastapi import FastAPI
from core import app_context as ctx


def register(app: FastAPI) -> None:

    @app.get("/api/azure/console/summary")
    def api_azure_console_summary():
        from providers import azure_services as provider_azure_services
        az = provider_azure_services
        type_to_key = {(c["namespace"] + "/" + c["type"]).lower(): c["key"] for c in az.RESOURCE_CATALOG}
        counts = {c["key"]: 0 for c in az.RESOURCE_CATALOG}
        for rec in list(ctx._azure_state_dict().values()):
            ft = str(rec.get("_type", "")).lower()
            if ft in type_to_key:
                counts[type_to_key[ft]] += 1
        return {"subscription": az.DEFAULT_SUBSCRIPTION, "resourceGroup": az.DEFAULT_RG,
                "counts": counts, "total": sum(counts.values())}
