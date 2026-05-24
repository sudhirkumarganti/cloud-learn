from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def _server():
    import server as server_module

    return server_module


def api_vpc_list_vpcs():
    s = _server()
    vpcs = []
    for vpc in s.vpc_state["vpcs"].values():
        vpc_id = vpc["vpc_id"]
        subnets = [item for item in s.vpc_state["subnets"].values() if item.get("vpc_id") == vpc_id]
        route_tables = [item for item in s.vpc_state["route_tables"].values() if item.get("vpc_id") == vpc_id]
        security_groups = [item for item in s.vpc_state["security_groups"].values() if item.get("vpc_id") == vpc_id]
        internet_gateways = [item for item in s.vpc_state.get("internet_gateways", {}).values() if item.get("attached_vpc_id") == vpc_id]
        vpcs.append(
            {
                **vpc,
                "subnet_count": len(subnets),
                "route_table_count": len(route_tables),
                "security_group_count": len(security_groups),
                "internet_gateway_count": len(internet_gateways),
                "availability_zones": sorted({item.get("availability_zone", "") for item in subnets if item.get("availability_zone")}),
            }
        )
    return {"vpcs": vpcs, "count": len(s.vpc_state["vpcs"])}


def api_vpc_create(req):
    s = _server()
    vpc_id = s._id("vpc")
    default_rt_id = s._id("rtb")
    default_sg_id = s._id("sg")
    vpc = {
        "vpc_id": vpc_id,
        "name": req.name,
        "cidr_block": req.cidr_block,
        "encryption_controls": req.encryption_controls,
        "tenancy": req.tenancy,
        "ipv6_mode": req.ipv6_mode,
        "tags": req.tags or [],
        "created": s._now(),
        "state": "available",
        "dhcp_options_id": f"dopt-{vpc_id.replace('vpc-', '')[:8] or s.secrets.token_hex(4)}",
        "main_route_table_id": default_rt_id,
        "default_security_group_id": default_sg_id,
        "internet_gateway_id": "",
    }
    s.vpc_state["vpcs"][vpc_id] = vpc
    s.vpc_state["route_tables"][default_rt_id] = {
        "route_table_id": default_rt_id,
        "vpc_id": vpc_id,
        "name": f"{req.name}-main" if req.name else default_rt_id,
        "routes": [{"destination": vpc["cidr_block"], "target_type": "local", "target_id": vpc_id, "type": "CreateRouteTable", "created": s._now()}],
        "subnet_ids": [],
        "is_main": True,
        "created": s._now(),
        "tags": [],
    }
    s.vpc_state["security_groups"][default_sg_id] = {
        "security_group_id": default_sg_id,
        "vpc_id": vpc_id,
        "group_name": "default",
        "description": "default VPC security group",
        "ingress": [],
        "egress": [{"protocol": "-1", "from_port": 0, "to_port": 0, "cidr": "0.0.0.0/0", "source_sg": "", "description": "allow all outbound traffic", "created": s._now()}],
        "is_default": True,
        "created": s._now(),
        "tags": [],
    }
    s._record_usage("vpc.create_vpc", vpc)
    return vpc


