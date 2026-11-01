# deployment-eso validation run

Playground `6ae7a3507f32053bde2bc71a`. Flux reconciles only `./flux/clusters/20261101-233840-deployment-eso-2bc71a`.
Add only the workloads and readiness gates needed for this run. Keep credentials
outside Git. Record findings, push both remotes, then destroy the playground.
Never reuse this folder for a new playground.

## Runtime fixtures

Only cert-manager, central PKI/trust, one persistent OpenBao Raft replica, the
relevant delivery controller and two Python application fixtures are selected.
Monitoring integrations are disabled in run-owned values, not in shared defaults.
OpenBao uses a 1Gi local-path volume; its one-share/one-threshold lab recovery
material remains in a mode0600 VM-local file. This is not production recovery
custody or HA validation. No external provider credentials are required.

The fixture HTTP endpoint returns SHA-256 fingerprints, never credential values.
`probes/backend.py` initializes/unseals the fresh lab, configures scoped roles and
policies, and writes randomized KV values without printing them.
`probes/verify.py` exercises actual application consumption, auth denials and
refresh/failure recovery. `probes/capture.py` records sanitized runtime metadata.

After bootstrapping this exact run path, use separate detached processes on
`dev-machine` (as laborant) and inspect only their sanitized logs/evidence:

```sh
python3 probes/backend.py eso /home/laborant/repo
python3 probes/verify.py eso
python3 probes/capture.py
```

Run these from the `probes` directory (or copy all three scripts together). The
verifier waits for backend and Pod readiness. It creates temporary negative-test
fixtures; it never emits actual provider values, service-account JWTs, OpenBao
client tokens, root tokens or recovery shares. Provisioning is for a **fresh lab**
only; it is not an idempotent production credential-rotation workflow.
