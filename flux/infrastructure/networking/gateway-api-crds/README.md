# Gateway API CRDs

Vendored upstream Gateway API Standard channel v1.4.0 definitions, moved intact
from the cluster overlay. Select this directory once per cluster and wait for
the CRDs to be Established before enabling Cilium's Gateway API support. The
existing `gateway-api` Flux Kustomization retains that readiness gate. Review
compatibility and upstream schema changes when upgrading; this refactor does
not change CRD versions, definitions or copyright notices.

For TLSRoute, TCPRoute and UDPRoute select the independent
[`opt-in/experimental-routes`](opt-in/experimental-routes) base as well. These
CRDs are not included by the standard base and require compatible controller
support. Native Gateway/route primitives live under `primitives/gateway`.
