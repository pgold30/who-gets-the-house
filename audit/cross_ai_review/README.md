# Cross-AI review of the 106-endpoint house queue (v3.3)

The original protocol (`audit/FOCUSED_REVIEW_PROTOCOL.md`) called for two human readers; this version uses two independent AI readings instead.

| File | What it is |
|---|---|
| `house_readings_chatgpt.csv` | ChatGPT's reading of the deed and candidate mortgages for every endpoint: financing and distress codes, mortgage ID, borrower and collateral match, purpose, pages, source links, rationale and the three price sources (deed recital, RP-5217, ACRIS index). Corrections made after the second check are included. |
| `reread_notes_chatgpt.md` | Page-level notes for the five endpoints sent back for a second look (H003-z, H004-a, H027-a, H040-z, H045-a). |
| `opendata_check_claude.csv` | Claude's check of every endpoint against ACRIS open data: deed type, amount and date, parties, and every mortgage on the parcel from 15 days before to 90 days after the sale, with flags. |
| `sensitivity_timing.csv` | Sensitivity: H027-a (loan 25 days after the transfer) and H050-z (two-lot development loan) treated as unknown purpose. |

The readings were locked (SHA-256 recorded) before `audit/focused_review_ANALYST_KEY.csv` was opened. `code/cross_ai_review.py` scores them and refits the headline model without the pairs that carry a documented error. The deed and mortgage images were opened one at a time in an ordinary browser session; ACRIS does not allow automated capture.
