"""Runtime bundles, deployments, and service-action router.

Extracted from server.py — contains the /api/runtime/bundles,
/api/deployments, and /api/actions route handlers.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException

from core import app_context as ctx
from core.models import DeploymentRequest, ServiceActionRequest, IAMUserRequest

# Aliases
STATE = ctx.STATE
_id = ctx.id_gen
_now = ctx.now
_record_usage = ctx.record_usage
runtime_state = ctx.runtime_state


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

def register(app: FastAPI) -> None:
    """Mount /api/runtime/bundles, /api/deployments, and /api/actions routes."""

    @app.get("/api/runtime/bundles")
    def api_runtime_bundles():
        return {"bundles": list(runtime_state["bundles"].values()), "count": len(runtime_state["bundles"])}

    @app.post("/api/deployments")
    def api_create_deployment(req: DeploymentRequest):
        deployment_id = _id("deploy")
        source_dir = Path(os.environ.get("CLOUDLEARN_DEPLOY_DIR", Path(__file__).resolve().parent / "deployments")) / deployment_id
        source_dir.mkdir(parents=True, exist_ok=True)
        deployment = {
            "deployment_id": deployment_id,
            "name": req.name,
            "source_url": req.source_url,
            "runtime": req.runtime,
            "command": req.command,
            "branch": req.branch,
            "repo": req.repo,
            "status": "created",
            "workdir": str(source_dir),
            "created": _now(),
        }
        if req.source_url.startswith("https://github.com/") or req.source_url.endswith(".git"):
            try:
                import subprocess
                subprocess.run(["git", "clone", "--depth", "1", req.source_url, str(source_dir)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                deployment["status"] = "cloned"
            except Exception as e:
                deployment["status"] = "clone_failed"
                deployment["error"] = str(e)
        STATE["deployments"][deployment_id] = deployment
        _record_usage("deploy.create", deployment)
        return deployment

    @app.post("/api/actions")
    def api_action_router(payload: ServiceActionRequest):
        service = payload.payload.get("service", "")
        action = payload.action.lower()
        if service == "s3":
            return {"message": "Use S3 REST or /api/s3 endpoints for S3 actions."}
        if service == "iam" and action == "createuser":
            from providers import aws_iam as provider_aws_iam
            return provider_aws_iam.api_iam_create_user(IAMUserRequest(**payload.payload))
        raise HTTPException(400, detail="UnsupportedAction")
