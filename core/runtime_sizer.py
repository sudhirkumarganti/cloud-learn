"""Map a real cloud instance type → host-feasible LXD / multipass container
limits.

The user picks (say) ``m5.8xlarge`` (32 vCPU / 128 GB). Your laptop has 8
cores and 16 GB. We can't honestly hand that to LXD. But the simulator should
still reflect the *relative* choice — bigger SKU → bigger container — within
the host's actual budget.

The mapping:

    tier_score = max(vcpu, ram_in_GB)

    score ≤ 1   → nano    (1 CPU,  256 MB)
    score ≤ 4   → small   (1 CPU,  512 MB)
    score ≤ 16  → medium  (2 CPU, 1024 MB)
    score ≤ 32  → large   (3 CPU, 2048 MB)
    score ≤ 64  → xlarge  (4 CPU, 4096 MB)
    score >  64 → huge    (5 CPU, 6144 MB)

then clamped by host: never more than ``host_cpus // 2`` CPUs or
``host_lxd_memory_mb // 3`` memory on one container, so several coexist.

The caller stores BOTH the requested shape (what the user picked) AND the
provisioned tier (what the container actually got), so the gap is visible in
the SDK / SPA response — e.g.::

    "runtime_sizing": {
        "requested_vcpu": 32, "requested_ram_mb": 131072,
        "cpu": 4, "memory_mb": 4096, "tier": "huge"
    }
"""
from __future__ import annotations


# Tier table: (max_score, tier_name, default_cpu, default_mem_mb).
_TIERS = (
    (1,     "nano",   1,  256),
    (4,     "small",  1,  512),
    (16,    "medium", 2, 1024),
    (32,    "large",  3, 2048),
    (64,    "xlarge", 4, 4096),
    (1 << 30, "huge",  5, 6144),
)


def shape_for_instance(instance_type: str, provider: str) -> dict | None:
    """Catalog lookup. `instance_type` is the bare name for AWS/Azure or either
    the bare name or full URL for GCP machineType (we strip to the last path
    segment). Returns None if unknown — caller should fall back to defaults."""
    from core import instance_catalog as cat
    p = (provider or "").strip().lower()
    if not instance_type:
        return None
    if p == "aws":
        shape = cat.AWS.get(instance_type)
    elif p == "gcp":
        name = str(instance_type).rstrip("/").rsplit("/", 1)[-1]
        shape = cat.GCP.get(name)
    elif p == "azure":
        shape = cat.AZURE.get(instance_type)
    else:
        shape = None
    if not shape:
        return None
    return {**shape, "name": instance_type}


def lxd_limits(shape: dict, host_cpus: int, host_mem_mb: int) -> dict:
    vcpu = max(1, int(shape.get("vcpu", 1)))
    ram_mb = max(128, int(shape.get("ram_mb", 1024)))
    score = max(vcpu, ram_mb // 1024 or 1)
    name, cpu, mem = "huge", 5, 6144
    for max_score, tn, tc, tm in _TIERS:
        if score <= max_score:
            name, cpu, mem = tn, tc, tm
            break
    cpu_cap = max(1, int(host_cpus) // 2)
    mem_cap = max(256, int(host_mem_mb) // 3)
    return {
        "tier": name,
        "cpu": min(cpu, cpu_cap),
        "memory_mb": min(mem, mem_cap),
        "requested_vcpu": vcpu,
        "requested_ram_mb": ram_mb,
        "host_cpu_cap": cpu_cap,
        "host_mem_cap_mb": mem_cap,
    }


def host_budget_caps() -> tuple[int, int]:
    """Per-container ceilings respect the SIMULATOR'S budget (which is itself a
    clamp 30-50% of host) — so individual tiers can't blow past the platform's
    share even on a big host. Falls back to a conservative default if server
    isn't importable (e.g., unit tests)."""
    try:
        import server
        b = server._simulator_budget()
        return int(b.get("cpu") or 2), int(b.get("memory_mb") or 2048)
    except Exception:
        import os
        return (os.cpu_count() or 2), 2048


def for_instance_type(instance_type: str, provider: str) -> dict | None:
    """Convenience: catalog lookup + host-aware tier mapping in one call.
    Returns None if the instance_type isn't in the catalog (the caller should
    then launch with no `limits.*` flags, accepting LXD defaults)."""
    shape = shape_for_instance(instance_type, provider)
    if not shape:
        return None
    cpus, mem_mb = host_budget_caps()
    return {
        **lxd_limits(shape, cpus, mem_mb),
        "instance_type": instance_type,
        "family": shape.get("family", "general"),
    }
