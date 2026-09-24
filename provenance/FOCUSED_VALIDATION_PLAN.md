# Focused validation plan

22 September 2026. Written before inspecting the new influence rankings or fitting these restrictions. This is an internal plan, not preregistration.

Keep the final full-control 6,006-pair sample and 9.25-log-point estimand as the reference. Compute observation weights for the joint half-difference by residualizing the two switch indicators against the existing nuisance design. Check exact reconstruction of the reported coefficient from those weights and outcomes. Aggregate influences by parcel and refit after excluding the top 1, 5, 10, 30 and 60 parcels in absolute influence. Also drop the 60 parcels with largest positive influence. These are data-dependent diagnostics, not preferred estimates or conventional post-selection confidence intervals.

Refit leaving each borough out and each of the three largest ZIP groups out. Refit with the intersection of existing safeguards: stable financing labels at both endpoints, unique amount-consistent deeds at both endpoints, and no broad institution-name flag. These are internal consistency restrictions, not truth labels; changed samples change the population. Report all planned fits, including unhelpful results.

Check uniqueness and consistency of endpoint merges against the archived house panel, exact price-growth reconstruction, date spacing, switch counts, missingness, financing-window nesting and source mortgage-amount coverage. Review saved operative-instrument findings only within their existing evidentiary limits. The archived house panel has no mortgage-document identifiers, so its financing flags cannot independently validate purchase-loan linkage.

For transparent condition/selection sensitivity, compute the minimum uniform adverse pair-outcome perturbation needed to reduce the coefficient by half or to zero for the 10, 30, 60 and 120 parcels with largest absolute coefficient-weight sums. Perturb each selected outcome against its coefficient-weight sign, holding labels and design fixed. This is a deliberately adversarial mathematical scenario, not a model of financing misclassification, a data correction, or an estimated error rate.

Prepare a probability sample of 20 cash-to-financed and 20 financed-to-cash pairs, selected using seed 20260922. Prepare a separate targeted set from the ten most influential parcels. The reviewer-facing file excludes prices, price growth, algorithm financing flags, switch direction and influence rank; an analyst key preserves selection probabilities and strata. Review both endpoints and allow verified purchase financing, verified relevant distress, conflicting or insufficient evidence. No-match is not verified cash. Human independence cannot be supplied by an AI review or by assigning the same records to another model.

## Audit-triggered additions

Source inspection found ten analysis pairs with multiple house records on an endpoint parcel/date, and three financed endpoints without positive recorded mortgage amounts. Report separate exclusions and their intersection with existing safeguards. These additions were triggered by source-consistency findings, not an attempt to choose favorable coefficients; they are not part of the original pre-fit plan. Add the missing-amount pairs to the targeted review queue, separately from probability sampling. Missing amounts are not proof that a financing flag is false.
