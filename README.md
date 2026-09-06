# Replication — *Who Gets the House?*

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22421851.svg)](https://doi.org/10.5281/zenodo.22421851)

Pablo Loschi. Companion to *Who Gets the House? Execution Certainty, the
Mortgage Recording Tax, and the Design of Transfer Taxes in New York City*.

Every input is public, free, and needs no licence, key, account, or fee.

**Requirements:** Python 3.9+ and `numpy`. Nothing else. Stages 1–3 need no
downloads; the analysis panel and the permit records are included.

```bash
bash run_all.sh          # stages 1-3, about four minutes
```

---

## The four stages, in increasing cost

| | What it does | Needs | Time |
|---|---|---|---|
| **`1_verify/`** | Re-derives every number the paper states | nothing | 5 s |
| **`2_reproduce/`** | Re-estimates the headline results | included data | 3 min |
| **`3_section4.9/`** | Re-runs the buyer-identity and REO analyses | included caches | 1 min |
| **`4_full_pipeline/`** | Rebuilds everything from the raw public APIs | network, ~30 GB | hours |

Stage 1 alone establishes that the paper is arithmetically consistent. Stage 2
establishes that its headline numbers come out of its data. Most readers will
not need stages 3 or 4.

### 1. Verify — no data, no network

```bash
cd 1_verify
python3 verify_manuscript_numbers.py    # 170 internal-consistency checks
python3 verify_public_counts.py         # 5 live record counts, downloads nothing
```

`verify_manuscript_numbers.py` re-derives every stated quantity from the
primitives the paper also states: each π̂ and asymmetry recomputed from its arm
means, the record linkage closing in both denominators, the π\* grid, the
decomposition, the notch arithmetic. `verify_public_counts.py` issues five
`count(1)` queries against NYC Open Data to confirm the sources exist at the
sizes claimed.

### 2. Reproduce the headline estimates — offline

```bash
cd 2_reproduce
python3 rerun_nosi.py      # Sections 4-5: the four-borough estimates
python3 pistar_model.py    # Section 5.1: the pi* grid and its inversion
```

`rerun_nosi.py` is **the script whose numbers are in the paper**: 8,208 house
pairs at π = 0.1114, permit-free 6,316 at 0.0934 with A = −0.0183. Its output
should match `nosi_results.json` exactly.

`permit_test.py` is also here and **does not** produce the published table. Run
alone it reports 14,527 pairs at 0.1176 — the twenty-four-month, five-borough
version written before the ACRIS coverage boundary was found. It is correct for
what it is, and it is kept because the difference between the two is
instructive.

### 3. Section 4.9 — buyer identity and the REO finding

```bash
cd 3_section4.9
python3 buyer_identity_split.py     # the split by buyer type
python3 asymmetry_composition.py    # where the asymmetry actually comes from
python3 reo_mechanism_test.py       # the deed-in-lieu mechanism, four tests
python3 check_unresolved_skew.py    # do the discarded pairs resemble the kept?
```

The deed and grantee lookups are cached (`deeds_for_pairs.json`,
`grantees_main.json`), so these run offline. Delete the caches to re-query ACRIS
Parties live; that takes about thirty minutes.

**Run `check_unresolved_skew.py` on any match you rely on.** It compares the
observations a match discarded against the ones it kept, and it is what caught a
silent Socrata truncation during this work that had cost half of Brooklyn.

### 4. Full pipeline — from the raw APIs

```bash
cd 4_full_pipeline/code
bash fetch_public_data.sh      # ~30 GB, several hours
```

Then retrieval → linkage → estimation in the order given in Appendix C of the
Supplemental Appendix. `output/` holds every result JSON, so any stage can be
checked without re-running the ones before it.

---

## Two retrieval traps, both real, both encountered here

**Page on an indexed column and assert the count.** ACRIS Legals holds 22.7M
rows and Socrata truncates silently at `$limit`. Worse, the table stores **one
row per (document, parcel)**, so a `document_id > last` cursor skips the
remaining rows of any multi-parcel document. Both bugs occurred during this
work, both were silent, and both were caught only by checking a page total
against an exact `count(1)`. `3_section4.9/buyer_identity_split.py` shows the
pattern that works.

**The 2016 building-class string.** Calendar year 2016 writes the category with
a double space after the two-digit code (`01  ONE FAMILY DWELLINGS`); 2017
onward use one. A filter on the full literal string silently drops all of 2016 —
the earliest pre-treatment year for the notch design — and manufactures a
before-and-after difference out of a formatting change. Match on the two-digit
code.

## Sources

| Resource | Contents |
|---|---|
| `w2pb-icbu` | DOF annualized calendar sales, 2016–2025 |
| `bnx9-e6tj` | ACRIS Real Property Master |
| `8h5j-fqxa` | ACRIS Real Property Legals |
| `sv7x-dduq` | ACRIS Personal Property Master (`INIC` share loans) |
| `uqqa-hym2` | ACRIS Personal Property Legals |
| `636b-3b5g` | ACRIS Real Property Parties (grantee names) |
| `7isb-wh4c` | ACRIS Document Control Codes |
| `ipu4-2q9a` | DOB Permit Issuance |
| CFPB HMDA data browser | Application dispositions, five NYC counties |

Seeds are `20260903` throughout.

## Licence

**Code** (`*.py`, `*.sh`) — MIT.

**Derived data and documentation** (`panel2.csv.gz`, `dob_permits.csv.gz`,
`sample_2016_2025.csv.gz`, the result JSONs, this README) — CC-BY-4.0.

**The underlying source data** are public records published by the City of New
York and the Consumer Financial Protection Bureau, and carry no licence of
mine. The compilations above are derived from them; they are licensed
explicitly rather than assumed to be in the public domain, because a database
compiled in the EU can attract a sui generis right even where its inputs do
not.

Attribution: cite the paper, or this deposit by its DOI.
