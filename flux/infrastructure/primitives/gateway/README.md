# Gateway primitives

The base creates only Gateway `application-gateway`, using GatewayClass `cilium`
and a same-namespace HTTP listener on port 80. Supply an existing, Accepted
GatewayClass backed by your controller or patch `spec.gatewayClassName`.
Creating Gateway API objects does not install a controller or ensure it supports
every route/protocol. In particular, the default class is not a claim that Cilium
supports every optional L4 route below. Select a controller with the required
conformance/features before enabling a route.

## Select routes

Each directory under `opt-in/` is a Kustomize Component. It adds a route targeting
Service `application` in the same namespace. All except HTTPRoute also append
the matching listener to the Gateway. No backend Service or workload is created.

| Component | API version | Listener | Backend Service port | Prerequisite |
| --- | --- | --- | --- | --- |
| `httproute` | v1 | HTTP 80 (`http`) | 80 | Standard CRDs |
| `grpcroute` | v1 | HTTP 50051 (`grpc`) | 50051 | Standard CRDs; controller gRPC support |
| `tlsroute` | v1alpha3 | TLS 443 passthrough (`tls`) | 8443 | Experimental CRDs; TLSRoute support |
| `tcproute` | v1alpha2 | TCP 5432 (`tcp`) | 5432 | Experimental CRDs; TCPRoute support |
| `udproute` | v1alpha2 | UDP 5353 (`udp`) | 5353 | Experimental CRDs; UDPRoute support |

HTTP and TLS examples use hostname `app.example.com`; patch it and configure DNS.
The gRPC example matches all gRPC requests on its dedicated listener. Its backend
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
`infrastructure/networking/gateway-api-crds/opt-in/experimental-routes`.
That opt-in adds only TLSRoute/TCPRoute/UDPRoute CRDs; it does not redeclare the
standard CRDs. Wait for CRDs to be Established before applying route objects.
The Gateway and controller must be ready before route acceptance is expected.
This base creates no ReferenceGrant, DNS entry or credential; references stay
within one namespace. Keep listeners restricted to that namespace unless an
explicit multi-namespace policy is needed.

## Verification

Build/composition and upstream v1.4.0 CRD schema checks cover all five route
types, their listener attachments and prefixed parent/backend references.
No controller/data-plane verification has been performed for these primitives.
In a consuming cluster, check Gateway `Accepted`/`Programmed` and listener status,
then each route's parent `Accepted`/`ResolvedRefs`, followed by actual HTTP,
gRPC, TLS, TCP or UDP traffic to its backend. Schema acceptance alone does not
prove routing. Account for load balancer/listener exposure costs when selecting
extra protocols.
