# CronJob primitive

Native `batch/v1` scheduled task, using `busybox:1.37.0` as a replaceable starter.
Requires Kubernetes >=1.27 for stable `spec.timeZone` support.

Defaults: daily at 03:00 Europe/Istanbul; `Forbid` overlapping scheduled Jobs;
5-minute missed-start deadline; 10-minute Job runtime deadline; two retries;
one successful and three failed Jobs retained, subject also to a 24-hour TTL.
Pods do not restart in place, run non-root with a read-only root filesystem,
and have resources and no mounted API token. Retry attempts can repeat work;
your task must tolerate retries. Forbid does not prevent manually created Jobs
from overlapping. Jobs are not guaranteed to run exactly once.

For `flux/clusters/<run>/scheduled-task/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: demo
namePrefix: maintenance-
resources:
- ../../../infrastructure/primitives/cronjob
patches:
- target:
    kind: CronJob
    name: scheduled-task
  patch: |-
    - op: replace
      path: /spec/schedule
      value: '*/30 * * * *'
```

Select the namespace separately. Replace image, command, resources and schedule
for the actual task; use existing Secret references for credentials. Configure a
dedicated ServiceAccount/RBAC only when needed. There is no Service or probe:
completion/exit status and logs are the task's success signal.

After deployment, test without waiting for the schedule:

```sh
kubectl -n demo create job maintenance-check --from=cronjob/maintenance-scheduled-task
kubectl -n demo wait --for=condition=complete job/maintenance-check --timeout=11m
kubectl -n demo logs job/maintenance-check
kubectl -n demo delete job maintenance-check
```

Suspend scheduling with `spec.suspend: true` for maintenance; this does not stop
Jobs already running. A Flux readiness check on the CronJob alone does not prove
that its task completed. Build/composition checks have passed; runtime execution
has not been verified in a playground.
