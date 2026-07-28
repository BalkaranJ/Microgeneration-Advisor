#!/usr/bin/env bash
#
# project_report.sh
# Prints a structure snapshot of the Python code, the classes, the method and
# class counts per file, the totals, and the most common method names. Useful
# for documentation, reviews, and keeping the UML diagrams honest.
#
# Filters and features shown here
#   variables      SCRIPT_DIR, PROJECT_ROOT, PY_FILES, and the loop counters
#   pipe           grep results flow into sed, awk, sort, and uniq
#   grep           finds the class and def lines
#   sed            strips the keywords so only the names remain
#   awk            counts and formats the aligned table and the totals
#   sort and uniq  rank the most common method names
#
# Run it with
#   bash Phase3/scripts/project_report.sh

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT" || { echo "Cannot enter the project root"; exit 1; }

# The files we care about, held in a space separated variable used by the loops.
PY_FILES="app.py test_app.py backend/advisor.py backend/weather.py backend/main.py"

# Regex variables. The def pattern also matches async def so FastAPI endpoints count.
CLASS_RE="^[[:space:]]*class "
DEF_RE="^[[:space:]]*(async[[:space:]]+)?def "

echo "Code structure for the Microgeneration Readiness Advisor"
echo "Project root $PROJECT_ROOT"
echo

# ---- Classes grouped by file ----
echo "Classes by file"
for f in $PY_FILES; do
  [ -f "$f" ] || continue
  # grep the class lines, then sed leaves only the class name.
  grep -E "$CLASS_RE" "$f" \
    | sed -E 's/^[[:space:]]*class[[:space:]]+([A-Za-z0-9_]+).*/\1/' \
    | while read -r cls; do
        printf "  %-22s %s\n" "$f" "$cls"
      done
done
echo

# ---- Class, method, and line counts per file ----
echo "Counts per file"
printf "%-24s %8s %8s %7s\n" "file" "classes" "methods" "lines"
for f in $PY_FILES; do
  [ -f "$f" ] || continue
  classes=$(grep -cE "$CLASS_RE" "$f")
  methods=$(grep -cE "$DEF_RE" "$f")
  lines=$(wc -l < "$f" | awk '{ print $1 }')
  printf "%-24s %8s %8s %7s\n" "$f" "$classes" "$methods" "$lines"
done
echo

# ---- Totals across all files with awk ----
echo "Totals"
grep -rhE "^[[:space:]]*(class|(async[[:space:]]+)?def) " $PY_FILES 2>/dev/null \
  | sed -E 's/^[[:space:]]*//' \
  | awk '{ if ($1 == "class") c++; else d++ }
         END { printf "  %d classes and %d methods across the code\n", c, d }'
echo

# ---- Most common method names, a pipe chain with sort and uniq ----
echo "Most common method names"
grep -rhE "$DEF_RE" $PY_FILES 2>/dev/null \
  | sed -E 's/^[[:space:]]*(async[[:space:]]+)?def[[:space:]]+([A-Za-z0-9_]+).*/\2/' \
  | sort | uniq -c | sort -rn | head -5 \
  | awk '{ printf "  %2d  %s\n", $1, $2 }'
