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
2. Remove the kube-proxy DaemonSet
   because Cilium is configured for kube-proxy replacement.
3. Create temporary TLS Secret `demo/protocol-fixture-tls` for `app.example.com`
   outside Git. A one-day self-signed certificate is sufficient for this fixture;
   the client verifies it explicitly, without disabling certificate validation.
4. `helm upgrade --install cilium cilium/cilium --version 1.20.4 -n kube-system
   -f <this-run>/cilium/bootstrap-values.yaml --wait --timeout 8m`.
5. Run `docs/runbooks/scripts/bootstrap-flux.sh` with this exact run folder. Flux then
   owns reconciliation of the same Cilium release and selects only these tests.

The bootstrap-values file is the effective shared values plus the focused run's
overrides. Hubble, encryption and monitoring are disabled for this test. No
separate Envoy Gateway controller is installed. Cilium uses LoadBalancer mode and
an eight-address lab-only IP pool (172.16.0.200–207). The assigned Gateway address
was 172.16.0.200; its ports are 18080 (HTTP), 15051 (gRPC), 18443 (TLS), 15432
(TCP), 15353 (UDP). The backend Service uses the shared route template ports.
Traffic tests run from the backend Pod through this VIP; external L2/BGP
advertisement was not configured or tested. No cloud load balancer is allocated.

The initial host-network attempt passed HTTP/gRPC/TLS but explicitly rejected
TCP/UDP as unsupported. After changing host-network mode, restarting the Cilium
operator and agents was required to pick up their startup configuration. The
generated Service retained the old `service.cilium.io/node-selector` annotation;
it was explicitly removed so traffic also worked from a newly scheduled Pod on
another node. Fresh bootstrap
uses LoadBalancer mode from the outset. Gateway readiness now checks every
listener and every route, not just the Gateway-level Programmed condition.

`verify-rbac.py` uses actual short-lived ServiceAccount tokens in memory; it never
prints or saves them. `verify-cronjob.py` records scheduler completion and Forbid
skip events; runtime TLS keys remain only in the disposable playground.

## Completed

All five protocols, 21 RBAC checks, CronJob execution/concurrency and Deployment
security checks passed. See [findings](../../docs/findings/primitives-cilium-2026-11-01.md).
Findings were pushed to both remotes before the playground was destroyed at
20:54:06 Europe/Istanbul on 2026-11-01. This folder is retained evidence; do not
reuse it for a new playground.
