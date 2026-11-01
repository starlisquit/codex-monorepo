# Verify container log collection

From `dev-machine`, after the observability release reconciles:

```sh
kubectl -n observability get vlagent victoria-metrics-k8s-stack
kubectl -n observability rollout status daemonset/vlagent-victoria-metrics-k8s-stack --timeout=3m
kubectl -n observability get pods -l app.kubernetes.io/name=vlagent -o wide
kubectl -n observability logs -l app.kubernetes.io/name=vlagent --tail=30
kubectl -n observability get grafanadashboard platform-container-logs
```

Expect one Ready agent on each Kubernetes node, including the control plane.
The former push-only StatefulSet should be removed by the operator. The native
OTLP push endpoint remains available through the existing headless Service.
Inspect agent logs for API, hostPath access, buffering, or remote-write errors.

Open **Platform / Container logs** in Grafana. Choose a namespace, Pod, container
and time range. Verify an existing structured INFO/ERROR record using the level
filter; then select All to include records without severity. The message filter
is a regular expression, not literal text. No traffic generator is needed to see
existing infrastructure logs.

For a direct backend check, run the following through a local forward in another
terminal:

```sh
kubectl -n observability port-forward svc/vlsingle-victoria-metrics-k8s-stack 19428:9428
curl -fsSG http://127.0.0.1:19428/select/logsql/query \
  --data-urlencode 'query=_time:5m kubernetes.pod_namespace:="demo"' \
  --data-urlencode 'limit=5'
curl -fsSG http://127.0.0.1:19428/select/logsql/field_values \
  --data-urlencode 'query=_time:5m *' \
  --data-urlencode 'field=kubernetes.pod_namespace'
```

Use a namespace generating recent stdout/stderr if demo has no recent output.
Inspect actual records for Kubernetes metadata and `output_stream`; a healthy
DaemonSet alone does not prove ingestion. Check log records from all three nodes
using `kubernetes.pod_node_name`. To check restart continuity, compare a uniquely
identified pre-restart record count, restart only its node's agent, and query that
record again; unrelated agents need not restart. Avoid recreating checkpoint data.

Removing the collector enablement returns vlagent to push-only mode. HostPath
checkpoints/buffers are not automatically erased; retain or remove them deliberately
when decommissioning a node. Re-enabling with preserved checkpoints resumes from
the saved positions, subject to runtime log rotation.
