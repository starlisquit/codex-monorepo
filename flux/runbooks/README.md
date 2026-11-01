# Platform runbooks

Run commands from the repository root unless a section explicitly names another
machine. The manifests here target `starlisquit/codex-monorepo`, branch `main`,
and the `iximiuz-platform` overlay. For another repository, namespace layout,
API address, or cluster domain, edit the corresponding references before applying.

## Bootstrap sequence

1. [Provision and prepare the playground](bootstrap/01-provision-playground.md)
2. [Install Cilium and bootstrap Flux](bootstrap/02-cilium-and-flux.md)
3. [Follow dependency gates and verify Ceph](bootstrap/03-platform-and-storage.md)
4. [Initialize OpenBao and connect External Secrets](bootstrap/04-openbao-and-external-secrets.md)
5. [Verify applications and telemetry](operations/verify-platform.md)

## Operations and recovery

- [Configure Velero and test backup/restore](operations/velero.md)

- [Enable and verify security tools](operations/security-tools.md)

- [Central PKI configuration, migration limits, and Vault/OpenBao integration](operations/pki.md)

- [Container log collection and dashboard verification](operations/container-logging.md)

- [Ingress NetworkPolicy templates and enforcement test](../policies/network/README.md)
- [Reconcile and troubleshoot Flux](operations/reconciliation.md)
- [Control-plane/API incident handling](recovery/control-plane.md)
- [OpenBao unseal and data recovery boundaries](recovery/openbao.md)

## Helper scripts

`scripts/bootstrap-cilium.sh` installs a minimal networking seed with Gateway API
and ServiceMonitors deferred until their CRDs exist. `scripts/bootstrap-flux.sh`
applies the committed Flux installation and Git source. Neither creates a new
repository or pushes bootstrap commits.

The Python OpenBao helpers need only the standard library and kubectl. Their
checked-in initialization and configuration helpers were exercised on the fresh
2026-11-01 rebuild, including file-permission and initialization safeguards.
They retain all recovery material together for this lab. Use a separate process
for production key custody. `configure-openbao.py` changes only the documented
lab mount/auth policy/role and verification value; do not reuse those names for
unrelated preexisting policy definitions.

Validation needs Python 3 with PyYAML and Kustomize:

```sh
python3 -m venv /tmp/flux-validation-venv
. /tmp/flux-validation-venv/bin/activate
python3 -m pip install PyYAML
flux/runbooks/scripts/validate.sh
```

On Ubuntu, install `python3-venv` first if venv support is missing.

To use a non-PATH Kustomize binary, set `KUSTOMIZE_BIN=/path/to/kustomize` for that
command. Also render modified charts using the same Helm major version as the
live helm-controller; a Helm 3 render did not detect the Helm 4 Collector failure.

If using an MCP command tool with a sub-minute timeout, run long jobs detached,
redirect stdin/stdout/stderr, then poll the log. The normal interactive shell
commands below may legitimately take minutes.
