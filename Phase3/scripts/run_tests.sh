#!/usr/bin/env bash
#
# run_tests.sh
# Automates running the unit test suite for the Microgeneration Readiness Advisor
# and prints a short summary of how many tests passed and failed.
#
# Filters and features shown here
#   variables      SCRIPT_DIR, PROJECT_ROOT, PY, TEST_FILE, LOG
#   pipe           pytest output is piped into tee, grep, and awk
#   grep           pulls the result lines out of the log
#   awk            tallies the passed and failed counts and formats the summary
#   sed            trims the pytest node path down to a readable test name
#
# Run it with
#   bash Phase3/scripts/run_tests.sh
#   PYTHON=python3 bash Phase3/scripts/run_tests.sh   (override the interpreter)

set -u

# ---- variables ----
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"   # Phase3/scripts up to the repo root
PY="${PYTHON:-python}"                            # allow override with the PYTHON env var
TEST_FILE="test_advisor.py"
LOG="$SCRIPT_DIR/last_test_run.log"

echo "Project root is $PROJECT_ROOT/backend"
echo "Running $TEST_FILE with $PY"
echo

cd "$PROJECT_ROOT/backend" || { echo "Cannot enter the backend directory"; exit 1; }

# Run the suite once. 2>&1 folds warnings into the same stream so grep sees everything,
# and tee keeps a full log while still showing output live.
"$PY" -m pytest "$TEST_FILE" -v 2>&1 | tee "$LOG"

echo
echo "================ SUMMARY ================"

# grep pulls the per test result lines, awk tallies them by their status word.
grep -E "PASSED|FAILED|ERROR" "$LOG" \
  | awk '{ for (i = 1; i <= NF; i++)
             if ($i == "PASSED" || $i == "FAILED" || $i == "ERROR") count[$i]++ }
         END { printf "Passed %d, Failed %d, Errors %d\n",
                      count["PASSED"], count["FAILED"], count["ERROR"] }'

# Show any failing test names, with the long pytest path trimmed away by sed.
FAILS="$(grep -E "FAILED" "$LOG" | sed -E 's/.*::([A-Za-z0-9_]+::[A-Za-z0-9_]+).*/\1/')"
if [ -n "$FAILS" ]; then
  echo "Failing tests"
  echo "$FAILS" | sed 's/^/  /'
else
  echo "No failing tests"
fi

# Pull the final pytest status line, for example 8 passed in 0.12s, and clean the equals signs.
grep -E "passed|failed|error" "$LOG" | tail -1 | sed -E 's/=+//g' \
  | awk '{ $1 = $1; print "Pytest reported " $0 }'
