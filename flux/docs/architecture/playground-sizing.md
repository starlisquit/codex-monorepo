# Playground sizing: prioritize the control plane

The control-plane VM needs more CPU and RAM than a worker or the dev machine.
It runs etcd, kube-apiserver, scheduler, and controller-manager, and in this lab
also accepted application and storage workloads because its scheduling taint
was removed by the playground. Flux, operators, CRDs, API discovery, and chart
installation generate additional API traffic during bootstrap.

The initial full-platform play requested 3 vCPUs and 5 GiB RAM for **every**
Kubernetes node. During deployment the control plane was observed at about
4 GiB used RAM, roughly 1 GiB available, and load averages above 28, while the
workers each had approximately 2.4–2.6 GiB available. Kubernetes API requests and
some guest command calls timed out. These observations support reserving more
control-plane capacity; they do not prove a single root cause for the slowdown.
That investigation was initially paused and later resumed; see the resource-pressure
findings for measured capacity failures. Do not describe the running cluster as fixed.

## Future-playground defaults

| Machine | vCPUs | RAM | System disk | Raw Ceph disk |
| --- | ---: | ---: | ---: | ---: |
| `cplane-01` | 4 | 6 GiB | 20 GiB | 25 GiB |
| `node-01` | 2 | 4608 MiB | 20 GiB | 25 GiB |
| `node-02` | 2 | 4608 MiB | 20 GiB | 25 GiB |
| `dev-machine` | 1 | 1 GiB | 10 GiB | none |

Total requested: 9 vCPUs, 16 GiB RAM, 145 GiB disks. The checked-in
[playground manifest](../runbooks/bootstrap/iximiuz-playground.yaml) and the
saved `codex-platform-243e14fd` playground definition use these defaults for
future starts. The running play was not resized or recreated by this change.

The platform's [manifest reference](https://labs.iximiuz.com/docs/custom-playgrounds/manifest-reference)
reports plan-dependent resource caps and proportional scaling when requests
exceed the budget. Its disk limits and the
[multi-drive guide](https://labs.iximiuz.com/docs/custom-playgrounds/multi-drive-vms)
currently differ; the observed 145 GiB configuration fits both documented totals.
Always inspect effective VM resources and `lsblk`; a requested size is not an
observed allocation. More RAM on the control plane necessarily reduces the worker
budget within this playground's total.

## Workload placement and limits

The demo overlay requires its services and Collector to run on workers. The
shared demo template now disables all but currency and quote, plus the Collector,
with 176Mi total requested memory and no browser load generator. See the
[resource-pressure findings](../findings/resource-pressure.md) for the measured
capacity deficit and the reason for this reduction. Local rendering validates
placement; confirm that Flux has actually replaced older running workloads.

Do not simply reapply a control-plane NoSchedule taint without configuring
storage placement and tolerations: this three-host Ceph cluster uses all three
nodes for monitor and OSD failure domains. Moving ordinary workloads off the
control plane is preferable to silently breaking the storage topology.

Monitor CPU, memory, image filesystem space, pending Pod requests, and image pull
queues during rollout. A large demo and replicated storage share the same small
VMs; a Ready HelmRelease alone does not establish sustainable capacity.
