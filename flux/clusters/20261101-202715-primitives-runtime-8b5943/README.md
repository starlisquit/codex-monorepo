# primitives-runtime validation run

Playground `6ae7767346471e13268b5943`. Flux reconciles only `./flux/clusters/20261101-202715-primitives-runtime-8b5943`.
Add only the workloads and readiness gates needed for this run. Keep credentials
outside Git. Record findings, push both remotes, then destroy the playground.
Never reuse this folder for a new playground.

This K3s version preinstalls Gateway API v1.6.1 CRDs (including L4 routes).
Do not select the repository's older v1.4.0 CRD bases in this run: Kubernetes
rejects removing their already-stored v1 API versions. The workload primitives
use their declared served API versions against the existing newer CRDs.
Envoy Gateway v1.9.3 is a run-only test controller, using internal ClusterIP.
Before bootstrap, create temporary Secret demo/protocol-fixture-tls with a
certificate for app.example.com; private key material must stay outside Git.

## Retired run

This run was cancelled on user direction before completing runtime verification.
Envoy Gateway had installed, but the user requested testing with the repository's
Cilium Gateway API integration instead. Reconciliation was suspended immediately;
configuration/history is preserved as evidence, not an active deployment target.
The old v1.4.0 L4 CRDs initially failed because K3s already stored those APIs as
v1. The final K3s state is not a successful primitive runtime verification.
The ServiceAccount token probe never prints credentials; its results were not
collected in this cancelled run.
