# Per-workload connection allowlist

A standard Kubernetes NetworkPolicy for a Pod or Deployment. It restricts **both
incoming and outgoing connections** for matching Pods in namespace `applications`.
It is included in the parent policy build, but no current workload is given its
opt-in label automatically.

| Direction | Allowed peer | Port |
| --- | --- | --- |
| Ingress | `applications` Pods labelled `networking.platform/caller: approved` | TCP 8080 |
| Egress | CoreDNS Pods in `kube-system` | UDP/TCP 53 |
| Egress | CNPG Pods labelled `cnpg.io/cluster: application-db` in `databases` | TCP 5432 |
| Egress | Valkey Pods with the specified release/name labels in `databases` | TCP 6379 |
| Egress | Documentation placeholder `192.0.2.10/32` | TCP 443 |

**Replace or remove the documentation IP rule before opting a real workload in.**
Review actual caller/dependency labels, namespace names and destination Pod ports.
Delete unused allows; duplicate a rule for each additional dependency. Return
traffic for an allowed connection is permitted automatically, so replies do not
need reverse-direction allow rules. Connections to the Kubernetes API, OTLP
agents, NATS or monitoring scrapers are not implicitly allowed by this example.
Add their exact peers/ports if the chosen workload needs them.

## Apply to a Pod or Deployment

For a Pod, add this to `metadata.labels`:

```yaml
networking.platform/connections: allowlisted
```

For a Deployment, add it to the **Pod template**, which creates a rollout:

```yaml
spec:
  template:
    metadata:
      labels:
        networking.platform/connections: allowlisted
```

Lab example, after customizing the policy:

```sh
kubectl apply --dry-run=server -k flux/policies/network/connection-allowlist
kubectl apply -k flux/policies/network/connection-allowlist
# For a standalone Pod:
kubectl -n applications label pod MY_POD networking.platform/connections=allowlisted
# For a Deployment:
kubectl -n applications patch deployment MY_DEPLOYMENT --type=merge \
  -p '{"spec":{"template":{"metadata":{"labels":{"networking.platform/connections":"allowlisted"}}}}}'
```

Replace `MY_POD`/`MY_DEPLOYMENT`. Prefer committing the label in the workload's Git
manifest where Flux manages it. To withdraw selection, remove the same label from
the Pod or Deployment template. Other policies can still isolate that workload.
For another namespace, use an overlay to change both `metadata.namespace` and any
caller namespace selectors that should move with it; source namespaces such as
`databases` and `kube-system` may need to stay unchanged.

## Important boundaries

Namespace and Pod selectors in each peer are **AND**, while separate peers/rules
are **OR**. NetworkPolicies are additive: another matching policy can grant more
connections. This template cannot override a broader allow policy. Review all
policies selecting the workload before claiming a strict boundary.

IP blocks are for fixed external addresses, not Services or changing DNS names.
Service translation and SNAT ordering are CNI-dependent; use Pod selectors for
in-cluster dependencies. Standard NetworkPolicy does not support FQDN allowlists.
Use a reviewed CiliumNetworkPolicy for domain-based restrictions if needed.
Allowing DNS resolution does not allow the resolved destination connection.
The DNS example assumes this lab's CoreDNS Pods; NodeLocal DNS needs a different
rule. Host/node traffic and hostNetwork Pods have CNI-specific behavior.

This controls L3/L4 reachability, not TLS, user authentication or HTTP paths. For
example, allowing TCP 6379 does not enforce Valkey TLS. Container image pulls are
performed by the node and are governed by the separate image admission policy,
not this Pod's egress policy.

## Verification

```sh
kustomize build flux/policies/network/connection-allowlist
kubectl -n applications describe networkpolicy workload-connection-allowlist
```

From disposable clients, check approved/unapproved caller labels and namespaces,
then from a selected test Pod verify DNS, each required dependency and an explicitly
unapproved destination. Test direct Pod and Service paths where applicable, using
fresh connections rather than existing sessions. Verify readiness probes, telemetry
exports and scraping after selection. Port-forwarding is not a valid network-policy
test. This new combined template is render-validated only: no playground is running.
The [earlier ingress test](../README.md#reproduce-enforcement-checks) exercised the
same namespace/Pod selector semantics, not this new egress rule set.
