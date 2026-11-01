#!/usr/bin/env python3
"""Validate every run's Flux path, dependency DAG and selected prerequisites."""
from pathlib import Path
from flux_render import build, substitute, variables_for
import os
import subprocess
import yaml

flux_root = Path(__file__).resolve().parents[3]
repo_root = flux_root.parent
kustomize = os.environ.get('KUSTOMIZE_BIN', 'kustomize')
for manifest in (flux_root / 'infrastructure').rglob('helmrelease.yaml'):
    release = yaml.safe_load(manifest.read_text())
    if release['spec'].get('suspend', False):
        raise SystemExit(f'Shared release must reconcile when selected: {manifest}')

runs = sorted((flux_root / 'clusters').glob('*/infrastructure.yaml'))
for manifest in runs:
    run = manifest.parent
    sync = list(yaml.safe_load_all((run / 'flux-system/gotk-sync.yaml').read_text()))
    root = next(o for o in sync if o['kind'] == 'Kustomization')
    expected_path = './' + run.relative_to(repo_root).as_posix()
    if root['spec']['path'] != expected_path:
        raise SystemExit(f'Flux must point to its own run folder: {run}')
    variables = variables_for(run)
    resources = [o for o in build(run, variables) if o['kind'] == 'Kustomization' and o['apiVersion'] == 'kustomize.toolkit.fluxcd.io/v1' and o['metadata']['name'] != 'flux-system']
    by_name = {o['metadata']['name']: o for o in resources}
    if len(by_name) != len(resources):
        raise SystemExit(f'Duplicate Flux Kustomization name: {run}')
    visited = set()
    objects = []
    def visit(name, stack):
        if name not in by_name:
            raise SystemExit(f'Unknown dependency {name} in {run}')
        if name in stack:
            raise SystemExit(f'Dependency cycle: {stack + [name]}')
        if name in visited:
            return
        o = by_name[name]
        if o['spec'].get('suspend', False):
            raise SystemExit(f'Selected component is suspended: {name}')
        path = (repo_root / o['spec']['path'].removeprefix('./')).resolve()
        if not path.is_relative_to(flux_root) or not (path / 'kustomization.yaml').is_file():
            raise SystemExit(f'Missing/outside Flux path: {path}')
        if name != 'foundation' and not o['spec'].get('dependsOn'):
            raise SystemExit(f'Missing readiness dependencies: {name}')
        for dep in o['spec'].get('dependsOn', []):
            visit(dep['name'], stack + [name])
        objects.extend(build(path, {**variables, **o['spec'].get('postBuild', {}).get('substitute', {})}))
        visited.add(name)
    for name in by_name:
        visit(name, [])
    identities = {(o['apiVersion'], o['kind'], o['metadata'].get('namespace', ''), o['metadata']['name']) for o in objects}
    if len(identities) != len(objects):
        raise SystemExit(f'Duplicate selected object ownership: {run}')
    checks = {(h['apiVersion'], h['kind'], h.get('namespace', ''), h['name']) for o in resources for h in o['spec'].get('healthChecks', [])}
    releases = [o for o in objects if o['kind'] == 'HelmRelease']
    expected = {(o['apiVersion'], o['kind'], o['metadata']['namespace'], o['metadata']['name']) for o in releases}
    actual = {h for h in checks if h[1] == 'HelmRelease'}
    if expected != actual:
        raise SystemExit(f'Helm readiness coverage differs in {run}: missing={expected-actual}, unknown={actual-expected}')
    namespaces = {o['metadata']['name'] for o in objects if o['kind'] == 'Namespace'} | {'kube-system', 'flux-system'}
    for o in objects:
        ns = o['metadata'].get('namespace')
        if ns and ns not in namespaces:
            raise SystemExit(f'Missing selected namespace {ns} in {run}')
        if o['apiVersion'] == 'postgresql.cnpg.io/v1' and o['kind'] == 'Cluster':
            ident = (o['apiVersion'], o['kind'], ns, o['metadata']['name'])
            if ident not in checks:
                raise SystemExit(f'Missing database readiness gate: {ident}')
    for o in releases:
        s = o['spec']; ref = s.get('chartRef') or s['chart']['spec']['sourceRef']
        ns = ref.get('namespace', o['metadata']['namespace'])
        if not any(x[1:] == (ref['kind'], ns, ref['name']) for x in identities):
            raise SystemExit(f'Missing selected chart source {ref} in {run}')
    print(f'Validated {run.name}: own Flux path, {len(resources)} child definitions, {len(releases)} releases, prerequisites and DAG')
print(f'Validated {len(runs)} run folder(s) and shared templates')
