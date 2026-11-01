path "kv/data/infrastructure/velero/velero/s3" {
  capabilities = ["read"]
}

# Only lifecycle operations on this client's own short-lived token.
path "auth/token/lookup-self" {
  capabilities = ["read"]
}
path "auth/token/renew-self" {
  capabilities = ["update"]
}
path "auth/token/revoke-self" {
  capabilities = ["update"]
}
