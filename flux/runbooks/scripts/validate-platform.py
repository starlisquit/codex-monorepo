#!/usr/bin/env python3
"""Check readiness dependencies and component coverage without accessing a cluster."""
from pathlib import Path
import sys
import yaml

flux_root = Path(__file__).resolve().parents[2]
cluster_root = flux_root / "clusters/iximiuz-platform"
resources = list(yaml.safe_load_all((cluster_root / "infrastructure.yaml").read_text()))
by_name = {r["metadata"]["name"]: r for r in resources}
if len(by_name) != len(resources):
    raise SystemExit("Duplicate Flux Kustomization name")

visited = set()
def visit(name, stack):
    if name not in by_name:
        raise SystemExit(f"Unknown dependency {name!r}, referenced by {stack}")
    if name in stack:
        raise SystemExit(f"Dependency cycle: {' -> '.join(stack + [name])}")
    if name in visited:
        return
    resource = by_name[name]
    relative = resource["spec"]["path"].removeprefix("./flux/")
    if not (flux_root / relative / "kustomization.yaml").is_file():
        raise SystemExit(f"Missing Kustomize path: {relative}")
    for dependency in resource["spec"].get("dependsOn", []):
        visit(dependency["name"], stack + [name])
    visited.add(name)

for name in by_name:
    visit(name, [])

for name in ("observability", "postgresql", "nats", "openbao", "valkey"):
    dependencies = {d["name"] for d in by_name[name]["spec"].get("dependsOn", [])}
    if "storage-ready" not in dependencies:
        raise SystemExit(f"{name} must wait for the Ceph write/read smoke test")

for resource in resources:
    if resource["metadata"]["name"] != "foundation" and not resource["spec"].get("dependsOn"):
        raise SystemExit(f"Missing readiness dependencies: {resource['metadata']['name']}")

expected_releases = set()
for tree in ("infrastructure", "security"):
    for manifest in (flux_root / tree).rglob("helmrelease.yaml"):
        release = yaml.safe_load(manifest.read_text())
        expected_releases.add((release["metadata"]["namespace"], release["metadata"]["name"]))
checked_releases = {
    (check["namespace"], check["name"])
    for resource in resources for check in resource["spec"].get("healthChecks", [])
    if check["kind"] == "HelmRelease"
}
if expected_releases != checked_releases:
    raise SystemExit(f"Release coverage differs: missing={expected_releases - checked_releases}, unknown={checked_releases - expected_releases}")
print(f"Validated {len(resources)} Flux Kustomizations and {len(expected_releases)} releases: paths, dependency DAG, and storage gates")
