"""AWS EC2 instance CRUD, AMI catalog, runtime provisioning, console sessions, WebSocket handlers.

Extracted from server.py — the biggest route module.  Contains:
- EC2 instance CRUD (list/create/start/stop/reboot/terminate)
- AMI catalog and instance-type catalog
- LXD/Multipass bootstrap and provisioning
- Console sessions (REST + WebSocket)
- EC2 query API (XML wire protocol)
- Runtime reconciliation helpers
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from core import app_context as ctx
from core.models import (
    EC2ConsoleCommandRequest,
    EC2ConsoleInputRequest,
    EC2InstanceRequest,
)

# ---------------------------------------------------------------------------
# Lazy back-reference to server.py
# ---------------------------------------------------------------------------


def _srv():
    import server as _s
    return _s


# ---------------------------------------------------------------------------
# Module-level constants (re-exported from server.py)
# ---------------------------------------------------------------------------

# These are mutable globals in server.py — we reference them via the module
# so that mutations in server.py are visible here.

def _console_sessions() -> Dict[str, dict]:
    return _srv().CONSOLE_SESSIONS


def _console_lock() -> threading.RLock:
    return _srv().CONSOLE_LOCK


def _lxd_bootstrap_lock() -> threading.RLock:
    return _srv().LXD_BOOTSTRAP_LOCK


# Expose AMI_CATALOG and EC2_INSTANCE_TYPE_CATALOG as module-level refs
# so that other modules can import them from here.

@property
def AMI_CATALOG():
    return _srv().AMI_CATALOG


@property
def EC2_INSTANCE_TYPE_CATALOG():
    return _srv().EC2_INSTANCE_TYPE_CATALOG


def get_ami_catalog():
    return _srv().AMI_CATALOG


def get_instance_type_catalog():
    return _srv().EC2_INSTANCE_TYPE_CATALOG


# ---------------------------------------------------------------------------
# State access
# ---------------------------------------------------------------------------

ec2_state = ctx.ec2_state
gcp_compute_state = ctx.gcp_compute_state


# ---------------------------------------------------------------------------
# Helper functions — delegated to server.py
# ---------------------------------------------------------------------------

def _ec2_state_meta(state: str) -> tuple:
    return _srv()._ec2_state_meta(state)


def _terminated_visible(instance: dict, now=None) -> bool:
    return _srv()._terminated_visible(instance, now)


def _reconcile_runtime_instances(instances: dict) -> None:
    return _srv()._reconcile_runtime_instances(instances)


def _prune_expired_terminated_instances() -> None:
    return _srv()._prune_expired_terminated_instances()


def _prune_expired_terminated_instances_from(instances: dict) -> None:
    return _srv()._prune_expired_terminated_instances_from(instances)


# ---------------------------------------------------------------------------
# Console REST API route handlers
# ---------------------------------------------------------------------------

def api_ec2_amis():
    return _srv().api_ec2_amis()


def api_ec2_runtime(host_os_hint: str = ""):
    return _srv().api_ec2_runtime(host_os_hint)


def api_ec2_runtime_lxd():
    return _srv().api_ec2_runtime_lxd()


def api_ec2_runtime_multipass():
    return _srv().api_ec2_runtime_multipass()


def api_ec2_runtime_bootstrap():
    return _srv().api_ec2_runtime_bootstrap()


def api_ec2_runtime_lxd_bootstrap():
    return _srv().api_ec2_runtime_lxd_bootstrap()


def api_ec2_runtime_multipass_bootstrap():
    return _srv().api_ec2_runtime_multipass_bootstrap()


def api_ec2_list_instances():
    return _srv().api_ec2_list_instances()


def api_ec2_create_instance(req: EC2InstanceRequest, *, auto_start: bool = True, host_os_hint: str = ""):
    return _srv().api_ec2_create_instance(req, auto_start=auto_start, host_os_hint=host_os_hint)


def api_ec2_start_instance(instance_id: str):
    return _srv().api_ec2_start_instance(instance_id)


def api_ec2_stop_instance(instance_id: str):
    return _srv().api_ec2_stop_instance(instance_id)


def api_ec2_reboot_instance(instance_id: str):
    return _srv().api_ec2_reboot_instance(instance_id)


def api_ec2_terminate_instance(instance_id: str):
    return _srv().api_ec2_terminate_instance(instance_id)


def api_ec2_console(instance_id: str):
    return _srv().api_ec2_console(instance_id)


def api_ec2_console_input(instance_id: str, req: EC2ConsoleInputRequest):
    return _srv().api_ec2_console_input(instance_id, req)


def api_ec2_console_exec(instance_id: str, req: EC2ConsoleCommandRequest):
    return _srv().api_ec2_console_exec(instance_id, req)


# ---------------------------------------------------------------------------
# EC2 Query API (XML wire protocol)
# ---------------------------------------------------------------------------

async def api_ec2_query(request: Request):
    return await _srv().api_ec2_query(request)


# ---------------------------------------------------------------------------
# WebSocket console endpoints
# ---------------------------------------------------------------------------

async def ws_ec2_console(websocket: WebSocket, instance_id: str):
    instance = ec2_state["instances"].get(instance_id)
    if not instance:
        await websocket.close(code=1008)
        return
    await _srv()._instance_console_ws(
        websocket, instance, instance_id, "EC2",
        "Instance console is not active. Start the instance first.",
    )


async def ws_runtime_console(websocket: WebSocket, instance_id: str):
    await ws_ec2_console(websocket, instance_id)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register(app: FastAPI) -> None:
    """Register EC2 routes directly on the FastAPI app.

    EC2 routes are partially registered via providers/aws_ec2_routes.py
    (REST JSON endpoints) and partially via @app decorators for query-protocol
    and WebSocket endpoints.  This register() adds the query-protocol and
    WebSocket endpoints.
    """

    @app.api_route("/ec2", methods=["GET", "POST"], include_in_schema=False)
    @app.api_route("/api/ec2/aws", methods=["GET", "POST"], include_in_schema=False)
    async def _ec2_query(request: Request):
        return await api_ec2_query(request)

    @app.websocket("/ws/ec2/instances/{instance_id}/console")
    async def _ws_ec2_console(websocket: WebSocket, instance_id: str):
        await ws_ec2_console(websocket, instance_id)

    @app.websocket("/ws/runtime-console/{instance_id}")
    async def _ws_runtime_console(websocket: WebSocket, instance_id: str):
        await ws_runtime_console(websocket, instance_id)
