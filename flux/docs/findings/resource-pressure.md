# Resource-pressure diagnosis — 2026-11-01

The API investigation was resumed at the user's request after the earlier pause.
Read-only node, Pod, Flux, kernel-counter, and VictoriaMetrics checks established
real capacity failures. No load-pause experiment was performed, so these findings
do not isolate a single application as the sole cause of every API timeout.

## Evidence

| Check | Recorded result |
| --- | --- |
| Allocatable node RAM | `5014156Ki` each, about 14.35 GiB across the three nodes |
| Nonterminal workload memory requests | About 15.90 GiB total |
| Already scheduled requests | 4.77 GiB on control plane, 4.56 GiB on node-01, 4.78 GiB on node-02 |
| Unscheduled requests | About 0.50 GiB PostgreSQL and 1.29 GiB demo |
| Demo namespace requests | About 5.11 GiB |
| Rook/Ceph namespace requests | About 5.61 GiB |
| Scheduler errors | PostgreSQL replica and demo services: `Insufficient memory`; one node also lacked requested CPU |
| Evictions | KEDA operator, fraud-detection, and MCP Pods evicted for low ephemeral storage |
| System disks | 20 GiB each; worker snapshots at 78% and 82% used; eviction records showed free space below the roughly 3 GiB threshold |
| CPU behavior | node-01 around 59–66% I/O wait; node-02 around 84% idle and little I/O wait |
| Root-disk reads | Roughly 34 MiB/s on control plane, 58 MiB/s on node-01; Ceph `vdb` devices lightly utilized |
| Major page faults | Roughly 630–690/s on control plane/node-01 during one sample |
| Node-level OOM-kill counters | No increases in the last 30-minute query window |
| API request latency | About 5.6s p99 in one three-minute histogram query |
| Controller termination | cert-manager cainjector previous log explicitly reported `leader election lost` |

The exact counters are snapshots. Node Ready/MemoryPressure=False/DiskPressure=False
were also observed later: those conditions do not negate earlier evictions or
requests that cannot fit. Linux available RAM and Kubernetes memory requests are
different measures; some available RAM does not make reserved capacity schedulable.

## Interpretation

The lab is overcommitted for the entire stack, with both scheduling-memory and
system-disk capacity problems. High load averages here include disk waits; they
do not establish that all CPU cores are saturated. The pattern is consistent
with heavy root filesystem reads and file-backed page/cache churn. Ceph's raw
OSD disks were not the busy devices in these samples. Node-level OOM kills were
not established, and controller exit code 1 must not be relabeled as OOM.

Nine demo Pods remained on the control plane in the captured snapshot. The
worker-only Git change had not replaced those running Pods. Flux child
Kustomizations showed older applied revisions or dependency/in-progress states;
a root Git revision does not mean every workload already runs those values.
API slowness and leader-election failures can then delay the very reconciliations
intended to reduce pressure.

The initial deployment packed too much into the lab. Increasing the control-plane
share in future definitions redistributes the same total node RAM; it does not
solve the total capacity deficit. Larger system disks and more total node RAM,
or a smaller workload set, are needed for a comfortable full-stack environment.

## Requested mitigation

The user chose to shrink the **shared template**, not only the lab overlay.
Only currency, quote, and a small Collector remain enabled; Kafka, browser load,
storefront, AI services, and other demo services are explicitly disabled. The
Collector no longer watches Kubernetes or scrapes removed dependencies.

The new demo requests 176Mi RAM total rather than about 5.1 GiB, a reduction of
roughly 4.9 GiB in requested capacity. It has no automatic traffic generator.
The rendered desired state has exactly three workload controllers under both
Helm 3 and Helm 4. Post-change runtime/API improvements must be checked after
Flux completes the upgrade; this record does not predeclare that outcome.
