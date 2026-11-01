#!/usr/bin/env python3
"""Initialize one fresh lab Raft cluster and unseal its three replicas.

Keeps five shares and the root token together in an owner-only lab file.
Production custody must use a separate approved process. No credentials printed.
"""
import json
import os
from pathlib import Path
import subprocess
import time

os.umask(0o077)
folder = Path(os.environ.get("OPENBAO_BOOTSTRAP_DIR", Path.home() / ".config/codex-platform"))
folder.mkdir(parents=True, exist_ok=True, mode=0o700)
folder.chmod(0o700)
output = folder / "openbao-init.json"

def bao(pod, *args):
    return subprocess.run(["kubectl", "-n", "secrets", "exec", pod, "--", "bao", *args],
                          capture_output=True, text=True, timeout=20)

for index in range(3):
    pod = f"openbao-{index}"
    for attempt in range(300):
        try:
            status = json.loads(bao(pod, "status", "-format=json").stdout)
        except (ValueError, subprocess.TimeoutExpired):
            time.sleep(2)
            continue
        if index == 0 and not status["initialized"]:
            # Reserve the destination before changing server state. Refuse to
            # overwrite old material or initialize a new cluster with old keys.
            with output.open("x") as stream:
                result = bao(pod, "operator", "init", "-key-shares=5", "-key-threshold=3", "-format=json")
                if result.returncode:
                    raise SystemExit("Initialization failed; inspect the server. Do not blindly rerun init.")
                material = json.loads(result.stdout)
                json.dump(material, stream)
                stream.flush()
                os.fsync(stream.fileno())
            output.chmod(0o600)
        if not output.exists():
            raise SystemExit("Server already initialized but original recovery material is missing; stop and recover it.")
        if output.stat().st_mode & 0o077:
            raise SystemExit("Initialization file permissions must be 0600; refusing to read it.")
        material = json.loads(output.read_text())
        if status.get("sealed", True):
            for key in material["unseal_keys_b64"][:3]:
                bao(pod, "operator", "unseal", key)
            try:
                status = json.loads(bao(pod, "status", "-format=json").stdout)
            except ValueError:
                time.sleep(2)
                continue
        if status.get("initialized") and not status.get("sealed"):
            print(f"{pod}: initialized and unsealed", flush=True)
            break
        time.sleep(2)
    else:
        raise SystemExit(f"{pod}: did not become unsealed; inspect retry-join, TLS, and PVCs")
print(f"Recovery material retained at {output} (0600); values omitted")
