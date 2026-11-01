# Native workload primitives — 2026-11-01

Added `infrastructure/primitives/deployment` as an independently selectable
native Deployment base. An internal HTTP Service is opt-in at
`deployment/opt-in/service`. No namespace or chart source is implicitly selected.
The deployment includes a pinned starter image, resource requests/limits, probes,
rolling updates and non-root/read-only security settings. Applications must
replace starter-specific image/arguments/probes and choose their own sizing.

Validation passed: 133 repository Kustomize builds and the existing run/DAG
checks. A temporary two-application composition (API with Service, worker without)
built successfully. Assertions confirmed distinct names and immutable selector
labels, matching Deployment/pod selectors, namespace transforms, and that the
optional Service selected only the API workload via the named HTTP port.
No playground was created; runtime startup, traffic and rollout behavior have
not been tested for this new primitive.

The primitives README documents candidates rather than deploying them: Job,
CronJob, StatefulSet, DaemonSet, standalone Service, HTTPRoute, HPA, PDB,
NetworkPolicy, ServiceAccount/RBAC, configuration references and PVC. Job and
CronJob are the recommended next additions.