def api_vpc_delete(vpc_id: str, force: bool = False):
    s = _server()
    vpc = s.vpc_state["vpcs"].get(vpc_id)
    if not vpc:
        raise HTTPException(404, detail="NoSuchVpc")

    instances = [item for item in s.ec2_state["instances"].values() if item.get("vpc_id") == vpc_id and item.get("state") not in {"terminated"}]
    if instances and not force:
        raise HTTPException(409, detail="VpcHasActiveInstances")

    if force:
        for inst in instances:
            inst["state"] = "terminated"
            inst["terminated_at"] = s._now()
            inst["updated"] = s._now()
            s._record_usage("vpc.delete.terminate_instance", {"vpc_id": vpc_id, "instance_id": inst.get("instance_id")})

    for subnet_id, subnet in list(s.vpc_state["subnets"].items()):
        if subnet.get("vpc_id") == vpc_id:
            rt_id = subnet.get("route_table_id")
            if rt_id and rt_id in s.vpc_state["route_tables"]:
                rt = s.vpc_state["route_tables"][rt_id]
                rt["subnet_ids"] = [sid for sid in rt.get("subnet_ids", []) if sid != subnet_id]
            del s.vpc_state["subnets"][subnet_id]

    for rt_id, rt in list(s.vpc_state["route_tables"].items()):
        if rt.get("vpc_id") == vpc_id:
            del s.vpc_state["route_tables"][rt_id]

    for sg_id, sg in list(s.vpc_state["security_groups"].items()):
        if sg.get("vpc_id") == vpc_id:
            del s.vpc_state["security_groups"][sg_id]

    for igw_id, igw in list(s.vpc_state.get("internet_gateways", {}).items()):
        if igw.get("attached_vpc_id") == vpc_id:
            del s.vpc_state.get("internet_gateways", {})[igw_id]

    del s.vpc_state["vpcs"][vpc_id]
    s._record_usage("vpc.delete_vpc", {"vpc_id": vpc_id, "force": force})
    return {"deleted": True, "vpc_id": vpc_id}


def api_vpc_create_subnet(req):
    s = _server()
    if req.vpc_id not in s.vpc_state["vpcs"]:
        raise HTTPException(404, detail="NoSuchVpc")
    subnet_id = s._id("subnet")
    main_rt_id = s.vpc_state["vpcs"][req.vpc_id].get("main_route_table_id", "")
    subnet = {
        "subnet_id": subnet_id,
        "vpc_id": req.vpc_id,
        "cidr_block": req.cidr_block,
        "availability_zone": req.availability_zone,
        "name": req.name or subnet_id,
        "route_table_id": main_rt_id,
        "created": s._now(),
        "tags": req.tags or [],
    }
    s.vpc_state["subnets"][subnet_id] = subnet
    if main_rt_id and main_rt_id in s.vpc_state["route_tables"]:
        s._vpc_associate_subnet_to_route_table(main_rt_id, subnet_id)
    s._record_usage("vpc.create_subnet", subnet)
    return subnet


def api_vpc_create_security_group(req):
    s = _server()
    if req.vpc_id not in s.vpc_state["vpcs"]:
        raise HTTPException(404, detail="NoSuchVpc")
    sg_id = s._id("sg")
    sg = {
        "security_group_id": sg_id,
        "vpc_id": req.vpc_id,
        "group_name": req.group_name,
        "description": req.description,
        "ingress": [],
        "egress": [{"protocol": "-1", "from_port": 0, "to_port": 0, "cidr": "0.0.0.0/0", "source_sg": "", "description": "allow all outbound traffic", "created": s._now()}],
        "is_default": False,
        "created": s._now(),
        "tags": req.tags or [],
    }
    s.vpc_state["security_groups"][sg_id] = sg
    s._record_usage("vpc.create_security_group", sg)
    return sg


def api_vpc_add_ingress(sg_id: str, payload: dict[str, Any]):
    s = _server()
    sg = s.vpc_state["security_groups"].get(sg_id)
    if not sg:
        raise HTTPException(404, detail="NoSuchSecurityGroup")
    rule = {
        "protocol": payload.get("protocol", "tcp"),
        "from_port": payload.get("from_port", 0),
        "to_port": payload.get("to_port", 65535),
        "cidr": payload.get("cidr", "0.0.0.0/0"),
        "source_sg": payload.get("source_sg", ""),
        "description": payload.get("description", ""),
        "created": s._now(),
    }
    sg.setdefault("ingress", []).append(rule)
    s._record_usage("vpc.add_ingress", {"sg_id": sg_id, "rule": rule})
    return sg


def api_vpc_list_subnets():
    s = _server()
    return {"subnets": list(s.vpc_state["subnets"].values()), "count": len(s.vpc_state["subnets"])}


def api_vpc_list_security_groups():
    s = _server()
    return {"security_groups": list(s.vpc_state["security_groups"].values()), "count": len(s.vpc_state["security_groups"])}


def api_vpc_list_route_tables():
    s = _server()
    return {"route_tables": list(s.vpc_state["route_tables"].values()), "count": len(s.vpc_state["route_tables"])}


