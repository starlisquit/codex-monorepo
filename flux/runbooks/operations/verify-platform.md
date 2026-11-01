# Verify platform and telemetry

Run from `dev-machine`. These checks determine current health; the docs contain
historical observations only. If the API is slow, use bounded requests and follow
the [incident runbook](../recovery/control-plane.md) instead of repeatedly forcing
reconciliation.

## Cluster and controllers

```sh
kubectl --request-timeout=10s get nodes -o wide
flux check
flux get kustomizations -A
flux get helmreleases -A
kubectl get pods -A
kubectl get pvc -A
kubectl -n kube-system get daemonset,pods -l k8s-app=kube-proxy
```

Expect Ready nodes, Ready selected releases/Kustomizations, no unexpected Pending
or crash-looping Pods, Bound workload PVCs, and no kube-proxy resources. Completed
bootstrap Jobs are expected. An OpenBao wait before initialization is expected;
an uninvestigated failed resource is not.

## Kubernetes resource Metrics API

```sh
kubectl wait --for=condition=Available apiservice/v1beta1.metrics.k8s.io --timeout=3m
kubectl get --raw /apis/metrics.k8s.io/v1beta1/nodes
kubectl top nodes
kubectl top pods -A
```

Metrics Server is separate from VictoriaMetrics and KEDA. Allow initial samples
to arrive. If `Metrics API not available` persists, inspect the APIService and
`kubectl -n observability logs deployment/metrics-server --tail=100`. See the
[component guide](../../infrastructure/observability/metrics-server/README.md)
for certificate, kubelet TLS, and deployment dependencies.

## Storage, database, and secrets

```sh
kubectl -n rook-ceph exec deploy/rook-ceph-tools -- ceph status
kubectl -n rook-ceph exec deploy/rook-ceph-tools -- ceph health detail
kubectl -n rook-ceph logs job/ceph-storage-check
kubectl -n databases get clusters.postgresql.cnpg.io application-db
kubectl -n secrets get certificates.cert-manager.io
kubectl -n secrets get secretstore,externalsecret
kubectl -n broker get statefulset nats
```

The original checks established three healthy PostgreSQL instances, three NATS
replicas, three unsealed OpenBao replicas, and successful External Secrets
synchronization. Repeat checks after any recovery; replication does not establish
backup recoverability.

## Grafana provisioning

Use the full API group to avoid ambiguous resource names:

```sh
kubectl -n observability get grafanas.grafana.integreatly.org
kubectl -n observability get grafanadatasources.grafana.integreatly.org
kubectl -n observability get grafanadashboards.grafana.integreatly.org
kubectl -n observability get grafanas.grafana.integreatly.org platform \
  -o jsonpath='{.status.conditions}'
```

Expect the binding's `GrafanaReady` condition True and synchronized datasources
and dashboards. Counts are not permanent acceptance criteria; the recorded lab
had 55 dashboards and five datasource CRs. Inspect conditions on any failures.

For local browser access, run one forward in its own terminal:

```sh
kubectl -n observability port-forward service/victoria-metrics-k8s-stack-grafana 3000:80
kubectl -n ui port-forward service/headlamp 8080:80
kubectl -n ui port-forward service/flux-ui 9080:9080
```

Use the appropriate login mechanism. Retrieve generated Grafana credentials only
through your approved secure workflow. Headlamp requires the user's own Kubernetes
credentials and RBAC; do not grant its application service account cluster-admin.

## Metrics ingestion and scrape errors

```sh
kubectl get --raw '/api/v1/namespaces/observability/services/vmsingle-victoria-metrics-k8s-stack:8428/proxy/api/v1/query?query=up' > /tmp/platform-up.json
python3 - <<'PY'
import json
results = json.load(open('/tmp/platform-up.json'))['data']['result']
print('series:', len(results))
print('up:', sum(r['value'][1] == '1' for r in results))
print('down jobs:', sorted({r['metric'].get('job', '') for r in results if r['value'][1] != '1'}))
PY
kubectl get --raw '/api/v1/namespaces/observability/services/vmagent-victoria-metrics-k8s-stack:8429/proxy/api/v1/targets' > /tmp/platform-targets.json
python3 - <<'PY'
import json
for target in json.load(open('/tmp/platform-targets.json')).get('data', {}).get('activeTargets', []):
    if target.get('health') == 'down':
        print(target.get('labels', {}).get('job'), target.get('lastError'))
PY
```

The recorded unresolved targets were controller-manager, scheduler, and etcd,
with serving-certificate name/trust errors. Do not disable verification just to
clear the target count. See [monitoring findings](../../docs/findings/observability.md).

## Demo and all three signals

```sh
kubectl -n demo get helmrelease opentelemetry-demo
kubectl -n demo get deployments,pods
kubectl -n demo logs deployment/otel-collector --tail=100
kubectl -n observability get service | grep -E 'vmagent|vlagent|vtagent|single'
kubectl -n demo port-forward service/quote 8080:8080
```

If the release uses a different Collector deployment name, find it using
`kubectl -n demo get deployments`. Check for exporter retry/queue/drop errors and
confirm that only currency, quote, and the Collector remain. Generate a small
request with `curl -fsS -H "Content-Type: application/json" --data '{"numberOfItems":2}' http://127.0.0.1:8080/getquote`
through the quote port forward. No automatic load generator remains. The worker-only affinity
is a capacity boundary: investigate Pending requests rather than moving the demo
onto the already constrained control plane.

Use Grafana Explore to query recent application series in VictoriaMetrics,
actual demo SDK log records in VictoriaLogs (DS), and recent service traces in
VictoriaTraces. Check service names and recent timestamps. Backend health,
Collector configuration, or scrape metrics alone do not prove all three signals.
The [fresh rebuild](../../docs/findings/rebuild-verification.md) verified all three
signals from quote traffic. Repeat these checks for the current play.


For reproducible backend queries, open three additional local forwards in separate
terminals:

```sh
kubectl -n observability port-forward svc/vmsingle-victoria-metrics-k8s-stack 18428:8428
kubectl -n observability port-forward svc/vlsingle-victoria-metrics-k8s-stack 19428:9428
kubectl -n observability port-forward svc/vtsingle-victoria-metrics-k8s-stack 10428:10428
```

After generating quote traffic, query recent metric samples and SDK logs:

```sh
python3 - <<'PYTHON'
import json, time, urllib.parse, urllib.request

def get(base, params):
    url = base + '?' + urllib.parse.urlencode(params)
    return urllib.request.urlopen(url, timeout=10).read().decode()

now = time.time()
print(get('http://127.0.0.1:18428/api/v1/query_range',
          {'query': 'quotes', 'start': now-300, 'end': now, 'step': '10s'}))
logs = get('http://127.0.0.1:19428/select/logsql/query',
           {'query': '_time:5m "Calculated quote"', 'limit': 3})
print(logs)
records = [json.loads(line) for line in logs.splitlines() if line.strip()]
if not records:
    raise SystemExit('No SDK logs yet; allow export/ingestion time and retry')
trace_id = records[0]['trace_id']
url = 'http://127.0.0.1:10428/select/jaeger/api/traces/' + trace_id
print(urllib.request.urlopen(url, timeout=10).read().decode())
PYTHON
```

Expect nonempty metric samples, SDK log records, and a trace matching a log's
`trace_id`. Recent range queries avoid mistaking an instant-query visibility lag
for absent ingestion. Stop the port forwards when finished.
