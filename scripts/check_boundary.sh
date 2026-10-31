#!/usr/bin/env bash
# Fail if tracked/untracked-not-ignored files contain material that must stay in ClickUp only.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
self="scripts/check_boundary.sh"
fail=0

patterns=(
  'EMAIL|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
  'ClickUp personal token|pk_[0-9]+_'
  'ClickUp form URL|forms\.clickup\.com'
  'ClickUp share URL|sharing\.clickup\.com'
  'user id (after)|user[^0-9]{0,12}[0-9]{9}([^0-9]|$)'
  'user id (before)|(^|[^0-9])[0-9]{9}[^0-9A-Za-z]{0,3}user'
)

while IFS= read -r f; do
  [ "$f" = "$self" ] && continue
  [ "$f" = "uv.lock" ] && continue
  [ -f "$f" ] || continue
  grep -Iq . "$f" 2>/dev/null || continue   # skip binary/empty
  for p in "${patterns[@]}"; do
    label="${p%%|*}"; re="${p#*|}"
    hits=$(grep -nEi -- "$re" "$f" || true)
    [ -n "$hits" ] || continue
    if [ "$label" = "EMAIL" ]; then
      hits=$(printf '%s\n' "$hits" | grep -viE '@(users\.noreply\.github\.com|example\.com)([^A-Za-z0-9.-]|$)' || true)
      [ -n "$hits" ] || continue
    fi
    while IFS= read -r h; do
      echo "boundary violation ($label): $f:${h%%:*}"
      fail=1
    done <<< "$hits"
  done
done < <(git ls-files --cached --others --exclude-standard | sort -u)

if [ "$fail" -ne 0 ]; then
  echo "check_boundary: FAILED (no tokens, e-mails, user ids or ClickUp form/share URLs in this repo)" >&2
  exit 1
fi
echo "check_boundary: ok"
