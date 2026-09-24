# Deed-image review of the same-surname flag: AI-assisted, confirmed by the author

**Status:** all 60 queued deeds are read. The author confirmed every reading and suggestion on 24 September 2026, and the confirmed classification is in `clearly_non_arms_length`.

**Result:**
- **Flagged deeds:** 16 of 40 show a non-market sign on the RP-5217NYC (40%, Wilson 95% CI 26–55%). Adding the 9 "possible" cases gives 62% (47–76%).
- **Unflagged cash deeds:** 2 of 20 (10%, 3–30%).

Self-declared conditions are a lower bound, so these shares are too.

## Sample
The queue was prepared by the independent audit (`ASTRA_AUDIT_2026-09-24_V3/deed_review_queue.csv`, seed 20260924). It holds 40 flagged deeds and 20 unflagged cash deeds, all from the headline house sample.

## Method
1. **Download.** Every page of each recorded document came from the public ACRIS image service (`GetImage`): 684 TIFF pages in `images/` (not redistributed; re-download with download.py). Downloads were paced and retried after rate limiting. Each file was checked to be a TIFF, and one deed with duplicated pages was downloaded again.
2. **Text.** macOS Vision OCR (`tools/ocr`) produced the text in `ocr/`. From the cover page it takes the first grantor and grantee addresses and the NYC and NYS transfer-tax amounts (`tools/parse_cover.py`).
3. **Form reading.** Every deed contains an **RP-5217NYC** real property transfer report. Its "Full Sale Price" (item 12) and its conditions of transfer (item 14) were read visually from crops (`crops/`).
   - Item 14's conditions include A, "Sale between relatives or former relatives"; C, "One of the buyers is also a seller"; and E, "Deed type not warranty or bargain and sale".
   - Four boxes cut off by the crop were re-read on enlarged images.
4. **Cross-check.** The NYS transfer tax (0.4% of consideration, or 0.65% at $3M or more) implies the taxed consideration.
   - It matches the form price for most deeds.
   - Where it does not, both values are recorded and the case is marked "unclear". It is not resolved.

## Files
- `deed_review_readings.csv`: the audit queue with its reading fields filled in and the author's confirmation recorded, plus:
  - `rp5217_conditions`, `rp5217_full_sale_price`, `nys_transfer_tax`, and the buyers and sellers on the form;
  - an `ai_suggestion_non_arms_length` column.

  The columns `clearly_non_arms_length`, `human_reviewer` and `human_confirmation_date` hold the author's confirmation.
- `readings.jsonl`: the raw per-deed readings.
- `cover_parse.json`: the OCR-derived cover-page fields.
- `REVIEW.html`: every reading beside its RP-5217 crop.

## Tallies (AI-assisted readings, confirmed by the author)

| | Flagged (40) | Unflagged (20) |
|---|---|---|
| Box A ticked (sale between relatives) | 13 | 1 |
| Box C ticked (buyer also a seller) | 7 | 0 |
| AI suggestion: likely not at arm's length | 16 | 2 |
| AI suggestion: possible | 9 | — |
| AI suggestion: unclear | 1 | 2 |
| AI suggestion: no indication on the form | 14 | 16 |

The four suggestion rows use these rules:
- **Likely:** a declared condition (box A, C or E), or a $0 price with $0 transfer taxes.
- **Possible:** a flagged deed with no declared condition but a shared cover-page address, or a buyer who is also listed as a seller.
- **Unclear:** the form price and the tax-implied consideration disagree.
- **No indication:** none of the above.

## Cautions
- **Item 14 is self-declared.** Several flagged deeds tick "None" although, by name, the buyer is also a seller or the parties look related (for example "Acevedo" to "Acevedo Jr."). Declared conditions are therefore a lower bound.
- **A $0 price is not always a gift.** Some forms show $0 while transfer taxes were paid on a positive consideration.
- **Some flags are coincidences.** At least one flagged deed shares only a common surname among seven parties (HOSSAIN); the strict flag drops it.
- **The surname flag has false negatives.** One unflagged deed declares a sale between relatives whose surnames differ.
- **Reading errors are possible.** Low-resolution scans are marked in the legibility notes.
