#!/usr/bin/env python3
"""Analyze a Proxmox cluster JSON snapshot and propose safe VM moves (no API calls)."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

GIB = 1024 ** 3


def number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def analyze(document: Any, cpu_limit: float = 80.0, memory_limit: float = 85.0,
            vcpu_limit: float = 2.5) -> dict[str, Any]:
    warnings: list[dict[str, Any]] = []

    def warn(record: str, message: str) -> None:
        warnings.append({"record": record, "message": message})

    if not isinstance(document, dict):
        raise ValueError("top-level JSON value must be an object")

    raw_nodes = document.get("nodes")
    raw_vms = document.get("vms")
    if not isinstance(raw_nodes, list):
        warn("nodes", "missing or invalid nodes array; treating as empty")
        raw_nodes = []
    if not isinstance(raw_vms, list):
        warn("vms", "missing or invalid vms array; treating as empty")
        raw_vms = []

    nodes: dict[str, dict[str, Any]] = {}
    for i, item in enumerate(raw_nodes):
        rec = f"nodes[{i}]"
        if not isinstance(item, dict):
            warn(rec, "record is not an object; skipped")
            continue
        name = item.get("node")
        if not isinstance(name, str) or not name.strip():
            warn(rec, "missing/invalid node name; skipped")
            continue
        if name in nodes:
            warn(rec, f"duplicate node {name!r}; later record skipped")
            continue
        status = item.get("status")
        if status not in ("online", "offline"):
            warn(rec, f"unexpected status {status!r}; node is not eligible for migration")
            status = "unknown"
        cores = item.get("cpu_cores")
        if not number(cores) or cores <= 0:
            warn(rec, f"invalid cpu_cores={cores!r}; CPU metrics unavailable")
            cores = None
        mem_total = item.get("mem_total")
        if not number(mem_total) or mem_total <= 0:
            warn(rec, f"invalid mem_total={mem_total!r}; RAM metrics unavailable")
            mem_total = None
        elif mem_total < GIB:
            # A 32-core Proxmox host reporting 256 KiB RAM is not a usable capacity signal.
            warn(rec, f"implausibly small mem_total={mem_total} bytes (<1 GiB); RAM metrics unavailable")
            mem_total = None
        nodes[name] = {
            "node": name, "status": status, "cpu_cores": cores,
            "mem_total": mem_total, "cpu_used_cores": 0.0,
            "vcpu_allocated": 0.0, "mem_used": 0.0,
            "cpu_complete": cores is not None,
            "memory_complete": mem_total is not None,
            "vcpu_complete": cores is not None,
            "running_vms": 0,
        }

    vms: list[dict[str, Any]] = []
    seen_ids: set[Any] = set()
    for i, item in enumerate(raw_vms):
        rec = f"vms[{i}]"
        if not isinstance(item, dict):
            warn(rec, "record is not an object; skipped")
            continue
        vmid = item.get("vmid")
        if vmid is None or isinstance(vmid, bool) or not isinstance(vmid, (str, int)):
            warn(rec, f"missing/invalid vmid={vmid!r}; skipped")
            continue
        if vmid in seen_ids:
            warn(rec, f"duplicate vmid={vmid!r}; later record skipped to avoid double-counting")
            continue
        seen_ids.add(vmid)
        name = item.get("name") if isinstance(item.get("name"), str) else str(vmid)
        node_name = item.get("node")
        status = item.get("status")
        if status != "running":
            if status not in ("stopped", "paused", "suspended"):
                warn(rec, f"unexpected VM status={status!r}; skipped")
            continue
        if not isinstance(node_name, str) or node_name not in nodes:
            warn(rec, f"node={node_name!r} is absent from nodes[]; VM {vmid} excluded")
            continue
        node = nodes[node_name]

        vcpus = item.get("vcpus")
        vcpu_ok = number(vcpus) and vcpus > 0
        if not vcpu_ok:
            warn(rec, f"invalid vcpus={vcpus!r}; CPU and overcommit metrics incomplete")
            node["cpu_complete"] = node["vcpu_complete"] = False
        cpu_usage = item.get("cpu_usage")
        cpu_ok = number(cpu_usage) and 0 <= cpu_usage <= 1
        if not cpu_ok:
            warn(rec, f"cpu_usage={cpu_usage!r} outside documented range [0, 1]; CPU metrics incomplete")
            node["cpu_complete"] = False
        mem_max = item.get("mem_max")
        memmax_ok = number(mem_max) and mem_max >= 0
        if not memmax_ok:
            warn(rec, f"invalid mem_max={mem_max!r}; RAM metrics incomplete")
            node["memory_complete"] = False
        mem_used = item.get("mem_used")
        memused_ok = number(mem_used) and mem_used >= 0
        if not memused_ok:
            warn(rec, f"invalid mem_used={mem_used!r}; RAM metrics incomplete")
            node["memory_complete"] = False
        if memmax_ok and memused_ok and mem_used > mem_max:
            warn(rec, f"mem_used={mem_used} exceeds mem_max={mem_max}; RAM metrics incomplete")
            node["memory_complete"] = False
            memused_ok = False

        if vcpu_ok:
            node["vcpu_allocated"] += float(vcpus)
        if vcpu_ok and cpu_ok:
            node["cpu_used_cores"] += float(vcpus) * float(cpu_usage)
        if memused_ok:
            node["mem_used"] += float(mem_used)
        node["running_vms"] += 1
        vms.append({
            "vmid": vmid, "name": name, "node": node_name,
            "vcpus": float(vcpus) if vcpu_ok else None,
            "cpu_usage": float(cpu_usage) if cpu_ok else None,
            "mem_max": float(mem_max) if memmax_ok else None,
            "mem_used": float(mem_used) if memused_ok else None,
            "complete": vcpu_ok and cpu_ok and memmax_ok and memused_ok,
        })

    for node in nodes.values():
        node["cpu_pct"] = (100 * node["cpu_used_cores"] / node["cpu_cores"]
                           if node["cpu_cores"] and node["cpu_complete"] else None)
        node["memory_pct"] = (100 * node["mem_used"] / node["mem_total"]
                              if node["mem_total"] and node["memory_complete"] else None)
        node["vcpu_per_core"] = (node["vcpu_allocated"] / node["cpu_cores"]
                                 if node["cpu_cores"] and node["vcpu_complete"] else None)
        node["cpu_overloaded"] = node["cpu_pct"] is not None and node["cpu_pct"] > cpu_limit
        node["memory_overloaded"] = node["memory_pct"] is not None and node["memory_pct"] > memory_limit
        node["vcpu_overloaded"] = node["vcpu_per_core"] is not None and node["vcpu_per_core"] > vcpu_limit
        known_overload = node["cpu_overloaded"] or node["memory_overloaded"] or node["vcpu_overloaded"]
        complete = node["cpu_pct"] is not None and node["memory_pct"] is not None and node["vcpu_per_core"] is not None
        node["overload"] = ("offline" if node["status"] == "offline" else
                            "overloaded" if known_overload else
                            "unknown" if not complete or node["status"] != "online" else "normal")
        node["complete"] = complete and node["status"] == "online"

    plan: list[dict[str, Any]] = []
    # Plan a sequence of moves. Never use a node with uncertain capacity; every
    # destination must stay under limits, and each source move must reduce overload.
    for _ in range(len(vms)):
        sources = [n for n in nodes.values() if n["overload"] == "overloaded" and n["complete"]]
        if not sources:
            break
        best: tuple[tuple[float, ...], dict[str, Any], dict[str, Any]] | None = None
        for source in sources:
            for vm in [v for v in vms if v["node"] == source["node"] and v["complete"]]:
                for target in nodes.values():
                    if target["node"] == source["node"] or target["status"] != "online" or not target["complete"]:
                        continue
                    src_after = projected(source, vm, direction=-1)
                    dst_after = projected(target, vm, direction=1)
                    if overload_severity(src_after, cpu_limit, memory_limit, vcpu_limit) >= overload_severity(
                            source, cpu_limit, memory_limit, vcpu_limit):
                        continue
                    if is_overloaded(dst_after, cpu_limit, memory_limit, vcpu_limit):
                        continue
                    # First reduce source overload, then prefer the least-loaded
                    # destination and lower measured VM resource use.
                    score = (overload_severity(src_after, cpu_limit, memory_limit, vcpu_limit),
                             max(dst_after["cpu_pct"] / cpu_limit,
                                 dst_after["memory_pct"] / memory_limit,
                                 dst_after["vcpu_per_core"] / vcpu_limit),
                             vm["cpu_usage"] * vm["vcpus"], vm["mem_used"])
                    if best is None or score < best[0]:
                        best = (score, vm, target)
        if best is None:
            break
        _, vm, target = best
        source = nodes[vm["node"]]
        before_src = metrics(source)
        before_dst = metrics(target)
        apply_move(source, vm, -1)
        apply_move(target, vm, 1)
        vm["node"] = target["node"]
        for n in (source, target):
            refresh_node(n, cpu_limit, memory_limit, vcpu_limit)
        plan.append({
            "vmid": vm["vmid"], "name": vm["name"],
            "from": source["node"], "to": target["node"],
            "reason": "safe under configured CPU, RAM, and vCPU limits; verify storage/affinity before execution",
            "source_before": before_src, "source_after": metrics(source),
            "target_before": before_dst, "target_after": metrics(target),
        })

    unresolved = [n["node"] for n in nodes.values()
                  if n["status"] == "online" and n["overload"] != "normal"]
    return {
        "cluster": document.get("cluster"),
        "collected_at": document.get("collected_at"),
        "thresholds": {"cpu_percent": cpu_limit, "memory_percent": memory_limit,
                       "vcpu_per_core": vcpu_limit},
        "nodes": [metrics(n, include_meta=True) for n in nodes.values()],
        "overloaded_nodes": [n["node"] for n in nodes.values() if n["overload"] == "overloaded"],
        "unresolved_online_nodes": unresolved,
        "migration_complete": not unresolved,
        "migration_plan": plan,
        "warnings": warnings,
    }


def projected(node: dict[str, Any], vm: dict[str, Any], direction: int) -> dict[str, float]:
    cores = node["cpu_cores"]
    total = node["mem_total"]
    cpu_used = node["cpu_used_cores"] + direction * vm["vcpus"] * vm["cpu_usage"]
    mem_used = node["mem_used"] + direction * vm["mem_used"]
    vcpu_alloc = node["vcpu_allocated"] + direction * vm["vcpus"]
    return {"cpu_pct": 100 * cpu_used / cores,
            "memory_pct": 100 * mem_used / total,
            "vcpu_per_core": vcpu_alloc / cores,
            "cpu_used_cores": cpu_used, "mem_used": mem_used,
            "vcpu_allocated": vcpu_alloc}


def apply_move(node: dict[str, Any], vm: dict[str, Any], direction: int) -> None:
    node["cpu_used_cores"] += direction * vm["vcpus"] * vm["cpu_usage"]
    node["mem_used"] += direction * vm["mem_used"]
    node["vcpu_allocated"] += direction * vm["vcpus"]
    node["running_vms"] += direction


def refresh_node(node: dict[str, Any], cpu_limit: float, memory_limit: float, vcpu_limit: float) -> None:
    node["cpu_pct"] = 100 * node["cpu_used_cores"] / node["cpu_cores"]
    node["memory_pct"] = 100 * node["mem_used"] / node["mem_total"]
    node["vcpu_per_core"] = node["vcpu_allocated"] / node["cpu_cores"]
    node["cpu_overloaded"] = node["cpu_pct"] > cpu_limit
    node["memory_overloaded"] = node["memory_pct"] > memory_limit
    node["vcpu_overloaded"] = node["vcpu_per_core"] > vcpu_limit
    node["overload"] = "overloaded" if is_overloaded(node, cpu_limit, memory_limit, vcpu_limit) else "normal"


def is_overloaded(m: dict[str, Any], cpu_limit: float, memory_limit: float, vcpu_limit: float) -> bool:
    return (m["cpu_pct"] > cpu_limit or m["memory_pct"] > memory_limit
            or m["vcpu_per_core"] > vcpu_limit)


def overload_severity(m: dict[str, Any], cpu_limit: float, memory_limit: float, vcpu_limit: float) -> float:
    return (max(0.0, m["cpu_pct"] / cpu_limit - 1.0)
            + max(0.0, m["memory_pct"] / memory_limit - 1.0)
            + max(0.0, m["vcpu_per_core"] / vcpu_limit - 1.0))


def metrics(node: dict[str, Any], include_meta: bool = False) -> dict[str, Any]:
    result = {
        "node": node["node"], "status": node["status"],
        "cpu_used_cores": round(node["cpu_used_cores"], 2),
        "cpu_cores": node["cpu_cores"], "cpu_percent": round(node["cpu_pct"], 2) if node["cpu_pct"] is not None else None,
        "memory_used_bytes": int(node["mem_used"]), "memory_total_bytes": int(node["mem_total"]) if node["mem_total"] is not None else None,
        "memory_percent": round(node["memory_pct"], 2) if node["memory_pct"] is not None else None,
        "vcpu_allocated": round(node["vcpu_allocated"], 2),
        "vcpu_per_core": round(node["vcpu_per_core"], 2) if node["vcpu_per_core"] is not None else None,
        "running_vms": node["running_vms"], "overload": node["overload"],
    }
    if include_meta:
        result["capacity_data_complete"] = node["complete"]
    return result


def table(report: dict[str, Any]) -> str:
    headers = ("NODE", "CPU used", "RAM used", "vCPU/core", "VMs", "STATE")
    rows = []
    for n in report["nodes"]:
        cpu = "unknown" if n["cpu_percent"] is None else f"{n['cpu_used_cores']:.1f}/{n['cpu_cores']} ({n['cpu_percent']:.1f}%)"
        ram = "unknown" if n["memory_percent"] is None else f"{n['memory_percent']:.1f}%"
        ratio = "unknown" if n["vcpu_per_core"] is None else f"{n['vcpu_per_core']:.2f}x"
        rows.append((n["node"], cpu, ram, ratio, str(n["running_vms"]), n["overload"]))
    widths = [max(len(headers[i]), *(len(r[i]) for r in rows)) for i in range(len(headers))]
    out = ["  ".join(headers[i].ljust(widths[i]) for i in range(len(headers))),
           "  ".join("-" * widths[i] for i in range(len(headers)))]
    out.extend("  ".join(row[i].ljust(widths[i]) for i in range(len(headers))) for row in rows)
    out.append("\nMigration suggestions (not executed):")
    out.append("  status: " + ("complete" if report["migration_complete"] else "partial / blocked by unresolved node data or overload"))
    if report["migration_plan"]:
        for m in report["migration_plan"]:
            after = m["source_after"]
            out.append(f"  VM {m['vmid']} {m['name']}: {m['from']} -> {m['to']} "
                       f"(source after CPU {after['cpu_percent']:.1f}%, RAM {after['memory_percent']:.1f}%)")
    else:
        out.append("  none; no safe move found for fully validated node capacities")
    if report["overloaded_nodes"]:
        out.append("Overloaded: " + ", ".join(report["overloaded_nodes"]))
    if report["unresolved_online_nodes"]:
        out.append("Unresolved online nodes: " + ", ".join(report["unresolved_online_nodes"]))
    if report["warnings"]:
        out.append("Warnings:")
        out.extend(f"  - {w['record']}: {w['message']}" for w in report["warnings"])
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="cluster JSON snapshot")
    parser.add_argument("--format", choices=("table", "json"), default="table")
    parser.add_argument("--cpu-limit", type=float, default=80.0, help="CPU overload threshold percent (default: 80)")
    parser.add_argument("--memory-limit", type=float, default=85.0, help="RAM overload threshold percent (default: 85)")
    parser.add_argument("--vcpu-limit", type=float, default=2.5, help="max allocated vCPU per physical core (default: 2.5)")
    args = parser.parse_args(argv)
    try:
        document = json.loads(args.input.read_text(encoding="utf-8"))
        report = analyze(document, args.cpu_limit, args.memory_limit, args.vcpu_limit)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: cannot analyze {args.input}: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    else:
        print(table(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
