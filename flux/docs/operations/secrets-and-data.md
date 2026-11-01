# Secrets, initialization, and data ownership

OpenBao was initialized **once**, with five shares and threshold three. The same
unseal material was used for all three joined Raft replicas. Do not initialize
each Pod as an independent cluster. Retry-join is not auto-unseal.

For this lab, initialization output was saved under
`/home/laborant/.config/codex-platform/openbao-init.json` on `dev-machine`, with
mode 0600 in an owner-only directory. It includes the root token and all shares.
That is convenient lab custody, not a production separation of duties. The
values were not printed or committed. Move recovery material to an approved
independent secure location before treating the data as important. Do not paste
it into issue comments, documentation, command output, or Git.

External Secrets authenticates using a short-lived Kubernetes service-account
token. Its namespaced role is bound to `external-secrets-openbao` in `secrets`,
with the `openbao` audience and a read-only policy for `kv/data/lab/*` and related
metadata. The verification value is deliberately non-sensitive. The root token
is not copied into a Kubernetes Secret for External Secrets.

The initial policies, auth configuration and verification KV value were configured
through the API; the SecretStore, service account, token-review RBAC and
ExternalSecret are Git-managed. Both halves are required on recreation. The
[OpenBao runbook](../../runbooks/bootstrap/04-openbao-and-external-secrets.md)
explains that operational boundary.

cert-manager owns the OpenBao TLS Secrets. Clients trust the CA certificate, not
the server private key. Verify certificates after renewal and arrange the
appropriate OpenBao reload; changing a mounted Secret is not proof that every
process has reloaded it. CA rotation also affects injected workloads.

PostgreSQL, Ceph, NATS, and OpenBao replication do not protect against all logical
deletions or loss of the playground. Configure and test independent PostgreSQL
backups, Ceph data protection, and OpenBao Raft snapshots before relying on them.
Neither Git nor an owner-only initialization file is a database backup.
