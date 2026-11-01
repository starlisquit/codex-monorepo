path "kv/data/infrastructure/ai/litellm/auth" {
  capabilities = ["read"]
}
path "kv/data/infrastructure/ai/litellm/providers" {
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
