# Tetragon, Trivy and security dashboards — 2026-11-01

Focused K3s play `6ae704a6789ac234e3344799` started at 12:21 Europe/Istanbul
(09:21 UTC). Kubernetes reported v1.37.1+k3s1 and Linux 6.1.167 with readable BTF
on all three nodes. Starting revision: `e4ab70b`. Only security tools and their
required Grafana/metrics/log pipeline were deployed; no Ceph, application databases
or platform PKI. Helm 4.3.1 installed Tetragon 1.8.0, Trivy Operator chart 0.38.1
(operator 0.36.1, scanner 0.76.1), VM stack 0.97.0 and Grafana Operator 5.25.0.
Grafana reported 13.2.3. Monitoring used local-path storage and lab-only overrides.

## Results

All 25 result assertions passed. Both dashboards synchronized through Grafana
Operator. All 27 panels queried through Grafana's actual datasource API without
query errors. Automated Chromium checks rendered both dashboards, exercised
namespace/image/severity and node/namespace/workload selections, and observed
12 + 15 successful datasource requests with no rendering/plugin errors.
Machine-readable [evidence](evidence/security-2026-11-01.json) records each check,
panel response and browser result.

| Area | Observed result |
| --- | --- |
| Tetragon deployment | Three agents 2/2, operator Ready; BPF startup succeeded on Linux/BTF preflight; no Cilium CNI dependency was needed for this K3s/Flannel test |
| Real runtime events | Harmless `/bin/ls` execs in process-probe generated events with the expected node, Pod and observed workload identity; events reached VictoriaLogs |
| Redaction | Process and parent argument fields absent from sampled events, including packed dashboard messages |
| Metrics ingestion | Five security targets healthy: three agents, tetragon-operator-metrics, and trivy-operator; observed namespace/workload labels preserved |
| Trivy deployment | Revised 1 GiB operator limit remained stable; reports produced for public workload images, including all three containers in Tetragon's scan |
| Controlled image identity | Report digests matched actual running image IDs for busybox and NGINX fixtures |
| Vulnerability totals | Three controlled reports; two independent NGINX 1.25.5 reports each contained 828 findings: Critical 21, High 83, Medium 80, Low 150, Unknown 494. Busybox report contained zero findings |
| Dashboard reconciliation | Raw total 1656, represented reports 3, image identities 2; deduplicated image ranking 828. These are report findings, not globally unique CVEs |
| Image/severity filters | Selecting library/nginx + Critical yielded 42 raw findings, two reports, one image identity and deduplicated Critical count 21 |
| Configuration / exposed-secret panels | Configuration total 42 matched report summaries; zero exposed-secret findings matched three actual reports. A nonexistent namespace returned No data, not a fabricated zero |
| Tetragon dashboard | Ready/Desired 3/3; real PROCESS_EXEC/PROCESS_EXIT metrics; node-filtered log messages retained structured event fields and redaction |

## Defects fixed

1. **Trivy multi-container cache lock:** sibling scanner containers shared the
   filesystem scan cache and one failed with `cache may be in use by another
   process: timeout`. `trivy.configFile.cache.backend: memory` gives each process
   its own scan cache while retaining the shared downloaded vulnerability DB.
   Subsequent multi-container scans completed and produced actual report CRs.
2. **Trivy queue retention:** the pinned operator's concurrency checker counts
   retained completed Jobs. The template's 30-minute scanJobTTL exhausted the
   two-Job queue after the first batch. Empty scanJobTTL restores immediate Job
   cleanup. Obsolete completed/failed lab Jobs were removed once after upgrading;
   subsequent scans progressed and cleaned up automatically. Reports remain.
3. **Grafana PromQL interpolation:** explicit `:regex` escaped an ordinary image
   value as `library\/nginx`, causing HTTP 400 / invalid string literal. Prometheus
   targets and variable queries now use datasource-aware interpolation; actual
   browser requests with library/nginx + Critical succeeded after the change.
4. **Tetragon log messages:** native JSON collection had no original message,
   yielding VictoriaLogs' missing-_msg placeholder. `pack_json fields (node_name,
   process_*) as _msg` creates a real event message without discarding expanded
   fields or restoring redacted arguments.

The lab-only Grafana limit initially set to 512 MiB caused an OOM during browser
testing; the reproducible override now uses 1 GiB. This is not a change to the
shared Grafana template. Its ephemeral storage meant dashboards/datasources were
reprovisioned after replacement; lab resync periods were set to 30 seconds. The
final Grafana Pod had no restarts during the successful checks.

Reproduction inputs: `flux/runbooks/examples/security-validation-monitoring.yaml`
merged after shared VM stack values, and `security-validation-workloads.yaml`.
Security charts used their repository values, including the fixes above. Metrics
queries used the live dashboard JSON via `/api/dashboards/uid/...` and
`/api/ds/query`. Trivy totals were compared with `kubectl get vulnerabilityreports,
configauditreports,exposedsecretreports -n security-validation -o json`. Events
were cross-checked through VictoriaLogs and vmagent's `/api/v1/targets`.

No enforcement/kill policy, private-registry access, production capacity, full
cluster scan completeness or backup/restore claim is made. Missing conditional
loss/error counters remain No data; they are not converted to zero. The old
full-platform acceptance queue is not completed by this focused test.

## Teardown

The user requested findings publication and immediate destruction of this lab.
Commit and verify these findings on both remotes before destroying the playground;
append the confirmed destruction outcome afterward. Do not retain a stopped play.
