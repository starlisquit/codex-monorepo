# Repository reorganization — 2026-11-01

- Removed `flux/MONITORING.md`; existing links now point to the monitoring
  findings or the OpenBao bootstrap procedure as appropriate.
- Moved `flux/runbooks` to `flux/docs/runbooks`, including examples and helper
  scripts. Updated commands, Markdown links and AGENTS.md. The moved Python
  validator and run generator now resolve the Flux root one directory higher.
- Moved NUI from `infrastructure/broker/nui` to `infrastructure/ui/nui`.
  This is a folder move: its broker namespace, credential references, chart,
  values and startup script are preserved.
- Removed `infrastructure/proxy/nginx` and its unused standalone Helm source
  `infrastructure/sources/nginx`, including the root source-bundle entry and
  current template/version listings. Historical verification evidence and
  isolated NGINX test fixtures remain as records of their original runs.

Validation passed: 163 Kustomize builds and all four retained run dependency,
namespace/source and readiness-coverage checks. The moved run generator was
exercised in an isolated temporary filesystem and emitted the correct run/sync
paths. Moved Python and shell helpers passed syntax checks; no newly broken
local Markdown links were introduced. No playground was needed for these
repository path changes.
