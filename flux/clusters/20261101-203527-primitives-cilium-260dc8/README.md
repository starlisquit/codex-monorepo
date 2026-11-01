# primitives-cilium validation run

Playground `6ae7785f7f32053bde260dc8`. Flux reconciles only `./flux/clusters/20261101-203527-primitives-cilium-260dc8`.
Add only the workloads and readiness gates needed for this run. Keep credentials
outside Git. Record findings, push both remotes, then destroy the playground.
Never reuse this folder for a new playground.

## Bootstrap prerequisites

This kubeadm playground was started with its Flannel init task disabled. The
one-time CNI bootstrap is necessary before ordinary Flux Pods can run:

1. Clone this repository and apply the core Gateway API and `opt-in/l4-routes`
   CRDs with `kubectl apply --server-side -k`.
2. Label `node-01` with `gateway-validation=true`; remove the kube-proxy DaemonSet
   because Cilium is configured for kube-proxy replacement.
3. Create temporary TLS Secret `demo/protocol-fixture-tls` for `app.example.com`
   outside Git. A one-day self-signed certificate is sufficient for this fixture;
   the client verifies it explicitly, without disabling certificate validation.
4. `helm upgrade --install cilium cilium/cilium --version 1.20.4 -n kube-system
   -f <this-run>/cilium/bootstrap-values.yaml --wait --timeout 8m`.
5. Run `runbooks/scripts/bootstrap-flux.sh` with this exact run folder. Flux then
   owns reconciliation of the same Cilium release and selects only these tests.

The bootstrap-values file is the effective shared values plus the focused run's
overrides. Hubble, encryption and monitoring are disabled for this test. No
separate Envoy Gateway controller is installed. Cilium exposes native Gateway
API listeners directly on labeled node-01 (172.16.0.3), using high ports 18080
(HTTP), 15051 (gRPC), 18443 (TLS), 15432 (TCP), 15353 (UDP). The backend Service
uses the ports from the shared route templates. There is no external load balancer.

`verify-rbac.py` uses actual short-lived ServiceAccount tokens in memory; it never
prints or saves them. `verify-cronjob.py` records scheduler completion and Forbid
skip events; runtime TLS keys remain only in the disposable playground.
