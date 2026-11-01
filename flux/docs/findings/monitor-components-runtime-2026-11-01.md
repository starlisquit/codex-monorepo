# Monitoring Component runtime verification — 2026-11-01

Fresh K3s playground `6ae791fa7f32053bde29d314`, Flux path
`./flux/clusters/20261101-222442-monitor-components-29d314`, configuration revision
`c3d52c878f9f6c64bc4efbeb103d155ce308d005`. Only certificate prerequisites,
monitoring CRDs, VictoriaMetrics operator 0.68.1 (v0.75.0), ephemeral VMSingle,
VMAgent, two application fixtures and namespace-isolation decoys were deployed.
No Ceph, Grafana or full monitoring stack was required.

## Runtime assertions

- Deployment `api-application` selected the ServiceMonitor opt-in; Deployment
  `worker-application` selected PodMonitor. Both exposed named metrics port 8081.
- The VictoriaMetrics operator converted them to VMServiceScrape and VMPodScrape;
  both became operational. VMAgent reported exactly two healthy application
  targets, with no scrape error, and VMSingle stored `template_probe` samples
  with the expected api/worker labels.
- Added same-label decoy Pods (and the api metrics Service) in namespace default.
  Neither monitor discovered them and no decoy metric was stored. Discovery stayed
  in applications even though VMAgent selected scrape resources cluster-wide.
- During a controlled negative test, suspended only the disposable api Flux child
  and changed its ServiceMonitor selector to a nonexistent matching metrics
  Service. Its target disappeared; the worker target stayed healthy. Restoring
  the selector and resuming reconciliation restored both healthy targets.
- Rolled both Deployments. The collector discovered the new Pod names/IPs, both
  targets recovered, and samples from the replacement Pods were stored. Decoys
  remained excluded. Stored historical series were not confused with current
  targets; post-rollout metric queries used current Pod names.

[Sanitized evidence](evidence/monitor-components-runtime-2026-11-01.json) records
before/after targets, actual metric samples and negative-test assertions. The
reproduction script is retained in this run as `verify-monitors.py`.

## Routine validation

`validate.sh` now invokes `validate-compositions.py`. Every one of the 12 current
Kustomize Components is built with its owner, in 46 combinations. Deployment
cases use two differently named/labeled apps; assertions cover monitor selection,
namespace scope, named ports and exact dedicated Service selection. Gateway
cases check listener and renamed parent/backend references; RBAC cases check
subject/role names, namespace transformations and cluster-scoped metadata.
Cilium's bootstrap Component is also built and its dependency removal checked.
Components cannot be built standalone by Kustomize, so wrapping them is required;
none are silently skipped. These checks require only existing Python/PyYAML and
Kustomize, with no environment-substitution or generation changes.

The live test uses the existing VictoriaMetrics conversion path. It does not
claim a separate Prometheus server was tested or that port declarations provide
application instrumentation. The Python metrics fixtures deliberately supplied
real Prometheus exposition. VMSingle data was disposable; no persistence/backup
claim is made.

## Teardown

Findings/configuration will be published to both remotes before destroying this
playground; confirmed destruction will be recorded afterwards.
