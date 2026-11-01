# Infrastructure ESO: GitLab Runner and Renovate

**Passed.** Fresh K3s playground `6ae7a6d27f32053bde2c2902`, created alongside
three other focused runs. Flux path:
`flux/clusters/20261101-235338-infra-eso-ci-2c2902`.
Application checks completed **2026-11-02 00:06:47 Europe/Istanbul**
(2026-11-01 21:06:47 UTC). Policy fix: `b394d1e`; final reconciled configuration: `de6fab5`.
All selected Flux stages and HelmReleases were Ready at final capture.

## Real service results

- The GitLab Runner and Renovate stores/ExternalSecrets authenticated against
  actual OpenBao. Both target Secrets matched every provider property and were
  owned by their respective ExternalSecret.
- Runner chart0.94.2/runner19.5.2 used `ci/gitlab-runner-auth`. ESO's template
  supplied its authentication token and the required empty registration-token
  field. Temporary project runner **58230510** became online and executed a real
  job through the Kubernetes executor.
- [Pipeline3015371114](https://gitlab.com/basarsubasi-gitops/kubernetes/flux/-/pipelines/3015371114),
  job **17648206882**, succeeded on that exact runner. The temporary validation
  branch contained only a small CI smoke job and did not change main.
- Effective manager TOML retained **concurrent=5** and runner-local **limit=5**.
  This run confirms configured limits; the previous six-job concurrency test was
  not repeated and no new measured five-way-overlap claim is made.
- Renovate chart46.396.0/app44.198.0 loaded `RENOVATE_TOKEN` from
  `ci/renovate-credentials`. A manual Job completed an authenticated clone/scan of
  the actual GitLab repository, emitted its extraction summary and finished the
  repository successfully. Existing **dryRun: full** remained enabled: no merge
  request or dependency-update branch was created.
- Own-path reads succeeded; unrelated KV access and wrong token audiences were
  rejected for both scoped service-account identities.

## Policy correction and limitations

Initial infrastructure policies disabled OpenBao's default policy but omitted
self-token permissions required by ESO. Live provider validation failed with
HTTP403 at `auth/token/lookup-self`. All nine policies were corrected in
`b394d1e` to permit only the caller's own token lookup/renew/revoke, retaining
exact-path, read-only KV access. Both CI integrations passed after application of
those real backend policy changes; routine validation now covers the missing
permission contract.

GitLab refused creation of a dedicated read-only project access token (HTTP400).
The already-authorized PAT was used solely inside this disposable read-only
Renovate run and never committed. It is not represented as a newly scoped bot
token. The runner used a separately minted temporary authentication token.
Renovate retains GitHub lookup warnings because no GitHub token was provided;
this does not invalidate its authenticated GitLab repository scan.

[Sanitized evidence](evidence/infra-eso-ci-2026-11-01.json) records credential
hashes, scopes tested, pipeline/job/runner IDs, configured concurrency, successful
Renovate processing and actual chart versions. Raw token values, private logs and
OpenBao recovery material remain outside Git. K3s `v1.37.1+k3s1`, OpenBao2.7.2,
ESO2.14.0 and the centrally trusted TLS setup were used. One 1Gi lab OpenBao replica
is not an HA/recovery test. Evidence distinguishes propagation of later report/
other-lane source revisions from the tested workload revision.

## Teardown

Findings/configuration were published to both remotes in
`2cef441f92244cdac89314d1bd3e041706e4bcbf` before teardown.
Destroy API confirmed playground destruction at `2026-11-01T21:12:08Z`.
GitLab confirmed runner and validation-branch deletion with **HTTP204** each.
The existing user PAT was not rotated or revoked.
