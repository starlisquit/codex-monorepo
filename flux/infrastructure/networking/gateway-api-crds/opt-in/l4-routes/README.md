# L4 route CRDs

Official Kubernetes SIG Network Gateway API **v1.6.3 Standard** definitions:

- https://github.com/kubernetes-sigs/gateway-api/blob/v1.6.3/config/crd/standard/gateway.networking.k8s.io_tlsroutes.yaml
- https://github.com/kubernetes-sigs/gateway-api/blob/v1.6.3/config/crd/standard/gateway.networking.k8s.io_tcproutes.yaml
- https://github.com/kubernetes-sigs/gateway-api/blob/v1.6.3/config/crd/standard/gateway.networking.k8s.io_udproutes.yaml

Select this base in addition to the core CRD base when L4 routes are needed.
TLSRoute, TCPRoute and UDPRoute use stable v1 APIs. This replaces the earlier
`opt-in/experimental-routes` v1.4.0 bundle; do not select both owners. It installs
no controller. Confirm controller protocol support and real traffic independently.
Coordinate upgrades and stored API versions; preserve CRDs while instances exist.
