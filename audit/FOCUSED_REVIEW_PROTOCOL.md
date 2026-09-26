# Independent house-instrument review

This queue is prepared, not completed. An AI reading of instruments may assist retrieval, but must not be described as independent human verification.

Give the reviewer **focused_blinded_house_review.csv**. Do not give them **focused_review_ANALYST_KEY.csv**, regression outputs or price changes until adjudication is complete. The source deeds may reveal consideration; blinding removes it from the queue, not from underlying legal records. Both endpoints of each pair are listed. Current loan IDs are absent from the archived panel and must be retrieved from genuine source records.

The analyst key distinguishes a random sample of 20 pairs in each financing-switch arm from targeted high-influence and missing-amount cases. Targeted cases cannot be used to estimate population error rates. The probability sample represents those switch arms in the final house sample, not unchanged-financing pairs or all NYC sales. Use recorded inclusion probabilities for any weighted summaries and report intervals appropriate to the stratified pair sampling. Do not count two endpoints as independent draws.

For each endpoint:

1. Read the deed's operative pages, parties, consideration, transfer type and parcel description. Record instrument ID and page references. A bank name or DEED cover code alone does not establish foreclosure or REO status.
2. Search ACRIS real-property legals for the parcel and join candidate documents to the master and parties around the purchase date. Check the existing narrow/base/wide matching windows against the code. Trace original financing, assignments and consolidations rather than assuming every nearby mortgage is purchase financing.
3. Inspect candidate operative mortgage pages: borrower/buyer identity, collateral parcel, transaction timing, stated purpose and any consolidation, assignment or satisfaction relationship. A positive principal is not by itself proof of a purchase-money loan.
4. Record one financing disposition: **supported purchase financing**, **documented alternative explanation/conflict**, or **insufficient evidence**. Absence of a match does not verify cash or rule out other financing. Record distress separately: foreclosure conveyance, lender resale after documented acquisition, other documented special transfer, no affirmative distress evidence, or unresolved.
5. Save the source URL, actual pages, rationale and reviewer identity. Have a second reader adjudicate conflicts or uncertain cases where feasible. Preserve all original labels alongside reviewed evidence.

Do not manufacture an error rate from a few convenient cases. If the bounded review remains incomplete, report its exact completion and leave the main labels unchanged. Do not silently relabel an unresolved sale as cash. If verified errors affect repeat pairs, document the rule, apply corrections consistently, rerun affected fits and regenerate the manuscript and release hashes before submission.

The inherited four-case instrument pilot remains separate. Existing AI-assisted readings do not count as newly completed independent cases in this queue.

The analyst key (`focused_review_ANALYST_KEY.csv`) is not in the public v3.2 archive, so that reviewers cannot see the answers. Its SHA-256 is `c57075d1462c944cd784f1b7ad44b2c2c71c9708bc7011e73ad9de84723c0ca0`. `code/focused_validation.py` regenerates the same file deterministically from the archived inputs and seeds, so anyone can confirm the key after the review. Earlier archives (v3.1) did include it; reviewers are asked not to open any package or repository for this paper until both sheets are locked.
