# Ingress NetworkPolicy templates

These use the standard `networking.k8s.io/v1` NetworkPolicy API, enforced by the
cluster's Cilium CNI. They are built-in Kubernetes resources, not custom CRDs.
No Cilium-specific API is required. Unlike Kyverno Audit policies, these policies
**enforce traffic restrictions immediately** on matching Pods.

## Additional connection allowlist

Use [connection-allowlist/](connection-allowlist/README.md) to constrain both ingress
and egress for a selected Pod or Deployment. It includes DNS, database/cache peers,
and a replace-before-use external IP example. Its opt-in label differs from the
ingress-only profiles below.

## Selected workloads: application and monitoring callers

The parent Kustomization includes `restricted-ingress/`. In namespace
`applications`, it selects only destination Pods carrying:

```yaml
networking.platform/ingress: restricted
```

Label the Deployment's **Pod template**, not just the Deployment metadata.
The two policies together allow:

| Destination port | Allowed source namespace | Required source Pod label |
| --- | --- | --- |
| TCP 8080 | `applications` | `networking.platform/caller: approved` |
| TCP 9090 | `observability` | `app.kubernetes.io/name: vmagent` |

All other Pod ingress to selected destinations is denied unless another policy
allows it. Egress is unchanged, including outgoing DNS queries and their replies.
Traffic to unlabeled destination Pods is unaffected by these templates.
Customize namespaces, labels and actual **destination Pod ports** in an overlay.
A Service port mapped to a different targetPort does not change the destination
port you must allow. The monitoring example uses the stack's vmagent name label;
confirm your agent's labels and the application's metrics listener before use.
The template does not create Services, metrics endpoints, or scrape resources.

A namespaceSelector and podSelector inside the **same `from` item** are ANDed.
Putting them in separate `from` items would allow either namespace members OR
matching Pods from any namespace, a much broader rule. The test covers this.

Kubernetes NetworkPolicies are additive: this is not a higher-priority deny.
Any other matching allow policy can expand access. These templates do not isolate
host-network traffic, node-originated probes, or ingress through a Gateway unless
the Gateway's source identity is explicitly allowed. They are not HTTP/user
identity authorization, TLS, or a boundary against someone permitted to relabel
caller Pods. Review RBAC accordingly. Port-forward access is not a valid test of
Pod-to-Pod policy enforcement.

## Optional namespace-wide baseline

`namespace-default-deny/` is deliberately excluded from the parent build. It
isolates **ingress and egress for every Pod** in `applications`, including unlabelled Pods.
Include it only after adding each workload's required allows, including ingress
controllers, monitoring, outbound dependencies, and DNS as appropriate. An ingress
allow alone cannot open an egress-isolated caller's outbound connection. The selected-workload policy above
already isolates its own destinations without this baseline.

```sh
kubectl diff -k flux/policies/network/restricted-ingress
# After adapting the template for your workloads:
kubectl apply -k flux/policies/network/restricted-ingress
# Optional, broader baseline; review before applying:
# kubectl apply -k flux/policies/network/namespace-default-deny
```

In this repo the lab's existing `policies` Flux Kustomization reconciles the opt-in
templates after Cilium and Kyverno. No existing application is automatically
labelled into ingress isolation. Add policy selection labels only after checking
its callers. Change manifests in Git for lasting changes; manual edits are reverted.

## Reproduce enforcement checks

From a clone on `dev-machine`, with cluster-admin access:

```sh
flux/docs/runbooks/scripts/test-network-policies.sh
```

The script uses temporary namespaces, a small HTTP server and BusyBox clients,
all constrained to workers with small resource budgets. It tests direct Pod IPs,
not port-forwarding. It verifies baseline connectivity, approved same-namespace
application access, monitoring access from another namespace, rejected wrong
labels/namespaces/ports, an unselected destination, and the optional namespace
baseline. Policy propagation is retried before assertions. Temporary namespaces
are removed on exit; no existing workloads or Git-managed policies are modified.
Image pulls can take several minutes. Run detached when using a short-timeout tool.

## Verified in the rebuilt lab — 2026-11-01

The earlier ingress-only baseline test passed all 15 access assertions plus the outgoing DNS check against
Cilium in play `6ae6cfaf789ac234e32e00bf`. Before policies, both listener ports and
cross-namespace access worked. After policies, all approved paths worked and all
six wrong-label/namespace/port cases were blocked. Unselected Pods stayed reachable
until the namespace-wide baseline was applied; both explicit allows continued to
work afterward. Each assertion required three consecutive results. The test
exited zero and removed its temporary namespaces.

The workers' CPU request budget was nearly full: an initial run with 5m per test
Pod could not schedule all clients. The helper now requests 1m per Pod (8m total)
and 8 MiB memory each; this is sufficient for these short, mostly idle probes,
not a workload sizing recommendation. The initial test namespaces were removed
before rerunning. No permanent workload placement or resource settings changed.


The baseline now denies egress too. The updated helper checks that an ingress
allow alone cannot bypass the caller's egress isolation, then adds an explicit
8080 egress allow for the approved test caller. This updated helper has been
syntax/render checked; the earlier live result does not verify the revised test.
The playground remains destroyed.

The optional resource is now named `default-deny-all`. If you manually installed
the former `default-deny-ingress` resource, apply the new template first. You may
then delete the old ingress-only resource; leaving it in place is redundant and
does not weaken the combined deny baseline. As with all standard NetworkPolicies,
other matching allow policies can still open connections in either direction.
