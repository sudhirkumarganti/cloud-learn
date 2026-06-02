from __future__ import annotations

from fastapi import Request

from core.models import EC2InstanceRequest, EC2ConsoleInputRequest, EC2ConsoleCommandRequest


def _server():
    import server as server_module

    return server_module


def register(app, h) -> None:
    @app.get("/api/ec2/amis")
    def api_ec2_amis():
        return _server().api_ec2_amis()

    @app.get("/api/ec2/runtime")
    def api_ec2_runtime(request: Request):
        return _server().api_ec2_runtime(request.headers.get("x-cloudlearn-host-os", ""))

    @app.get("/api/ec2/runtime/lxd")
    def api_ec2_runtime_lxd():
        return _server().api_ec2_runtime_lxd()

    @app.get("/api/ec2/runtime/multipass")
    def api_ec2_runtime_multipass():
        return _server().api_ec2_runtime_multipass()

    @app.post("/api/ec2/runtime/bootstrap")
    def api_ec2_runtime_bootstrap():
        return _server().api_ec2_runtime_bootstrap()

    @app.post("/api/ec2/runtime/lxd/bootstrap")
    def api_ec2_runtime_lxd_bootstrap():
        return _server().api_ec2_runtime_lxd_bootstrap()

    @app.post("/api/ec2/runtime/multipass/bootstrap")
    def api_ec2_runtime_multipass_bootstrap():
        return _server().api_ec2_runtime_multipass_bootstrap()

    @app.get("/api/ec2/instances")
    def api_ec2_list_instances():
        return _server().api_ec2_list_instances()

    @app.post("/api/ec2/instances")
    async def api_ec2_create_instance(request: Request, auto_start: bool = True):
        payload = {}
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        model = EC2InstanceRequest(**payload)
        return _server().api_ec2_create_instance(
            model,
            auto_start=auto_start,
            host_os_hint=request.headers.get("x-cloudlearn-host-os", ""),
        )

    @app.post("/api/ec2/instances/{instance_id}/start")
    def api_ec2_start_instance(instance_id: str):
        return _server().api_ec2_start_instance(instance_id)

    @app.post("/api/ec2/instances/{instance_id}/stop")
    def api_ec2_stop_instance(instance_id: str):
        return _server().api_ec2_stop_instance(instance_id)

    @app.post("/api/ec2/instances/{instance_id}/reboot")
    def api_ec2_reboot_instance(instance_id: str):
        return _server().api_ec2_reboot_instance(instance_id)

    @app.post("/api/ec2/instances/{instance_id}/terminate")
    def api_ec2_terminate_instance(instance_id: str):
        return _server().api_ec2_terminate_instance(instance_id)

    @app.get("/api/ec2/instances/{instance_id}/console")
    def api_ec2_console(instance_id: str):
        return _server().api_ec2_console(instance_id)

    @app.post("/api/ec2/instances/{instance_id}/console/input")
    async def api_ec2_console_input(instance_id: str, request: Request):
        payload = {}
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        model = EC2ConsoleInputRequest(**payload)
        return _server().api_ec2_console_input(instance_id, model)

    @app.post("/api/ec2/instances/{instance_id}/console/exec")
    async def api_ec2_console_exec(instance_id: str, request: Request):
        payload = {}
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        model = EC2ConsoleCommandRequest(**payload)
        return _server().api_ec2_console_exec(instance_id, model)
