#!/usr/bin/env bash
# Exercise the actual templates against isolated, disposable worker Pods.
set -euo pipefail
repo_root=$(git rev-parse --show-toplevel)
template_dir="$repo_root/flux/policies/network"
suffix="$(date +%s)-${RANDOM}"
target_ns="netpol-app-$suffix"
monitor_ns="netpol-monitor-$suffix"
other_ns="netpol-other-$suffix"
cleanup() {
  kubectl delete namespace "$target_ns" "$monitor_ns" "$other_ns" \
    --ignore-not-found --wait=false >/dev/null || true
}
trap cleanup EXIT
export NETPOL_TARGET_NS="$target_ns" NETPOL_MONITOR_NS="$monitor_ns" NETPOL_OTHER_NS="$other_ns"
python3 - <<'PY' | kubectl apply -f - >/dev/null
import json, os
names = [os.environ[k] for k in ('NETPOL_TARGET_NS','NETPOL_MONITOR_NS','NETPOL_OTHER_NS')]
items = [{'apiVersion':'v1','kind':'Namespace','metadata':{'name':n}} for n in names]
def pod(ns, name, labels, server=False):
    command = ['sh','-c','mkdir -p /tmp/www; echo policy-test-ok > /tmp/www/index.html; httpd -p 8080 -h /tmp/www; exec httpd -f -p 9090 -h /tmp/www'] if server else ['sleep','1800']
    container = {'name':'busybox','image':'busybox:1.37.0','command':command,
                 'resources':{'requests':{'cpu':'1m','memory':'8Mi'},'limits':{'memory':'24Mi'}},
                 'securityContext':{'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL']}}}
    if server:
        container['readinessProbe']={'tcpSocket':{'port':8080},'periodSeconds':2}
    items.append({'apiVersion':'v1','kind':'Pod','metadata':{'name':name,'namespace':ns,'labels':labels},
                  'spec':{'terminationGracePeriodSeconds':1,'automountServiceAccountToken':False,'securityContext':{'runAsNonRoot':True,'runAsUser':1000},
                          'affinity':{'nodeAffinity':{'requiredDuringSchedulingIgnoredDuringExecution':{'nodeSelectorTerms':[{'matchExpressions':[{'key':'kubernetes.io/hostname','operator':'In','values':['node-01','node-02']}]}]}}},
                          'containers':[container]}})
pod(names[0],'protected',{'networking.platform/ingress':'restricted'},True)
pod(names[0],'unselected',{},True)
pod(names[0],'approved',{'networking.platform/caller':'approved'})
pod(names[0],'denied',{})
pod(names[0],'wrong-namespace-monitor',{'app.kubernetes.io/name':'vmagent'})
pod(names[1],'monitor',{'app.kubernetes.io/name':'vmagent'})
pod(names[1],'wrong-label',{})
pod(names[2],'wrong-namespace-app',{'networking.platform/caller':'approved'})
print(json.dumps({'apiVersion':'v1','kind':'List','items':items}))
PY
for ns in "$target_ns" "$monitor_ns" "$other_ns"; do
  kubectl -n "$ns" wait pod --all --for=condition=Ready --timeout=180s >/dev/null
done
protected_ip=$(kubectl -n "$target_ns" get pod protected -o jsonpath='{.status.podIP}')
unselected_ip=$(kubectl -n "$target_ns" get pod unselected -o jsonpath='{.status.podIP}')
probe() {
  kubectl --request-timeout=10s -n "$1" exec "$2" -- \
    wget -q -T 2 -O - "http://$3:$4/" 2>/dev/null | grep -q policy-test-ok
}
assert_access() {
  local expected="$1" description="$2" ns="$3" client="$4" ip="$5" port="$6"
  local successes=0
  # Require three consecutive results, including for denial, to allow policy propagation.
  for attempt in {1..15}; do
    # Ensure an exec/API failure cannot masquerade as a network-policy denial.
    kubectl --request-timeout=10s -n "$ns" exec "$client" -- true >/dev/null
    local actual=deny
    if probe "$ns" "$client" "$ip" "$port"; then actual=allow; fi
    if [[ "$actual" == "$expected" ]]; then successes=$((successes+1)); else successes=0; fi
    if [[ "$successes" -ge 3 ]]; then echo "PASS $expected: $description"; return; fi
    sleep 1
  done
  echo "FAIL expected $expected: $description" >&2
  return 1
}
# Establish that denial later cannot be attributed to an absent listener or broken network.
assert_access allow 'baseline application port' "$target_ns" denied "$protected_ip" 8080
assert_access allow 'baseline monitoring port' "$monitor_ns" wrong-label "$protected_ip" 9090
assert_access allow 'baseline other namespace' "$other_ns" wrong-namespace-app "$protected_ip" 8080
kubectl kustomize "$template_dir/restricted-ingress" | sed \
  -e "s/namespace: applications/namespace: $target_ns/g" \
  -e "s/kubernetes.io\/metadata.name: applications/kubernetes.io\/metadata.name: $target_ns/g" \
  -e "s/kubernetes.io\/metadata.name: observability/kubernetes.io\/metadata.name: $monitor_ns/g" \
  | kubectl apply -f - >/dev/null
assert_access allow 'approved application caller' "$target_ns" approved "$protected_ip" 8080
assert_access allow 'approved monitoring caller' "$monitor_ns" monitor "$protected_ip" 9090
assert_access deny 'same namespace, missing caller label' "$target_ns" denied "$protected_ip" 8080
assert_access deny 'right app label, wrong namespace' "$other_ns" wrong-namespace-app "$protected_ip" 8080
assert_access deny 'right monitoring namespace, wrong label' "$monitor_ns" wrong-label "$protected_ip" 9090
assert_access deny 'right monitoring label, wrong namespace' "$target_ns" wrong-namespace-monitor "$protected_ip" 9090
assert_access deny 'approved app caller, wrong destination port' "$target_ns" approved "$protected_ip" 9090
assert_access deny 'monitor cannot use application port' "$monitor_ns" monitor "$protected_ip" 8080
kubectl -n "$target_ns" exec protected -- nslookup kubernetes.default.svc.cluster.local >/dev/null
echo 'PASS: outgoing DNS remains available'
assert_access allow 'unselected destination unaffected' "$target_ns" denied "$unselected_ip" 8080
kubectl kustomize "$template_dir/namespace-default-deny" | sed \
  -e "s/namespace: applications/namespace: $target_ns/g" | kubectl apply -f - >/dev/null
assert_access deny 'namespace baseline isolates unselected destination' "$target_ns" denied "$unselected_ip" 8080
assert_access deny 'ingress allow alone cannot bypass caller egress deny' "$target_ns" approved "$protected_ip" 8080
assert_access allow 'explicit monitoring allow survives namespace baseline' "$monitor_ns" monitor "$protected_ip" 9090
# The namespace baseline also selects the approved caller. Open its outbound
# connection explicitly; destination ingress remains governed by the template.
cat <<POLICY | kubectl apply -f - >/dev/null
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: approved-test-caller-egress
  namespace: $target_ns
spec:
  podSelector:
    matchLabels:
      networking.platform/caller: approved
  policyTypes: [Egress]
  egress:
  - to:
    - podSelector:
        matchLabels:
          networking.platform/ingress: restricted
    ports:
    - protocol: TCP
      port: 8080
POLICY
assert_access allow 'explicit ingress and egress allows survive namespace baseline' "$target_ns" approved "$protected_ip" 8080
echo 'PASS: all ingress policy checks; removing temporary namespaces'
