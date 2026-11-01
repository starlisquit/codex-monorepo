# Recurring log error review — 2026-11-01

A 30-minute container-log query ending around 06:35 UTC grouped error/fatal
records by namespace, container and exact message. These are log-record counts,
not distinct incidents or failed requests: a single request timeout often emits
several errors. Findings are a dated snapshot, not live cluster health.

| Pattern | Observed count | Assessment |
| --- | ---: | --- |
| kube-apiserver: Unhandled Error | 1095 | Relevant. Sample `err` values show Handler timeout, response-write failures and post-timeout context cancellation. The generic message hides the actual cause in `err`. |
| kube-apiserver: Unable to authenticate the request | 75 | Relevant to availability. Samples show `[invalid bearer token, context canceled]`; cancellation is evidence of failed request processing, not proof of stolen credentials or a persistent bad token. |
| PostgreSQL: Error collecting user query | 61 | Historical recovery failures in this window. Samples show a missing local PostgreSQL socket while a replica was restarting, not invalid SQL. Zero matching records in the last five minutes. |
| kube-apiserver: Timeout or abort while handling | 33 | Relevant and consistent with the API timeout cluster above. |
| Metrics Server: webhook authorizer request cancelled | 15 | Relevant downstream symptom: SubjectAccessReview calls to the Kubernetes API were cancelled. Do not disable authorization to hide this. |
| Controllers: lease-lock/reconciler errors | Several groups | Samples include API deadline errors; consistent with control-plane interruption. Examine actual `error`/`err` fields before treating each group as an independent fault. |

In a subsequent five-minute sample, API-server Unhandled Error still had 86
records, authentication errors 14, and request timeouts/aborts 10. Metrics Server
still reported authorizer cancellations. This is not solely stale bootstrap noise.
The API `/readyz` nevertheless returned `ok` and PostgreSQL reported all three
instances healthy at the check; instantaneous readiness does not rule out
intermittent stalls. These logs alone do not establish whether CPU, memory,
root-disk I/O or another cause is responsible. Existing resource-pressure findings
remain relevant, but a fresh performance investigation would be needed to assign
cause to this interval.

Synthetic `severity simulation fatal` records come from the intentionally deployed
log-severity test Job and are expected test data. Exclude its service/Pod when
assessing real failures; a severity label alone does not establish impact.

The log viewer now disables message wrapping and inline label display. Timestamp
and expandable log details remain available. Inspect `err`, `error`, namespace,
Pod and node there; the recurring-message table groups exact `_msg` values and can
therefore combine multiple causes behind a generic title such as Unhandled Error.
