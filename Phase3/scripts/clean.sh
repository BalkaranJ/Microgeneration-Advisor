#!/usr/bin/env bash
#
# clean.sh
# Removes Python caches, the pytest cache, and the frontend build output so the
# working tree is tidy. Pass --dry-run to preview what would be removed without
# deleting anything.
#
# Filters and features shown here
#   variables      SCRIPT_DIR, PROJECT_ROOT, DRY_RUN, TARGETS
#   flag           --dry-run switches the behaviour
#   find           locates the matching directories, skipping node_modules
#   pipe           the find results flow into grep to count them
#
# Run it with
#   bash Phase3/scripts/clean.sh --dry-run    (preview only)
#   bash Phase3/scripts/clean.sh              (actually remove)

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DRY_RUN="no"
[ "${1:-}" = "--dry-run" ] && DRY_RUN="yes"

# Directory names to clear, kept in one variable.
TARGETS="__pycache__ .pytest_cache .vite"

cd "$PROJECT_ROOT" || { echo "Cannot enter the project root"; exit 1; }

echo "Cleaning under $PROJECT_ROOT (dry run $DRY_RUN)"

for name in $TARGETS; do
  # find every matching directory, pruning node_modules so it stays fast.
  matches=$(find . -path ./frontend/node_modules -prune -o -type d -name "$name" -print)
  count=$(printf "%s\n" "$matches" | grep -c .)
  echo "  $name found $count"
  if [ "$DRY_RUN" = "no" ] && [ -n "$matches" ]; then
    printf "%s\n" "$matches" | while read -r d; do
      [ -n "$d" ] && rm -rf "$d"
    done
  fi
done

# Remove the frontend production build if it is present.
if [ -d "frontend/dist" ]; then
  echo "  frontend/dist found 1"
  [ "$DRY_RUN" = "no" ] && rm -rf "frontend/dist"
fi

echo "Done"
