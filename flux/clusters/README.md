# One Flux configuration per playground run

The former iximiuz-labs and iximiuz-platform examples have been removed. Each
new playground gets a fresh folder containing only that run's namespace/source
selection, workloads, lab overrides, readiness gates and Flux sync path. Keep
completed run folders as reproducible records; never reuse one for a new play.

After starting a playground, generate its folder from the repository root:

```sh
run_dir=$(python3 flux/runbooks/scripts/new-validation-run.py \
  --name sonarqube-postgresql --play-id PLAY_ID \
  --namespace quality --namespace databases \
  --source cloudnative-pg --source sonarqube)
```

Replace PLAY_ID with the actual ID (lowercase). Folder timestamps use
Europe/Istanbul and include the play ID suffix. The helper creates a foundation
and a GitRepository/root Flux Kustomization pointing at that exact folder.
Add the needed release wrappers and dependency/health gates before publishing.
The generator refuses an existing folder instead of overwriting a prior run.

Push the configuration to both remotes before bootstrapping it:

```sh
flux/runbooks/scripts/bootstrap-flux.sh "$run_dir"
```

The helper requires kubectl/Flux and an explicit run path. Shared Flux 2.10.0
controller manifests live under bootstrap/flux-system; each run supplies its own
sync objects. The defaults use the public GitHub repository on main. Private
sources require credentials provisioned outside Git.

Record the play ID, tested revision, findings, run status and teardown in the
run metadata/report. Publish findings to both remotes, then destroy the unused
playground. Do not retain a stopped playground. Validation checks every saved
run's sync path, dependency DAG, selected namespaces/sources and release/DB
health-check coverage, rather than assuming a fixed example folder.
