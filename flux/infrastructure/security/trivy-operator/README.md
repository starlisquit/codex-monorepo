# Trivy Operator

Deploys the Kubernetes operator, not a standalone Trivy CLI or central scan server.
The operator creates scan Jobs and vulnerability/configuration report CRs for
workloads in `demo` and `applications` only. Scan Jobs run in `trivy-system`, not
inside target namespaces; they therefore do not conflict with the application's
image allowlist. Review access to the operator namespace independently.

Defaults limit concurrent scan Jobs to one, enable Trivy's slower/lower-resource
mode, retry failed scans after five minutes, and expire reports after 24 hours.
Finished Jobs/scan Secrets have 30-minute retention. Operator and scan affinity
exclude labelled control-plane/master nodes. A scan requests 1 GiB ephemeral
storage with a 2 GiB limit; very large images may need more memory/disk and fail.
Scan failures are not clean vulnerability results.

Enabled: image vulnerability and workload configuration scanning, with unfixed
vulnerabilities retained in findings. Disabled initially: node/infra collection,
cluster compliance, RBAC assessment, exposed-secret scanning, SBOM generation,
cluster SBOM cache, and per-CVE metric labels. These choices limit host access,
API writes, database storage and metric cardinality. Summary finding metrics stay
enabled. Namespace targeting does not imply the operator's cluster RBAC is minimal
or namespace-isolated; inspect the rendered roles before use.

Global Secret/service-account credential discovery is disabled. Private registry
scans need an explicitly scoped supported credential configuration; this template
assumes the public demo images. Jobs still need HTTPS egress to image registries,
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
