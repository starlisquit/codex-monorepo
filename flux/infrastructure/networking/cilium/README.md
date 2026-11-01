# Cilium networking, service mesh, and gRPC

The pinned `1.20.4` chart enables kube-proxy replacement, Hubble/Relay/UI, metrics
collection, and the sidecarless Layer 7 service-mesh building blocks:

- `l7Proxy: true`: Layer 7 proxy/policy support.
- `envoy.enabled: true`: a Cilium-managed Envoy DaemonSet.
- `envoyConfig.enabled: true`: CiliumEnvoyConfig processing.
- `loadBalancer.l7.backend: envoy`: opt-in L7 load balancing for Services.
- `gatewayAPI.enabled: true`: Gateway API controller.
- `gatewayAPI.enableAlpn: true`: negotiate HTTP/2 on TLS Gateway listeners.
- `gatewayAPI.enableAppProtocol: true`: select backend protocols from Services.

There is no single `serviceMesh.enabled` chart switch. These settings enable the
platform capabilities; they do not automatically proxy all workload traffic or
create workload routes/policies. Cilium's annotation-based L7 service load
balancing is labeled beta in the pinned version's documentation.

## Workload configuration

Each consuming cluster chooses its Gateways, HTTPRoutes/GRPCRoutes, certificates,
Service annotations, and L7 policies. No example policies are installed here.
For opt-in L7 service load balancing, Cilium supports the Service annotation
`service.cilium.io/lb-l7: enabled`. No automatic port redirection list is set.
Use the pinned version's gRPC guidance when configuring backend protocol handling.

Install the Gateway API CRDs required by your routes before enabling its
controller. A plaintext HTTP/2 backend can advertise its Service port as
`appProtocol: kubernetes.io/h2c`; configure TLS listeners and certificate Secrets
for TLS-terminating Gateways. ALPN alone does not create a TLS listener or issue a
certificate. Supply the real `k8sServiceHost`/`k8sServicePort` before installation.

This configuration does not turn on transparent encryption or automatic mesh mTLS.
Cilium's older mutual-authentication feature is deprecated in 1.20 and scheduled
for removal in 1.21; it is not enabled as part of these L7 settings. Choose traffic
encryption and workload identity separately if required.

## gRPC metrics

There is no standalone `grpc` Hubble metrics plugin in Cilium 1.20.4. gRPC uses
HTTP/2, so the existing `httpV2` plugin can record its HTTP request/response
observations when the traffic is visible through Cilium's L7 proxy. This requires
an appropriate proxy path, such as a configured Gateway, L7 policy, or opt-in
service load balancing. Merely enabling Hubble does not redirect all traffic.

The HTTP metrics report HTTP status, method, protocol, and reporter. They do not
provide a dedicated `grpc-status` label or per-message streaming RPC metrics;
HTTP status 200 can still represent a failed gRPC call. Use application or
OpenTelemetry instrumentation for gRPC-specific success/error codes and RPC
semantics. End-to-end TLS passthrough hides HTTP/gRPC details from Hubble unless
TLS is terminated at an inspection point.

## Validation

Helm rendering verifies the Envoy DaemonSet and the resulting Cilium configuration
flags, while Kustomize builds verify the Flux resources. A test-only API address
is used for rendering. Live gRPC routing, HTTP/2 negotiation, and metric generation
still require a running cluster and a configured workload.

References (pinned version):

- [Chart values](https://github.com/cilium/cilium/blob/v1.20.4/install/kubernetes/cilium/values.yaml)
- [Service load balancing](https://github.com/cilium/cilium/blob/v1.20.4/Documentation/network/servicemesh/envoy-load-balancing.rst)
- [gRPC Gateway example](https://github.com/cilium/cilium/blob/v1.20.4/Documentation/network/servicemesh/gateway-api/grpc.rst)
- [HTTP metrics implementation](https://github.com/cilium/cilium/blob/v1.20.4/pkg/hubble/metrics/http/handler.go)
