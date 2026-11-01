#!/usr/bin/env python3
"""Configure this lab's scoped External Secrets backend without printing credentials."""
import base64
import json
import os
from pathlib import Path
import ssl
import subprocess
import time
import urllib.request

os.umask(0o077)
folder = Path(os.environ.get("OPENBAO_BOOTSTRAP_DIR", Path.home() / ".config/codex-platform"))
key_file = folder / "openbao-init.json"
if key_file.stat().st_mode & 0o077:
    raise SystemExit("Initialization material must have mode 0600")
material = json.loads(key_file.read_text())
ca = subprocess.check_output(["kubectl", "-n", "secrets", "get", "secret", "openbao-server-tls",
                              "-o", "jsonpath={.data.ca\\.crt}"], text=True)
ca_file = folder / "openbao-ca.crt"
ca_file.write_bytes(base64.b64decode(ca))
context = ssl.create_default_context(cafile=str(ca_file))
log = (folder / "port-forward.log").open("w")
forward = subprocess.Popen(["kubectl", "-n", "secrets", "port-forward", "pod/openbao-0", "18200:8200"],
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
    if "kv/" not in call("sys/mounts")["data"]:
        call("sys/mounts/kv", {"type": "kv", "options": {"version": "2"}})
    if "kubernetes/" not in call("sys/auth")["data"]:
        call("sys/auth/kubernetes", {"type": "kubernetes"})
    call("auth/kubernetes/config", {"kubernetes_host": "https://kubernetes.default.svc:443"})
    call("sys/policies/acl/external-secrets-lab", {"policy":
         'path "kv/data/lab/*" { capabilities = ["read"] }\n'
         'path "kv/metadata/lab/*" { capabilities = ["read", "list"] }'})
    call("auth/kubernetes/role/external-secrets-lab", {
        "bound_service_account_names": ["external-secrets-openbao"],
        "bound_service_account_namespaces": ["secrets"], "audience": "openbao",
        "token_policies": ["external-secrets-lab"], "token_ttl": "1h"})
    call("kv/data/lab/verification", {"data": {"status": "openbao-external-secrets-ok"}})
    print("KV v2, scoped Kubernetes authentication, and verification value configured; credentials omitted")
finally:
    forward.terminate()
    forward.wait(timeout=10)
    log.close()
