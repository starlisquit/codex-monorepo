# Gateway primitives

The base creates only Gateway `application-gateway`, using GatewayClass `cilium`
and a same-namespace HTTP listener on port 80. Supply an existing, Accepted
GatewayClass backed by your controller or patch `spec.gatewayClassName`.
Creating Gateway API objects does not install a controller or ensure it supports
every route/protocol. Cilium 1.20.4 has been runtime-verified for all five route types in
LoadBalancer mode. Its host-network mode rejects TCPRoute and UDPRoute. Select
a compatible controller and exposure mode before enabling a route.

## Select routes

Each directory under `opt-in/` is a Kustomize Component. It adds a route targeting
Service `application` in the same namespace. All except HTTPRoute also append
the matching listener to the Gateway. No backend Service or workload is created.

| Component | API version | Listener | Backend Service port | Prerequisite |
| --- | --- | --- | --- | --- |
| `httproute` | v1 | HTTP 80 (`http`) | 80 | Standard CRDs |
| `grpcroute` | v1 | HTTP 50051 (`grpc`) | 50051 | Standard CRDs; controller gRPC support |
| `tlsroute` | v1 | TLS 443 passthrough (`tls`) | 8443 | L4 CRDs; TLSRoute support |
| `tcproute` | v1 | TCP 5432 (`tcp`) | 5432 | L4 CRDs; TCPRoute support |
| `udproute` | v1 | UDP 5353 (`udp`) | 5353 | L4 CRDs; UDPRoute support |

HTTP and TLS examples use hostname `app.example.com`; gRPC uses
`grpc.example.com`. Patch these and configure DNS/client authority. Explicit
gRPC host matching avoids a wildcard gRPC route catching unmatched HTTP hosts
when a controller shares an HTTP routing configuration across listeners. Its backend
must serve HTTP/2; set Service `appProtocol: kubernetes.io/h2c` for cleartext
backends where required by the controller. HTTP/gRPC
listeners use cleartext; configure HTTPS listeners and certificate references for
TLS termination. TLSRoute passes encrypted traffic through; the backend owns the
certificate and must serve TLS. Do not add a Gateway certificate to that
passthrough listener. TCP and UDP routes match their dedicated listeners.

For a wrapper at `flux/clusters/<run>/gateway/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: demo
namePrefix: api-
resources:
- ../../../infrastructure/primitives/gateway
components:
- ../../../infrastructure/primitives/gateway/opt-in/httproute
# Select other route components only when required and supported.
```

This produces `api-application-gateway` and `api-application-http`. The provided
Kustomize name-reference configuration keeps route parentRefs consistent with
prefixes/suffixes, and transforms backendRefs when the backend Service is
included in the same build. References to external Services keep their original
names; patch backendRefs if the backend was renamed in a separate build.

Select namespace and `infrastructure/networking/gateway-api-crds` separately.
For the L4 routes, additionally select
`infrastructure/networking/gateway-api-crds/opt-in/l4-routes`.
The L4 routes use stable v1 APIs from Gateway API v1.6.3. This replaces the
older alpha API templates. That opt-in adds only TLSRoute/TCPRoute/UDPRoute
CRDs; it does not redeclare the
standard CRDs. Wait for CRDs to be Established before applying route objects.
The Gateway and controller must be ready before route acceptance is expected.
This base creates no ReferenceGrant, DNS entry or credential; references stay
within one namespace. Keep listeners restricted to that namespace unless an
explicit multi-namespace policy is needed.

## Verification

Build/composition and upstream v1.6.3 CRD schema checks cover all five route
types, their listener attachments and prefixed parent/backend references.
Cilium 1.20.4 runtime traffic checks passed for HTTP, gRPC, TLS passthrough, TCP
and UDP, including unmatched HTTP Host/TLS SNI rejection. Cilium may report the
Gateway Programmed even with rejected listeners: check every listener and route.
When changing Cilium exposure modes, restart agents/operator and remove stale
Service node-selection annotations as described in the runtime findings.
In a consuming cluster, check Gateway `Accepted`/`Programmed` and listener status,
then each route's parent `Accepted`/`ResolvedRefs`, followed by actual HTTP,
gRPC, TLS, TCP or UDP traffic to its backend. Schema acceptance alone does not
prove routing. Account for load balancer/listener exposure costs when selecting
extra protocols.

See [native Gateway API runtime findings](../../../docs/findings/primitives-cilium-2026-11-01.md)
for the exact versions, fixture changes, assertions and limits.
