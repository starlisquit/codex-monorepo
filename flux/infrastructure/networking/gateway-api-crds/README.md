# Gateway API CRDs

Vendored upstream Gateway API Standard channel **v1.6.3** core definitions:
GatewayClass, Gateway, HTTPRoute, GRPCRoute, BackendTLSPolicy and ReferenceGrant.
This matches the documented Gateway API version for Cilium 1.20.4. That controller also requires the TLSRoute CRD; select the
L4 opt-in with Cilium Gateway API even when no TLSRoute instance is created.
Select this directory once per cluster and wait for CRDs to be Established
before enabling Cilium Gateway API support. No controller is installed here.

For TLSRoute, TCPRoute and UDPRoute additionally select the independent
[`opt-in/l4-routes`](opt-in/l4-routes) base. These stable v1 APIs replace the
older v1.4.0 experimental route definitions. Native Gateway/route primitives
live under `primitives/gateway`. ListenerSet is not included by these bases.

Do not downgrade pre-existing CRDs or share ownership with another CRD installer.
For upgrades, check storedVersions and migrate stored objects as required before
removing API versions. Deleting a CRD deletes all instances of that kind.
Existing completed-run evidence retains its original validation version/scope.
