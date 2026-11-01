# Database certificate stage

Select this base after cert-manager and `ClusterIssuer/platform-workload-ca` are
Ready. Wait for both Certificate resources before applying the parent PostgreSQL
Cluster base. It creates only server and streaming-replication leaf Certificates;
it does not install the operator, issuer, namespace or database.

Secrets include `cnpg.io/reload` labels so CNPG observes renewal. The root private
key remains in the certificates namespace. The application integration consumes
the public `platform-ca` ConfigMap supplied by trust-manager, not these private
leaf Secrets. See the parent README and runtime findings for the complete order.
