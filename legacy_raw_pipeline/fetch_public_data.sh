#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# fetch_public_data.sh — retrieval layer for "Who Gets the House?"
#
# Downloads the six public datasets the paper uses, in full, to ./data/.
# No API key or licence is required. Socrata throttles anonymous callers, so
# an app token in $SOCRATA_APP_TOKEN is used when present.
#
# This script covers RETRIEVAL ONLY. Linkage, estimation and the tables are
# produced by the scripts listed in Appendix C of the Supplemental Appendix,
# which are deposited separately with the author's analysis archive.
#
#   bash fetch_public_data.sh            # everything (large: ~30 GB, hours)
#   bash fetch_public_data.sh sales dob  # named subsets only
# ---------------------------------------------------------------------------
set -euo pipefail

DOMAIN="https://data.cityofnewyork.us/resource"
OUT="${OUT:-./data}"
PAGE="${PAGE:-50000}"
mkdir -p "$OUT"

# name : resource id : cursor column (must be unique and sortable)
DATASETS=(
  "sales:w2pb-icbu:sale_date"
  "acris_master:bnx9-e6tj:document_id"
  "acris_legals:8h5j-fqxa:document_id"
  "pp_master:sv7x-dduq:document_id"
  "pp_legals:uqqa-hym2:document_id"
  "dob_permits:ipu4-2q9a:job__"
)

hdr=(-H "Accept: application/json")
[[ -n "${SOCRATA_APP_TOKEN:-}" ]] && hdr+=(-H "X-App-Token: ${SOCRATA_APP_TOKEN}")

count_rows () {  # exact row count, so progress is meaningful
  curl -sS "${hdr[@]}" --get "$DOMAIN/$1.json" \
       --data-urlencode '$select=count(1) AS n' \
    | python3 -c 'import sys,json; print(json.load(sys.stdin)[0]["n"])'
}

fetch () {
  local name=$1 rid=$2 key=$3
  local dest="$OUT/$name.ndjson" total offset=0 got

  # Cursor paging on an indexed column, NOT $offset. Socrata degrades badly on
  # deep offsets, and the ACRIS legals table has ~22.7M rows; ordering by the
  # key and stepping keeps every page a fresh indexed scan.
  echo "==> $name  ($rid)"
  total=$(count_rows "$rid") || { echo "    count failed; skipping"; return; }
  echo "    $total rows"

  : > "$dest"
  while :; do
    got=$(curl -sS --retry 5 --retry-delay 3 --retry-all-errors "${hdr[@]}" \
          --get "$DOMAIN/$rid.json" \
          --data-urlencode "\$limit=$PAGE" \
          --data-urlencode "\$offset=$offset" \
          --data-urlencode "\$order=$key" \
        | tee >(python3 -c '
import sys, json
rows = json.load(sys.stdin)
out = open(sys.argv[1], "a")
for r in rows:
    out.write(json.dumps(r, separators=(",", ":")) + "\n")
' "$dest") | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))')
    offset=$((offset + got))
    printf "\r    %d / %d" "$offset" "$total"
    [[ "$got" -lt "$PAGE" ]] && break
  done
  printf "\r    %d / %d  done\n" "$offset" "$total"
  gzip -f "$dest"
}

# HMDA is a different API: aggregations by county, not a Socrata resource.
fetch_hmda () {
  echo "==> hmda (CFPB data browser)"
  local base="https://ffiec.cfpb.gov/v2/data-browser-api/view/aggregations"
  # Five NYC counties; 36 = New York State FIPS.
  for county in 36005 36047 36061 36081 36085; do
    for year in 2019 2020 2021 2022 2023; do
      curl -sS --retry 3 --get "$base" \
        --data-urlencode "years=$year" \
        --data-urlencode "counties=$county" \
        --data-urlencode "loan_purposes=1" \
        -o "$OUT/hmda_${county}_${year}.json" || true
    done
  done
  echo "    done"
}

want=("$@")
for spec in "${DATASETS[@]}"; do
  IFS=: read -r name rid key <<<"$spec"
  if [[ ${#want[@]} -eq 0 ]] || [[ " ${want[*]} " == *" $name "* ]]; then
    fetch "$name" "$rid" "$key"
  fi
done
if [[ ${#want[@]} -eq 0 ]] || [[ " ${want[*]} " == *" hmda "* ]]; then
  fetch_hmda
fi

echo
echo "Retrieved to $OUT. Next: the linkage and estimation scripts in"
echo "Appendix C of the Supplemental Appendix."