def api_vpc_create_route_table(req):
    s = _server()
    if req.vpc_id not in s.vpc_state["vpcs"]:
        raise HTTPException(404, detail="NoSuchVpc")
    rt_id = s._id("rtb")
    rt = {
        "route_table_id": rt_id,
        "vpc_id": req.vpc_id,
        "name": req.name or rt_id,
        "routes": [{"destination": s.vpc_state["vpcs"][req.vpc_id].get("cidr_block", "10.0.0.0/16"), "target_type": "local", "target_id": req.vpc_id, "type": "CreateRouteTable", "created": s._now()}],
        "subnet_ids": [],
        "is_main": False,
        "created": s._now(),
        "tags": req.tags or [],
    }
    s.vpc_state["route_tables"][rt_id] = rt
    s._record_usage("vpc.create_route_table", rt)
    return rt


def api_vpc_list_internet_gateways():
    s = _server()
    internet_gateways = s.vpc_state.get("internet_gateways", {})
    return {"internet_gateways": list(internet_gateways.values()), "count": len(internet_gateways)}


def api_vpc_create_internet_gateway(req):
    s = _server()
    igw_id = s._id("igw")
    igw = {"internet_gateway_id": igw_id, "name": req.name or igw_id, "attached_vpc_id": "", "created": s._now(), "tags": req.tags or []}
    s.vpc_state.setdefault("internet_gateways", {})[igw_id] = igw
    s._record_usage("vpc.create_internet_gateway", igw)
    return igw


def api_vpc_attach_internet_gateway(igw_id: str, payload: dict[str, Any]):
    s = _server()
    vpc_id = payload.get("vpc_id", "")
    igw = s._vpc_attach_internet_gateway_record(igw_id, vpc_id)
    s._record_usage("vpc.attach_internet_gateway", {"igw_id": igw_id, "vpc_id": vpc_id})
    return igw


def api_vpc_add_route(rt_id: str, payload: dict[str, Any]):
    s = _server()
    rt = s.vpc_state["route_tables"].get(rt_id)
    if not rt:
        raise HTTPException(404, detail="NoSuchRouteTable")
    route = {
        "destination": payload.get("destination_cidr", "0.0.0.0/0"),
        "target_type": payload.get("target_type", "internet-gateway"),
        "target_id": payload.get("target_id", ""),
        "type": "CreateRoute",
        "created": s._now(),
    }
    rt.setdefault("routes", []).append(route)
    s._record_usage("vpc.add_route", {"route_table_id": rt_id, "route": route})
    return rt


def api_vpc_associate_subnet(rt_id: str, req):
    s = _server()
    s._vpc_associate_subnet_to_route_table(rt_id, req.subnet_id)
    s._record_usage("vpc.associate_subnet", {"route_table_id": rt_id, "subnet_id": req.subnet_id})
    return s.vpc_state["route_tables"][rt_id]


def api_vpc_resources(vpc_id: str):
    s = _server()
    if vpc_id not in s.vpc_state["vpcs"]:
        raise HTTPException(404, detail="NoSuchVpc")
    subnets = [item for item in s.vpc_state["subnets"].values() if item.get("vpc_id") == vpc_id]
    route_tables = [item for item in s.vpc_state["route_tables"].values() if item.get("vpc_id") == vpc_id]
    security_groups = [item for item in s.vpc_state["security_groups"].values() if item.get("vpc_id") == vpc_id]
    internet_gateways = [item for item in s.vpc_state.get("internet_gateways", {}).values() if item.get("attached_vpc_id") == vpc_id]
    instances = [item for item in s.ec2_state["instances"].values() if item.get("vpc_id") == vpc_id]
    return {
        "vpc": s.vpc_state["vpcs"][vpc_id],
        "subnets": subnets,
        "route_tables": route_tables,
        "security_groups": security_groups,
        "internet_gateways": internet_gateways,
        "instances": instances,
        "counts": {
            "subnets": len(subnets),
            "route_tables": len(route_tables),
            "security_groups": len(security_groups),
            "internet_gateways": len(internet_gateways),
            "instances": len(instances),
        },
    }
