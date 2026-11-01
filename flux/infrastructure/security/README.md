# Runtime security and vulnerability scanning

Reusable Flux HelmRelease templates, initially suspended. The cluster was destroyed;
these resources have been rendered and validated locally, not exercised on live nodes.

| Component | Pinned chart / application | Purpose |
| --- | --- | --- |
| [Tetragon](tetragon/README.md) | 1.8.0 / 1.8.0 | Node-level eBPF process telemetry and runtime investigation |
| [Trivy Operator](trivy-operator/README.md) | 0.38.1 / 0.36.1 | Image vulnerability and workload configuration reports |

Sources are the official Cilium and Aqua Helm repositories. Chart archives were
verified against index SHA-256 digests before rendering with Helm 4. Helm pins
chart versions in Git; review versions and images before promotion.

These complement existing controls: Kyverno/admission policies validate workload
configuration, image allowlists restrict image references, Cilium policies control
network connections, Tetragon observes running processes, and Trivy reports known
vulnerabilities/misconfiguration. None automatically blocks vulnerable images or
malicious runtime activity with this configuration. No new Tetragon enforcement
TracingPolicy or report-driven admission integration is installed.

Both expose ServiceMonitors for the existing VictoriaMetrics stack. Tetragon events
are exported through a stdout sidecar, so the configured vlagent DaemonSet can
collect them into VictoriaLogs. Trivy reports are Kubernetes custom resources;
its summary metrics can be queried in Grafana. Neither component supplies a new
Grafana dashboard in this change.

## Deployment and sizing

The shared releases use `spec.suspend: true`. The `iximiuz-platform` overlays enable
those releases, but their **parent Flux Kustomizations remain suspended** in
`clusters/iximiuz-platform/infrastructure.yaml`. This is deliberate: the last play
had API/controller instability, so security agents/scans must not silently add
load to the next bootstrap. See the [enablement runbook](../../runbooks/operations/security-tools.md).

For three nodes, configured Tetragon requests total approximately 880 MiB RAM
(three 256 MiB agents plus three 16 MiB exporters and a 64 MiB operator). Trivy
adds a 128 MiB operator and one 256 MiB-request scan Job, approximately **1.23 GiB
additional memory requests** while scanning. Actual peaks and kernel/BPF memory
can differ; a scan container has a 1 GiB memory limit and 2 GiB ephemeral-storage
limit. This is additional capacity, not reserved space already present in the lab.

Operators/scans are constrained away from nodes labelled control-plane/master.
Tetragon agents still run on every node, including the control plane, because
process monitoring is node-local. Reserve that node's additional headroom. Monitor
API latency, disk space, scan OOMs, event drops and exporter backlog before widening
coverage. Scanner temporary image layers and databases can pressure root disks.

Do not broaden the application-only image allowlist or isolation policies globally
to accommodate these agents. Tetragon uses host access and elevated capabilities
by design; its dedicated namespace is labelled privileged for Pod Security
Admission. Trivy runs in a separate baseline namespace. This separation does not
by itself constitute a network/RBAC isolation boundary.
