#!/usr/bin/env python3
"""Seed central PKI from the lab's existing CA without printing private material.
Run BEFORE installing the central root Certificate on an existing playground.
Fresh bootstraps skip this step and let cert-manager generate the root.
"""
import json
import subprocess


def get(namespace, name):
    result = subprocess.run(['kubectl', '--request-timeout=10s', '-n', namespace,
                             'get', 'secret', name, '--ignore-not-found', '-o', 'json'],
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout) if result.stdout.strip() else None

if get('certificates', 'platform-root-ca'):
    print('Central CA already exists; leaving it unchanged')
else:
    source = get('secrets', 'openbao-injector-ca')
    if source is None:
        raise SystemExit('No existing OpenBao CA. Fresh bootstrap: let cert-manager create the root.')
    data = source['data']
    assert 'tls.crt' in data and 'tls.key' in data
    target = {'apiVersion': 'v1', 'kind': 'Secret',
              'metadata': {'name': 'platform-root-ca', 'namespace': 'certificates'},
              'type': 'kubernetes.io/tls', 'data': data}
    subprocess.run(['kubectl', '--request-timeout=10s', 'create', '-f', '-'],
                   input=json.dumps(target), text=True, check=True, stdout=subprocess.DEVNULL)
    print('Existing CA adopted into certificates/platform-root-ca; private values omitted')
