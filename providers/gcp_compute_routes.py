from __future__ import annotations

from fastapi import Request


def _server():
    import server as server_module

    return server_module


def register(app, h) -> None:
    @app.get("/compute/v1/projects/{project}/zones/{zone}/instances")
    @app.get("/api/gcp/compute/v1/projects/{project}/zones/{zone}/instances")
    def api_gcp_compute_list_instances(project: str, zone: str):
        return _server().api_gcp_compute_list_instances(project, zone)

    @app.post("/compute/v1/projects/{project}/zones/{zone}/instances")
    @app.post("/api/gcp/compute/v1/projects/{project}/zones/{zone}/instances")
    async def api_gcp_compute_create_instance(project: str, zone: str, request: Request):
        return await _server().api_gcp_compute_create_instance(project, zone, request)

    @app.get("/compute/v1/projects/{project}/zones/{zone}/instances/{instance}")
    @app.get("/api/gcp/compute/v1/projects/{project}/zones/{zone}/instances/{instance}")
    def api_gcp_compute_get_instance(project: str, zone: str, instance: str):
        return _server().api_gcp_compute_get_instance(project, zone, instance)

    @app.post("/compute/v1/projects/{project}/zones/{zone}/instances/{instance}/start")
    @app.post("/api/gcp/compute/v1/projects/{project}/zones/{zone}/instances/{instance}/start")
    def api_gcp_compute_start_instance(project: str, zone: str, instance: str):
        return _server().api_gcp_compute_start_instance(project, zone, instance)

    @app.post("/compute/v1/projects/{project}/zones/{zone}/instances/{instance}/stop")
    @app.post("/api/gcp/compute/v1/projects/{project}/zones/{zone}/instances/{instance}/stop")
    def api_gcp_compute_stop_instance(project: str, zone: str, instance: str):
        return _server().api_gcp_compute_stop_instance(project, zone, instance)

    @app.post("/compute/v1/projects/{project}/zones/{zone}/instances/{instance}/reset")
    @app.post("/api/gcp/compute/v1/projects/{project}/zones/{zone}/instances/{instance}/reset")
    def api_gcp_compute_reset_instance(project: str, zone: str, instance: str):
        return _server().api_gcp_compute_reset_instance(project, zone, instance)

    @app.delete("/compute/v1/projects/{project}/zones/{zone}/instances/{instance}")
    @app.delete("/api/gcp/compute/v1/projects/{project}/zones/{zone}/instances/{instance}")
    @app.post("/compute/v1/projects/{project}/zones/{zone}/instances/{instance}/delete")
    @app.post("/api/gcp/compute/v1/projects/{project}/zones/{zone}/instances/{instance}/delete")
    def api_gcp_compute_delete_instance(project: str, zone: str, instance: str):
        return _server().api_gcp_compute_delete_instance(project, zone, instance)

    @app.get("/compute/v1/projects/{project}/zones/{zone}/operations/{operation_id}")
    @app.get("/api/gcp/compute/v1/projects/{project}/zones/{zone}/operations/{operation_id}")
    def api_gcp_compute_get_operation(project: str, zone: str, operation_id: str):
        return _server().api_gcp_compute_get_operation(project, zone, operation_id)
