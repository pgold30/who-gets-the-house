#!/usr/bin/env bash
# Stages 1-3. No network, no downloads. Needs python3 and numpy.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
hr(){ printf '\n%s\n%s\n%s\n' "$(printf '=%.0s' {1..78})" "  $1" "$(printf '=%.0s' {1..78})"; }

hr "1. Internal consistency  (no data, no network)"
( cd 1_verify && $PY verify_manuscript_numbers.py | tail -3 )

hr "2. Headline estimates    (offline, included data)"
( cd 2_reproduce && $PY rerun_nosi.py | grep -E "panel excluding|36m (all|permit-free|permitted)" )
echo "  -- compare against nosi_results.json --"

hr "3. Section 4.9           (offline, cached lookups)"
( cd 3_section4.9 && $PY asymmetry_composition.py | grep -E "^  (all|REO|non-REO|arms balanced) " )
( cd 3_section4.9 && $PY reo_mechanism_test.py | grep -E "lender is the FIRST|no lender either" )

hr "Done"
echo "  Stage 4 (full rebuild from the public APIs) is not run here."
echo "  See README.md and 4_full_pipeline/code/fetch_public_data.sh."
