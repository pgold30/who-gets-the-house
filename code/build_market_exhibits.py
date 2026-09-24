"""Generate revised market-conditions tables solely from saved fitted results."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'results/market_conditions_extension.json').read_text()); M=D['models']; G=ROOT/'paper/generated'

def table(file, title, label, columns, rows, notes):
    text='\\begin{table}[htbp]\\centering\\small\n\\caption{'+title+'}\\label{'+label+'}\n'
    text+='\\begin{tabular}{l'+'r'*(len(columns)-1)+'}\\toprule\n'+' & '.join(columns)+' \\\\\n\\midrule\n'
    text+='\n'.join(' & '.join(row)+' \\\\' for row in rows)
    text+='\n\\bottomrule\\end{tabular}\n\\notes{'+notes+'}\n\\end{table}\n'
    (G/file).write_text(text)

rows=[]
for j, label in [(2,'First sale'),(3,'Second sale')]:
    row=[label]
    for key in ['credit','credit_trends']:
        row += [f"{100*M[key]['beta'][j]:.2f}",f"{100*M[key]['inference']['parcel']['se'][j]:.2f}"]
    rows.append(row)
table('credit.tex','Credit conditions at both sale dates','tab:credit', ['Financing $\\times$ rate','Without trends','SE','With trends','SE'],rows,
      'Log points per one percentage point of PMMS rates, centered on 4 percent; 6,006 pairs. Both models include separate uninteracted weekly rates at both endpoints, the full geographic controls and both financing-switch indicators. The second adds separate endpoint financing-specific linear calendar trends. Standard errors cluster by parcel (CR0). Appendix Table~\\ref{tab:marketconditions} reports calendar-dependence sensitivity. The headline contrast is estimated in the model without rate interactions.')

rows=[]
pformat=lambda p: '$<0.001$' if p < .001 else f'{p:.3f}'
for key, label in [('credit','Credit'),('credit_trends','Credit + trends'),('inventory','Inventory'),('inventory_trends','Inventory + trends')]:
    model=M[key]; v=model['inference']['endpoint_quarter']; vy=model['inference']['endpoint_year']
    ci=lambda j: f"[{100*v['ci_low'][j]:.2f}, {100*v['ci_high'][j]:.2f}]"
    rows.append([label,f"{100*model['beta'][2]:.2f}",ci(2),f"{100*model['beta'][3]:.2f}",ci(3),pformat(v['joint_slopes_p']),pformat(vy['joint_slopes_p'])])
# Compact column headings keep the full intervals legible on a portrait page.
table('market_conditions.tex','Historical market conditions: endpoint and trend sensitivity','tab:marketconditions',
      ['Model','First','95\\% CI','Second','95\\% CI','$p_Q$','$p_Y$'],rows,
      'All 6,006 pairs; slopes in log points. Credit unit: one percentage point of the weekly rate. Inventory unit: a doubling of prior-month borough Single Family inventory relative to its borough reference. Inventory models also include separate endpoint financing-by-borough controls (Brooklyn reference). Both indicators enter uninteracted at both dates. Intervals use the union of parcel and either-endpoint calendar-quarter score dependence and a $t_{39}$ reference. Columns $p_Q$ and $p_Y$ test both interaction slopes jointly, using calendar-quarter and calendar-year dependence respectively, with approximate $F_{2,39}$ and $F_{2,9}$ references. Negative covariance eigenvalues are set to zero: one is corrected in each quarter model with trends and in each year model. The unadjusted eigenvalues are recorded in the replication output. These are exploratory, pointwise diagnostics, not exact small-cluster inference.')
out=[]
for key in ['credit','credit_trends','inventory','inventory_trends']:
    row=M[key]
    out.append({'model':key, **{kind:row['inference'][kind] for kind in ['parcel','endpoint_quarter','endpoint_year']}})
(ROOT/'results/market_inference_summary.json').write_text(json.dumps(out,indent=2))
print('Built corrected credit and historical inventory exhibits.')
