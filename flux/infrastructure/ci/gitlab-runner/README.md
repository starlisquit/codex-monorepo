# GitLab Runner

Official [GitLab chart](https://gitlab.com/gitlab-org/charts/gitlab-runner),
chart `0.94.2` / Runner `19.5.2`, from `https://charts.gitlab.io`.
The component creates namespace `ci`; its HelmRepository is in `sources/gitlab.yaml`.
Select this component in your own cluster overlay after provisioning credentials.
It is intentionally not added to the full-platform overlay.

One manager replica, `concurrent: 5`, and runner-local `limit = 5` permit at most
five concurrent CI jobs in this installation. `Recreate` prevents a rolling-update
surge from briefly running two managers. Do not increase replicas or deploy another
manager with the same token and assume the five-job ceiling remains global.

Create a project/group runner in GitLab using the current runner authentication
token workflow, not a legacy registration token. Configure project scope, tags,
protected-branch access and untagged-job behavior in GitLab. Supply Secret
`ci/gitlab-runner-auth` with `runner-token` and an empty
`runner-registration-token` key. For a secure local token file outside Git:

```sh
kubectl create namespace ci --dry-run=client -o yaml | kubectl apply -f -
kubectl -n ci create secret generic gitlab-runner-auth \
  --from-file=runner-token=/secure/runner-token \
  --from-literal=runner-registration-token=
```

Namespace-scoped RBAC permits the Kubernetes executor to create job Pods and
supporting Secrets/services in `ci`; it does not grant cluster-admin. Builds are
unprivileged. Docker-in-Docker is not configured. Resource requests/limits apply
to manager, build and helper containers; tune them for actual jobs. Protect runner
credentials and restrict which projects can execute code on this runner.

Validate/deploy independently:

```sh
kustomize build flux/infrastructure/ci/gitlab-runner
helm repo add gitlab https://charts.gitlab.io
helm pull gitlab/gitlab-runner --version 0.94.2 --untar --untardir /tmp/gitlab-runner-chart
helm lint /tmp/gitlab-runner-chart/gitlab-runner -f flux/infrastructure/ci/gitlab-runner/values.yaml
helm upgrade --install gitlab-runner gitlab/gitlab-runner --version 0.94.2 \
  -n ci -f flux/infrastructure/ci/gitlab-runner/values.yaml --wait --timeout 10m
```

For Flux, include the source and component in the consuming overlay and use a
HelmRelease health check. Do not have Helm CLI and Flux manage the same release
concurrently. Verify an actual tagged pipeline, the generated config's concurrency,
and job Pod RBAC/security context. Chart readiness alone does not prove job execution.
