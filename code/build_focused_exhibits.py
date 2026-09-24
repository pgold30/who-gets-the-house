"""Render the complete bounded validation sequence without selected-case CIs."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'results/focused_validation.json').read_text());G=ROOT/'paper/generated'
labels={'reference':'Main reference','drop_top_positive_influence_60':'Omit 60 largest positive influences',
        'joint_record_consistency_restrictions':'Joint record-consistency safeguards',
        'exclude_ambiguous_source_dates':'Omit ambiguous source dates',
        'exclude_financed_without_positive_amount':'Omit missing positive loan amounts',
        'joint_safeguards_and_source_checks':'Joint safeguards and source checks'}
borough={'1':'Manhattan','2':'Bronx','3':'Brooklyn','4':'Queens'}
rows=[]
for row in D['fits']:
    name=row['specification'];label=labels.get(name)
    if label is None:
        if name.startswith('drop_top_absolute'):label='Omit top '+name.split('_')[-1]+' absolute influences'
        elif name.startswith('leave_borough'):label='Omit '+borough[name.split('_')[2]]
        else:label='Omit ZIP '+name.split('_')[-2]
    rows.append(f"{label} & {row['pairs']:,} & {100*row['pi_joint']:.2f} & {100*(row['pi_joint']-D['reference']['pi_joint']):+.2f} \\\\")
tex=r'''\begin{table}[htbp]\centering\small
\caption{Focused house validation: influence, geography and source consistency}\label{tab:focusedvalidation}
\begin{tabular}{lrrr}\toprule
Restriction & Pairs & Contrast & Change \\
\midrule
'''+ '\n'.join(rows)+r'''
\bottomrule\end{tabular}
\notes{Log points. Every row refits the joint switch model and all nuisance controls on its retained sample. Parcels, not single observations, are removed in the influence exercises. Absolute- and positive-influence exclusions are selected using the fitted outcome; they are diagnostics, not alternative preferred samples, and ordinary confidence intervals would not account for that selection. Geographic and source restrictions also change the estimation population. The three ZIPs are selected by pair count. Combined safeguards require stable financing windows, unique amount-consistent deeds at both endpoints and no broad institutional-name flag. Source checks additionally remove ambiguous parcel/date records and financed endpoints without positive recorded loan amounts. These are internal consistency restrictions, not validated classifications. The complete model outputs and nominal parcel intervals are retained in the replication files.}
\end{table}
'''
(G/'focused_validation.tex').write_text(tex)
byname={v['specification']:v for v in D['fits']}
macros={'FocusedJoint':byname['joint_safeguards_and_source_checks']['pi_joint'],
        'FocusedTopSixty':byname['drop_top_absolute_influence_60']['pi_joint'],
        'FocusedPositive':byname['drop_top_positive_influence_60']['pi_joint']}
(G/'focused_numbers.tex').write_text('\n'.join('\\newcommand{\\'+k+'}{'+f'{100*v:.2f}'+'}' for k,v in macros.items())+'\n')
print('Focused validation table and macros built.')
