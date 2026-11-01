# Primitive runtime verification with native Gateway API — 2026-11-01

Verified the CronJob, RBAC and Gateway primitives in a fresh kubeadm playground,
with the repository's Cilium integration handling the standard Kubernetes Gateway
API resources. All five route protocols passed actual traffic checks. No separate
Envoy Gateway controller was installed in this kubeadm run.

## Run and versions

- Playground: `k8s-omni`, ID `6ae7785f7f32053bde260dc8`.
- Exact Flux path: `./flux/clusters/20261101-203527-primitives-cilium-260dc8`.
- Tested configuration revision: `aee8dc6737e7b4fa08f5c47304ccfbe013b71ed9`.
- Evidence captured at 20:51:42 Europe/Istanbul (17:51:42 UTC).
- API server `v1.37.2`; kubelets `v1.37.1`; Flux `v2.10.0`;
  official Cilium chart/application `1.20.4`; Gateway API Standard `v1.6.3`.
- Only Cilium networking/Gateway support, Flux, demo backends, CronJobs and RBAC
  were selected. Hubble, monitoring and encryption were disabled for this run.
- The playground's Flannel init task was disabled. Cilium was bootstrapped before
  Flux Pods could run, then Flux adopted/reconciled that same release. kube-proxy
  was removed because the template enables kube-proxy replacement.

[Runtime evidence](evidence/primitives-cilium-2026-11-01.json) and
[CronJob scheduling observations](evidence/primitives-cronjob-2026-11-01.json)
contain sanitized status/results, without tokens or TLS private keys.

## Gateway results

Cilium GatewayClass `cilium` was Accepted. Gateway, all five listeners and all
five routes reported current-generation acceptance and resolved references;
Gateway and listeners were Programmed. Flux readiness explicitly checks every
listener and route, including their observed generations.

Traffic ran from the managed backend Pod through the Cilium-managed LoadBalancer
VIP `172.16.0.200`, not directly to its backend Service. The final backend Pod was
on node-02, after a Deployment rollout from the earlier placement.

| Route | Gateway port | Backend Service port | Actual result |
| --- | --- | --- | --- |
| HTTPRoute | 18080 | 80 | HTTP 200, `http:primitive-runtime-ok` |
| GRPCRoute | 15051 | 50051 | Real gRPC Health Check returned `SERVING`, authority `grpc.example.com` |
| TLSRoute | 18443 | 8443 | TLS 1.3 passthrough, `tls:primitive-runtime-ok`; certificate chain and hostname verified |
| TCPRoute | 15432 | 5432 | Stream echo returned `tcp:primitive-runtime-ok` |
| UDPRoute | 15353 | 5353 | Datagram echo returned `udp:primitive-runtime-ok` |

An unmatched HTTP Host returned 404. An unmatched TLS SNI was reset before a
backend TLS session could be established. The positive TLS check used a one-day
self-signed fixture certificate trusted explicitly by the client; it did not
disable certificate or hostname validation. Keys stayed outside Git.

Cilium IPAM allocated the private VIP from a run-only eight-address pool. The
traffic checks originate inside the cluster; external L2/BGP advertisement,
public access and cloud load balancing were not configured or verified.

## CronJob results

- Created a manual Job from the unmodified starter CronJob's jobTemplate. It
  completed successfully and printed its timestamp and expected starter message.
- A second wrapper ran every minute with a 75-second task, retaining the shared
  `Forbid` concurrency policy and other bounded execution defaults.
- Observed a scheduler-created successful Job, `JobAlreadyActive` event explicitly
  stating that `Forbid` blocked an overlapping start, and a maximum observed
  active count of one. A later scheduled execution started after completion.
- The daily 03:00 Europe/Istanbul schedule remains the template default. Its
  exact wall-clock trigger was not awaited; the minute schedule tested the real
  controller, while the manual Job tested the original task command.

## RBAC and Deployment results

All **21 real API authorization checks** passed with actual short-lived
ServiceAccount tokens held only in memory:

- Baseline ServiceAccount: Pod get/list/watch and cross-namespace reads denied.
- RoleBinding + pod-reader ClusterRole: Pod get/list/watch allowed in `demo`,
  denied in `proxy` and for an all-namespace list.
- ClusterRoleBinding + pod-reader ClusterRole: Pod reads allowed across namespaces.
- All three identities: Secret reads and Pod creation denied (HTTP 403). Creation
  probes used server-side dry run and did not create resources.

The protocol backend also consumes the shared Deployment primitive, with one
replica and a Python protocol fixture replacing the starter image/command.
It became Ready and rolled to a new Pod successfully. Runtime checks confirmed
UID/GID 10001, no mounted Kubernetes API token, and a root-filesystem write rejected
with EROFS (errno 30). The default HTTP echo image itself was not exercised.

## Findings and fixes

1. **CRD/API versions:** the original v1.4.0 alpha route definitions could not be
   applied over a K3s installation already storing those kinds as v1. Cilium
   1.20.4 documentation expects Gateway API v1.6.3. Updated the core CRD bundle
   and L4 route opt-in to that upstream version, and all route primitives to
   stable v1. Renamed `opt-in/experimental-routes` to `opt-in/l4-routes` because
   these definitions are now Standard-channel APIs. Do not downgrade stored API
   versions or install competing CRD owners.
2. **Host-network limitation:** Cilium rejected TCP/UDP listeners and routes in
   host-network mode, even while the overall Gateway was Programmed. Switched
   to Cilium's LoadBalancer mode and added per-listener/per-route Flux gates.
3. **Mode-switch rollout:** changing the ConfigMap alone did not reload startup
   settings. Restarted Cilium operator and agents, and removed the generated
   Service's stale `service.cilium.io/node-selector` annotation. This resolved
   traffic failure after the backend moved to another node. Fresh bootstrap
   values use LoadBalancer mode without the old node restriction.
4. **Wildcard gRPC routing:** Cilium's shared HTTP routing configuration allowed
   the wildcard gRPC route to catch an unmatched HTTP host. Scoped the shared
   GRPCRoute to `grpc.example.com` and supplied that authority in the client.
   Positive HTTP/gRPC checks and unmatched-host rejection then passed together.

A preliminary K3s run (`6ae7767346471e13268b5943`) was cancelled when the user
specified the repository's native Gateway API/Cilium setup. Its state/configuration
was published before destruction at 20:34:44 Europe/Istanbul. It is not counted
as successful runtime verification; its retained run metadata records cancellation.

## Repository validation and scope

All **165 Kustomize builds** and the existing run/DAG/source/namespace checks
passed. Gateway and route objects also passed the official v1.6.3 CRD schemas.
Every selected Flux child reconciled to the tested revision, including the
HelmRelease and strict Gateway readiness gates.

These checks cover the reported lab traffic and permissions, not performance,
HA, disruption budgets, external advertisement, public TLS provisioning or every
controller implementation. Existing static-only reports describe earlier versions;
this report records the current runtime scope and supersedes their unverified
runtime status for the primitives tested here. Autoscaling remains with KEDA.

## Teardown

Publish these findings and configuration to both remotes before destruction.
Confirmed destruction will be recorded after the API returns success.
