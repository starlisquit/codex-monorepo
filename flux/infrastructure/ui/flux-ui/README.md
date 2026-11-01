# Standalone Flux Web UI

Uses the official `flux-operator` chart `0.62.1` in **web-server-only mode**:

```yaml
installCRDs: false
web:
  enabled: true
  serverOnly: true
```

The chart/image name is shared with Flux Operator, but this release only runs the
Web UI. It does not install Flux controllers, reconcile FluxInstances, manage
Flux upgrades, or install the operator's CRDs. No FluxInstance is included.

Bootstrap Flux separately using your chosen method, such as `flux bootstrap`.
Then create the `ui` namespace, reconcile shared chart sources and monitoring
CRDs, and include `./flux/infrastructure/ui/flux-ui` in the cluster's Flux
Kustomizations. The HelmRelease remains suspended until intentionally enabled.
The existing `sources/flux-operator.yaml` OCI source is retained because it
supplies the chart used for this UI-only deployment.

The chart creates the standalone server's view/impersonation RBAC rather than the
operator's cluster-admin binding. Configure UI authentication and user permissions
through `web.config` or `web.configSecretName` before exposing it broadly. The UI's
GitOps actions remain subject to the configured user-access model; it does not
become the owner of Flux's installation.

Ingress and HTTPRoute are disabled. After deployment, access locally with:

```sh
kubectl -n ui port-forward service/flux-ui 9080:9080
```

The ServiceMonitor stays enabled for collection by the VM stack. The release
depends on `observability/prometheus-operator-crds` and keeps the chart's NetworkPolicy
allowing the web and metrics ports. Bootstrap or UI deployment has not been
performed against a cluster; Helm/Kustomize renders validate these templates.
