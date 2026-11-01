# Runtime security and vulnerability scanning

Reusable Flux HelmRelease templates. Selecting a component through a cluster
Kustomization deploys it normally; no default suspension or resource-based
activation gate is configured. Resource availability is assumed. The playground
is destroyed, so these templates are locally validated, not live-tested.

| Component | Pinned chart / application | Purpose |
| --- | --- | --- |
| [Tetragon](tetragon/README.md) | 1.8.0 / 1.8.0 | Node-level eBPF process telemetry and runtime investigation |
| [Trivy Operator](trivy-operator/README.md) | 0.38.1 / 0.36.1 | Image vulnerability and configuration reports |

Sources are the official Cilium and Aqua Helm repositories. Chart archives were
verified against index SHA-256 digests before rendering with Helm 4.

These complement admission policies and Cilium network policies. Neither tool
blocks vulnerable images or malicious runtime activity in this configuration:
no Tetragon enforcement TracingPolicy or report-driven admission integration is
installed. Review policies independently from observation/scanning.

Both expose ServiceMonitors for the existing VictoriaMetrics stack. Tetragon
exports events through a stdout sidecar, which vlagent can collect into
VictoriaLogs. Trivy reports are Kubernetes custom resources and summary metrics
can be queried in Grafana. No new Grafana dashboard is supplied here.

## Deployment

The `iximiuz-platform` overlay selects both components and reconciles them after
foundation, monitoring CRDs and Cilium, with HelmRelease and CRD health checks.
Other clusters choose components by including the desired directories. Use the
[verification runbook](../../runbooks/operations/security-tools.md).

Tetragon uses upstream process-cache and event-export scope/rate defaults. Trivy
scans all namespaces with upstream scan concurrency and normal-speed image scans.
Regular resource requests/limits and worker placement remain explicit deployment
settings; they do not suspend or silently disable a selected component. Operators
and scans run away from labelled control-plane/master nodes, while Tetragon's
node-local agents also run on control-plane nodes.

Tetragon's dedicated namespace allows the host access and elevated capabilities
required by the agent. Trivy runs in a separate baseline namespace; node/infra and
cluster-compliance collection stay explicitly disabled because they require
additional host-access decisions, not because resources are presumed unavailable.
Review those privileges before enabling them. Global registry-credential discovery
also remains disabled; configure private registry credentials deliberately.
