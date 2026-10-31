#!/usr/bin/env bash
# commit-msg hook: prefix the message with the DIN-n id found in the branch name.
msg_file="$1"
branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
id="$(printf '%s' "$branch" | grep -oE 'DIN-[0-9]+' | head -1)"
[ -z "$id" ] && exit 0
grep -qE 'DIN-[0-9]+' "$msg_file" && exit 0
printf '%s %s\n' "$id" "$(cat "$msg_file")" > "$msg_file"
