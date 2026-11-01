# sonarqube-postgresql validation run

Playground `6ae765f67f32053bde237f3e`. Flux reconciles only `./flux/clusters/20261101-191654-sonarqube-postgresql-237f3e`.
Add only the workloads and readiness gates needed for this run. Keep credentials
outside Git. Record findings, push both remotes, then destroy the playground.
Never reuse this folder for a new playground.

This run deployed through Flux and verified a real scanner analysis, browser
login/dashboard, strict JDBC TLS and analysis persistence after application/DB
recovery. See [findings](../../docs/findings/sonarqube-postgresql-2026-11-01.md)
and run.json for the tested revision and teardown state. The scanner manifest
under validation is a manual one-shot fixture, excluded from root reconciliation;
its token Secret remains outside Git.
