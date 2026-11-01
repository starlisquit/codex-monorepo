#!/usr/bin/env python3
"""Configure an explicitly scoped External Secrets backend without printing credentials."""
import argparse
import re
import base64
import json
import os
from pathlib import Path
import ssl
import subprocess
import time
import urllib.request

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--namespace',default='secrets')
parser.add_argument('--pod',default='openbao-0')
parser.add_argument('--tls-secret',default='openbao-server-tls')
parser.add_argument('--role',required=True)
parser.add_argument('--secret-prefix',required=True)
parser.add_argument('--verification-path',help='Optional scoped test value to create; no verification secret is written by default')
parser.add_argument('--auth-mount',default='kubernetes')
parser.add_argument('--kv-mount',default='kv')
parser.add_argument('--service-account',default='external-secrets-openbao')
parser.add_argument('--audience',default='openbao')
args=parser.parse_args()
for value in [args.role,args.secret_prefix,args.auth_mount,args.kv_mount]:
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_/-]*',value):parser.error('Invalid role or path')
if args.verification_path and not args.verification_path.startswith(args.secret_prefix.rstrip('/')+'/'):parser.error('Verification path must be inside the explicitly allowed prefix')
os.umask(0o077)
folder = Path(os.environ.get("OPENBAO_BOOTSTRAP_DIR", Path.home() / ".config/codex-platform"))
key_file = folder / "openbao-init.json"
if key_file.stat().st_mode & 0o077:
    raise SystemExit("Initialization material must have mode 0600")
material = json.loads(key_file.read_text())
ca = subprocess.check_output(["kubectl", "-n", args.namespace, "get", "secret", args.tls_secret,
                              "-o", "jsonpath={.data.ca\\.crt}"], text=True)
ca_file = folder / "openbao-ca.crt"
ca_file.write_bytes(base64.b64decode(ca))
context = ssl.create_default_context(cafile=str(ca_file))
log = (folder / "port-forward.log").open("w")
forward = subprocess.Popen(["kubectl", "-n", args.namespace, "port-forward", "pod/"+args.pod, "18200:8200"],
                           stdin=subprocess.DEVNULL, stdout=log, stderr=log)

def call(path, data=None):
    body = None if data is None else json.dumps(data).encode()
    request = urllib.request.Request("https://127.0.0.1:18200/v1/" + path, data=body,
                                    headers={"X-Vault-Token": material["root_token"],
                                             "Content-Type": "application/json"})
    # Bypass environment HTTP proxies for this deliberately local forward only.
    client = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                         urllib.request.HTTPSHandler(context=context))
    with client.open(request, timeout=10) as response:
        content = response.read()
        return json.loads(content) if content else None

try:
    for attempt in range(30):
        try:
            call("sys/health")
            break
        except Exception:
            if forward.poll() is not None:
                raise SystemExit("Port forward exited; inspect its local log")
            time.sleep(1)
    else:
        raise SystemExit("OpenBao did not become reachable over the verified local TLS forward")
    if args.kv_mount+'/' not in call("sys/mounts")["data"]:
        call("sys/mounts/"+args.kv_mount, {"type": "kv", "options": {"version": "2"}})
    if args.auth_mount+'/' not in call("sys/auth")["data"]:
        call("sys/auth/"+args.auth_mount, {"type": "kubernetes"})
    call("auth/"+args.auth_mount+"/config", {"kubernetes_host": "https://kubernetes.default.svc:443"})
    prefix=args.secret_prefix.rstrip('/')
    policy=f'path "{args.kv_mount}/data/{prefix}/*" {{ capabilities = ["read"] }}\npath "{args.kv_mount}/metadata/{prefix}/*" {{ capabilities = ["read", "list"] }}'
    call("sys/policies/acl/"+args.role, {"policy":policy})
    call("auth/"+args.auth_mount+"/role/"+args.role, {
        "bound_service_account_names": [args.service_account],
        "bound_service_account_namespaces": [args.namespace], "audience": args.audience,
        "token_policies": [args.role], "token_ttl": "1h"})
    if args.verification_path:
        call(args.kv_mount+"/data/"+args.verification_path, {"data": {"status": "openbao-external-secrets-ok"}})
    print("KV v2, scoped Kubernetes authentication, and verification value configured; credentials omitted")
finally:
    forward.terminate()
    forward.wait(timeout=10)
    log.close()
