#!/bin/sh
set -eu

# NUI v0.10.0 parses absent localStorage entries as null, discarding defaults.
# Apply the source-level null defaults to the served bundle for every client.
# Refuse unknown bundles so image upgrades cannot silently drop the fix.
for key in docs-state cards-all cards-deck-uuid cards-drawer-uuid links-menu-uuid logs; do
  default='[]'
  [ "$key" != docs-state ] || default='{"drawerPosition":"right"}'
  needle='JSON.parse(localStorage.getItem(`'"$key"'`))'
  patched="($needle??$default)"
  count=0
  for bundle in /frontend/dist/assets/index-*.js; do
    if grep -qF "$patched" "$bundle"; then
      count=$((count + 1))
    elif grep -qF "$needle" "$bundle"; then
      sed -i "s/$needle/($needle??$default)/g" "$bundle"
      grep -qF "$patched" "$bundle"
      count=$((count + 1))
    fi
  done
  if [ "$count" -ne 1 ]; then
    echo "NUI session-default patch failed for $key: expected one bundle, found $count" >&2
    exit 1
  fi
done
# The empty KV bucket API returns null; the UI store otherwise spreads null
# when the first bucket is created. Normalize the pinned store's list response.
needle='n.setAll(r),await Su.actions.fetch(e,t)'
patched='n.setAll(r??[]),await Su.actions.fetch(e,t)'
count=0
for bundle in /frontend/dist/assets/index-*.js; do
  if grep -qF "$patched" "$bundle"; then
    count=$((count + 1))
  elif grep -qF "$needle" "$bundle"; then
    sed -i "s/$needle/$patched/g" "$bundle"
    grep -qF "$patched" "$bundle"
    count=$((count + 1))
  fi
done
if [ "$count" -ne 1 ]; then
  echo "NUI empty-bucket patch failed: expected one bundle, found $count" >&2
  exit 1
fi
exec /entrypoint.sh --proto-schemas-path=/db/protoschemas --cddl-schemas-path=/db/cddlschemas "$@"
