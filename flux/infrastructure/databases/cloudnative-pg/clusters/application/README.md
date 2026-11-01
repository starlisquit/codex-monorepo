# Application PostgreSQL cluster

The template includes the platform's server and replication TLS Secret
references. Reconcile the CloudNativePG operator, storage and
`infrastructure/certificates/pki/postgresql` before this cluster, with health
checks for the issued certificates. The certificate bundle requires the
platform workload issuer. The iximiuz overlay already provides these gates.

Consumers only override actual differences, such as storage capacity,
instance count or alternative certificate names. The default is 20Gi per
instance on ceph-block; the lab keeps its 1Gi capacity override locally.
This directory does not generate certificate private keys or bypass readiness.
