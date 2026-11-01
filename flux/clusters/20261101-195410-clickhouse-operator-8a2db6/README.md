# clickhouse-operator validation run

Playground `6ae76eb246471e13268a2db6`. Flux reconciles only `./flux/clusters/20261101-195410-clickhouse-operator-8a2db6`.
Add only the workloads and readiness gates needed for this run. Keep credentials
outside Git. Record findings, push both remotes, then destroy the playground.
Never reuse this folder for a new playground.

Verified cert-manager, official ClickHouse operator, Keeper-backed SQL and PVC
persistence after ClickHouse pod replacement. See
[findings](../../docs/findings/clickhouse-operator-2026-11-01.md).
The workload is a small non-HA validation fixture, not production sizing.
