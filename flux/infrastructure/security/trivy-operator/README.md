# Trivy Operator

The operator has a 1 GiB memory limit: the first full-platform bootstrap repeatedly
OOM-killed it at 256 MiB. Scan concurrency is two Jobs. Per-container requests are
128 MiB memory and 256 MiB ephemeral storage; multi-container workloads otherwise
reserve several GiB per Job and could not schedule on the lab workers. Limits
remain 2 GiB memory and 8 GiB ephemeral storage per scanner. Monitor actual use,
scan completion, and worker disk space before raising concurrency.

Deploys the Kubernetes operator, not a standalone Trivy CLI or central scan server.
The operator creates scan Jobs and vulnerability/configuration report CRs for
workloads across all namespaces. Scan Jobs run in `trivy-system`, not
inside target namespaces; they therefore do not conflict with the application's
image allowlist. Review access to the operator namespace independently.

The operator uses upstream scan concurrency (ten Jobs for the pinned chart),
normal-speed image scanning and current-revision scan selection. Reports expire
after 24 hours; Jobs/scan Secrets have 30-minute retention. Operator/scan affinity
excludes labelled control-plane/master nodes. Each scan requests 512 MiB RAM and
2 GiB ephemeral storage with limits of 2 GiB RAM and 8 GiB ephemeral storage.
These are normal workload budgets, not activation gates.

Image vulnerability, configuration, RBAC assessment, exposed-secret scanning and
SBOM generation use the upstream enabled defaults. Node/infra and cluster-compliance
collection remain explicitly disabled because they require additional host access;
this is a separate privilege decision. Cluster SBOM caching stays at the upstream
default. Per-CVE/image metric labels remain off to avoid unnecessary cardinality,
while summary findings are exposed. Inspect rendered RBAC before production use.

Global Secret/service-account credential discovery is disabled. Private registry
scans need an explicitly scoped supported credential configuration; the default configuration
can scan public images without them. Jobs still need HTTPS egress to image registries,
vulnerability databases (chart defaults use mirror.gcr.io) and any package metadata
services Trivy contacts. HTTPS verification is retained. A blanket egress policy
on `trivy-system` must account for these dependencies; allowing only the registry
holding the Trivy executable is insufficient.

Helm's CRD CreateReplace mode manages the chart's report schemas. There are more
installed report CRDs than enabled scanners; an installed report CRD does not
prove that scanner is enabled. Report contents and metrics are not wired into
admission rejection by this change.

```sh
kubectl -n trivy-system get deployment,pods,jobs
kubectl -n trivy-system logs deployment/trivy-operator --tail=50
kubectl get vulnerabilityreports,configauditreports -A
kubectl -n demo get vulnerabilityreports -o yaml
kubectl -n trivy-system get servicemonitor
```

Wait for a successful scan and inspect `.report.summary`, scanner version, image
identity and conditions/events. Do not treat missing reports, stale databases or
failed Jobs as a clean bill of health. Failed/missing registry access can prevent
reports. No scanner workload or CVE results were live-verified in the destroyed lab.
