# Decision: lead with the financing-gap evidence

Version WGTH-2026-09-10-F1 makes the cumulative financing-associated house price gap the central contribution. The abstract, introduction, literature positioning and conclusion now follow that question. The detailed co-op audit and tax-notch analysis move to appendices. The main claim is descriptive and conditional: observed transaction controls do not explain the entire house contrast. It is not a causal estimate of mortgage-tax incidence or execution risk.

This is a substantive scope decision, not a claim that the reform identification is solved. The $2 million result remains useful supplementary evidence. Promoting it to the lead would require both a better counterfactual and a sharper incremental contribution relative to the existing transaction-tax literature.

## Bounded comparison-market screen, 10 September 2026

| Candidate | What the screen establishes | Decision |
|---|---|---|
| Westchester and Nassau | Outside the NYC-specific 2019 additional taxes; NY SalesWeb documents downloadable transactions outside NYC. | Best candidates for a future empirical check, not validated controls. |
| Nearby Connecticut markets | Public transaction data are available, but Connecticut added a marginal conveyance-tax bracket above $2.5m from July 2020. | Do not use the unchanged 2020–2025 placebo design: its $2.5m comparison price would itself be affected by another tax reform. A redesigned, narrower exercise could still be possible. |
| Nearby New Jersey markets | New graduated transfer fees took effect in July 2025, including thresholds near those studied in NYC. | Do not pool all 2020–2025 as an untreated period. Earlier years remain potential comparisons, not verified ones. |

Sources checked:

- [NY State 2019 reform memorandum](https://www.tax.ny.gov/pdf/memos/real_estate/m19-1r.pdf): NYC-specific additional base and supplemental taxes.
- [NY SalesWeb documentation](https://www.tax.ny.gov/research/property/assess/sales/salesweb.htm): ten years of non-NYC transfers, grouped downloads, 3,000-result search limit and reporting lags. Availability is documented; no county transaction file was obtained. The webpage/application access attempts did not yield a usable extract in this bounded run. This does not establish that public access is unavailable.
- [Connecticut DRS tax-change notice](https://portal.ct.gov/drs/legislative-summaries/2019-legislative-updates/real-estate-conveyance-tax-change): 2.25% marginal rate above $2.5m beginning July 2020. This is a marginal-bracket change, not an NYC-style jump in total liability.
- [Connecticut public sales dataset](https://data.ct.gov/widgets/5mzw-sjtu?mobile_redirect=true): public sales source identified; not downloaded.
- [New Jersey July 2025 notice](https://www.nj.gov/treasury/taxation/pdf/lpt/GraduatedPercentFeeNotice.pdf): new graduated rates, statutory payer change and transitional refund provisions.

## What was not established

No external-market counts, pre-trend estimates, common-support results or treatment effects were computed. Lack of statistical significance in the existing within-NYC pre-period tests does not establish parallel trends with a county outside NYC. This is a legal/data-availability screen, not a completed empirical feasibility test.

An efficient next empirical screen would obtain only annual local-window counts and property-type composition for Nassau and Westchester, initially 2016–2019. Restrict both NYC and counties to harmonised houses/condominiums; co-op coverage is a separate issue. Examine sample size and pre-reform changes before obtaining wider periods. Keep both counties in the report rather than selecting whichever produces a desirable post-reform result. Residential sorting and tax-induced cross-border substitution could invalidate a nearby control even with good pre-trend fit.

## Work and resource boundary

No additional instrument images were reviewed. No full data download, raw-panel reconstruction, bootstrap rerun or new environment was performed. Existing estimates and all previous robustness outputs are retained. The focused paper does not claim an improved causal counterfactual, and this revision does not itself justify raising the prior 7.5/10 assessment.

The first journal target remains Journal of Housing Economics. The narrower framing makes the contribution easier to evaluate; publication prospects still depend on novelty, measurement and an independent assessment of the design. No acceptance probability is asserted.

## Reproduction and versioning

Keep this directory beside TARGETED_REVISION_2026-09-10 and PUBLICATION_RELEASE_2026-09-10. F1 changes framing and organisation only. Its estimates are those of the frozen release and T1 supplement; neither earlier archive alone represents F1.

From their parent directory:

```sh
PUBLICATION_RELEASE_2026-09-10/clean_run/venv/bin/python FOCUSED_REVISION_2026-09-10/code/build_focused.py
tectonic -X compile FOCUSED_REVISION_2026-09-10/manuscript/paper.tex --outdir FOCUSED_REVISION_2026-09-10/output/pdf --keep-logs
```

The F1 supplement contains the focused manuscript source/PDF, this decision record and a manifest. It requires the existing release and T1 supplement for the underlying analyses. Nothing was submitted, uploaded or published.
