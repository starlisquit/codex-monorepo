# Experimental L4 route CRDs

Vendored verbatim from Kubernetes SIG Network Gateway API release **v1.4.0**:

- https://github.com/kubernetes-sigs/gateway-api/blob/v1.4.0/config/crd/experimental/gateway.networking.k8s.io_tlsroutes.yaml
- https://github.com/kubernetes-sigs/gateway-api/blob/v1.4.0/config/crd/experimental/gateway.networking.k8s.io_tcproutes.yaml
- https://github.com/kubernetes-sigs/gateway-api/blob/v1.4.0/config/crd/experimental/gateway.networking.k8s.io_udproutes.yaml

Select this base in addition to the standard CRD base only when L4 routes are
needed. It adds TLSRoute (served v1alpha2/v1alpha3, storage v1alpha3), TCPRoute
(v1alpha2), and UDPRoute (v1alpha2). It does not install a controller or imply
controller support. Do not also install another owner for these same CRDs.
Experimental APIs can change incompatibly; coordinate upgrades and stored API
versions before removing/replacing them. Preserve CRDs while route instances
are in use; deleting a CRD deletes all instances of that kind.
