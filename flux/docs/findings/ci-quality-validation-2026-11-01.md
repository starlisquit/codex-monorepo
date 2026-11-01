# CI and quality chart verification — 2026-11-01

Focused playground: `6ae6ffdf789ac234e333b048`, official `k3s` base, started
12:01 Europe/Istanbul / 09:01 UTC. Three Kubernetes nodes reported
`v1.37.1+k3s1`, Linux `6.1.167`; the separate dev machine ran Helm `4.3.1`.
Only the three requested tools, a disposable PostgreSQL fixture and validation
Jobs were installed. No Ceph, Flux controller stack, observability stack or
security agents were deployed. Storage was K3s `local-path`, not Ceph.

Template commits: `543c7f2`, with Renovate extraction correction `1aa9a82`.
The GitHub and GitLab `main` branches are synchronized before teardown.
Credentials and generated administrator/scanner tokens remain outside Git.

## Charts and template selection

| Component | Official source | Pinned chart | Application tested |
| --- | --- | --- | --- |
| GitLab Runner | https://charts.gitlab.io | 0.94.2 | 19.5.2 |
| SonarQube | https://SonarSource.github.io/helm-chart-sonarqube | 2026.5.1003 | Community Build 26.9.0.129388, explicitly selected |
| Renovate | https://docs.renovatebot.com/helm-charts | 46.396.0 | 44.198.0 |

All are opt-in components with namespace creation, HelmRepository definitions,
HelmReleases, watch-labelled values ConfigMaps and documented Secret prerequisites.
They are not added to the unrelated full-platform overlay. The repository checker
now derives release health-check coverage from selected Kustomize resources rather
than requiring every available template to be selected in that overlay.

## Results

| Check | Status | Evidence / limits |
| --- | --- | --- |
| Repository validation | Passed | `KUSTOMIZE_BIN=/workspace/scratch/flux-setup/kustomize flux/runbooks/scripts/validate.sh`: 94 builds; 37 selected child definitions / 25 selected releases; dependency/storage checks and clean whitespace |
| Official chart lint/render | Passed | All three charts linted and rendered with repository values under Helm 3.17.0 locally and Helm 4.3.1 in the lab. Helm lint takes a downloaded chart path; `--version` belongs to pull/template/install, not lint |
| GitLab Runner installation | Passed | Helm release deployed, Deployment 1/1; effective TOML: concurrent=5, runner limit=5, executor=kubernetes, privileged=false |
| Manager rollout configuration | Passed | One replica; Recreate strategy prevents a rolling-update surge from doubling the manager count. Additional installations/replicas do not share a global five-job ceiling |
| Real GitLab job execution and concurrency | Passed | Pipeline 3014117890: six successful jobs on temporary project runner 58212324. GET /projects/88359167/pipelines/3014117890/jobs confirmed maximum timestamp overlap five; five active job Pods observed while sixth queued. Job 6 began after earlier jobs completed |
| SonarQube install / PostgreSQL | Passed | Helm release Ready; API reported UP / 26.9.0.129388; external PostgreSQL 17.6 accepted JDBC connections and contained 164 public tables; 5 GiB data PVC Bound; sysctl/filesystem init containers completed |
| SonarQube administrative/scanner credentials | Passed | Initial administrator password changed; project-scoped analysis token provisioned in a temporary Secret. No credential values recorded |
| SonarQube real analysis | Passed | Official scanner completed successfully in 29.05 s; compute task 90b60615-15c3-4da8-9cdd-1b657968b9cf SUCCESS; analysis c48e0f4e-3402-4594-920c-215c218c373d; API returned one file / four ncloc for ci-validation |
| SonarQube restart continuity | Passed | Deleted the SonarQube Pod, waited for replacement Ready, then verified API UP, the same successful compute task/analysis and one file / four ncloc. The data PVC UID was unchanged |
| Renovate schedule and credentials | Passed | CronJob 03:00 Europe/Istanbul; Forbid overlap; external Secret; explicit GitLab repository scope, autodiscover=false, dryRun=full |
| Renovate authenticated repository scan | Passed with warnings | Job renovate-complete-scan completed; repository cloned; flux manager extracted 32 entries in 32 files; result done, exitCode=0, 11.16 s repository processing. Default patterns previously found only two installation files; explicit YAML patterns corrected that |
| Renovate remaining lookup limits | Limited | GitHub token absent for fluxcd/flux2 release lookup. Cilium/Tetragon each reported repeated identical Helm registry URLs from multiple source definitions. No write-mode / MR creation claimed |
| Sustained full-platform health / production capacity | Not run | This focused test does not complete the interrupted full-platform handoff or certify production sizing |
| Production database backup/restore and TLS ingress | Not run | Test database and internal HTTP were disposable fixtures; no recovery or public TLS claim |

Runner evidence: [pipeline](https://gitlab.com/basarsubasi-gitops/kubernetes/flux/-/pipelines/3014117890).
The reusable six-job fixture is `flux/runbooks/examples/gitlab-runner-smoke.gitlab-ci.yaml`.
The temporary runner and validation branch were removed after evidence collection
(GitLab DELETE returned HTTP 204 for each). No runner authentication token is retained.

SonarQube's first analysis harness changed the password before discovering a
directory permission error. The disposable test database was reset, directory
ownership corrected, and the retry persisted credentials before changing them.
The initial scanner fixture reached 1021 MiB at its 1 GiB limit while analysis
stalled; the retry fixture uses 2 GiB. Neither adjustment changes the SonarQube
server template or weakens its bootstrap checks. Scanner image digest:
`sha256:47956b669bf486bdad919e1cbd0533223515aa0b6d1d31763e5a3754942df6d7`.

## Teardown protocol

Findings and updates were committed as `afbd35b` and verified on both remotes
before destroying the playground. The temporary GitLab runner and validation
branch were removed. At 12:17:59 Europe/Istanbul / 09:17:59 UTC, the destroy API
returned `ok: true` for play `6ae6ffdf789ac234e333b048`; subsequent listing showed
no running plays. It was destroyed, not retained in a stopped state. The earlier
full-platform playground had already been destroyed at the user's request.
