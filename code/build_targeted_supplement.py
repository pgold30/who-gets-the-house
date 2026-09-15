"""Package a four-case image review and existing targeted results; no downloads.

Review labels below are AI-assisted readings of saved visible ACRIS pages,
not automated classifier outputs or independent human adjudications.
"""
from pathlib import Path
import csv, json, hashlib, shutil
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT
REVIEWER='AI-assisted image review; independent human review pending'
URL='https://a836-acris.nyc.gov/DS/DocumentSearch/DocumentImageView?doc_id='
cases=[
 dict(kind='house',document_id='2023051600851001',bbl='3082410041',sale_day='2023-05-10',stratum='broad_only',finding='lender_resale_after_foreclosure_acquisition',
 evidence=['deed_2023051600851001_p3_zoom.png','instrument_2019020500740001_p1.png','instrument_2019020500740001_p3.png','instrument_2019020500740001_p3_detail.png'],
 related_document='2019020500740001',notes='Sale deed page 3 identifies Central Mortgage/Arvest as grantor and recites the 24 January 2019 referee deed. The earlier deed page 3 conveys the same premises to Arvest pursuant to a mortgage foreclosure judgment. Supports an REO resale interpretation; does not establish condition or the causal price effect. The narrower institutional rule missed this seller, while the broad rule flagged it.'),
 dict(kind='house',document_id='2019093000695001',bbl='4102650007',sale_day='2019-09-26',stratum='specific_institution',finding='referee_deed_in_foreclosure_to_institution',
 evidence=['instrument_2019093000695001_p1.png','instrument_2019093000695001_p2_detail.png'],related_document='',
 notes='Operative page 2 is explicitly a Referee\'s Deed in Foreclosure, conveying to U.S. Bank as trustee. Cover metadata uses ordinary DEED. This is a foreclosure transfer, not an ordinary lender resale. The narrower institutional-buyer rule already excludes this case.'),
 dict(kind='coop',document_id='2025020500312001',bbl='1014060017',sale_day='2025-02-11',stratum='timing_unique',finding='collateral_unit_match_purchase_unverified',sale_unit='7AB',instrument_unit='7AB',
 evidence=['coop_2025020500312001_p1.png','coop_2025020500312001_p3.png','coop_2025020500312001_p4.png'],related_document='',
 notes='Cover and co-operative addendum identify 7AB. UCC collateral identifies shares for 7A and 7B and the proprietary lease. Unit match supported; debtor-to-buyer identity and purchase-loan purpose not independently established.'),
 dict(kind='coop',document_id='2020020400882001',bbl='3011700041',sale_day='2020-02-17',stratum='timing_unique',finding='collateral_unit_mismatch',sale_unit='1CD',instrument_unit='4E',
 evidence=['instrument_2020020400882001_p1.png','instrument_2020020400882001_p2.png','instrument_2020020400882001_p3_detail.png'],related_document='',
 notes='Preserved DOF sale identifies 1CD at $1,120,000. Cover, operative UCC collateral and addendum identify 4E in the same building. Reject the assignment of this filing to the 1CD sale; classify that sale as unresolved, not cash. Timing uniqueness fails under strict, base and wide windows here.'),
]
for c in cases:
 c.update(review_date='2026-09-10',reviewer=REVIEWER,evidence_url=URL+c['document_id'])
 c['evidence_sha256']={f:hashlib.sha256((ROOT/'audit/images'/f).read_bytes()).hexdigest() for f in c['evidence']}
(ROOT/'audit/instrument_pilot.json').write_text(json.dumps(cases,indent=2)+'\n')
pd.DataFrame([{k:v for k,v in c.items() if k not in ['evidence','evidence_sha256']} | {'evidence_files':';'.join(c['evidence'])} for c in cases]).to_csv(ROOT/'audit/instrument_pilot.csv',index=False)

# Update only the working queue copies. Sampling weights refer to the original
# 30-per-stratum queues, not to this small, selectively continued pilot.
for name,key in [('distress_adjudication_queue.csv','deed'),('coop_instrument_review_queue.csv','base_unique_candidate_document_id')]:
 frame=pd.read_csv(ROOT/'audit'/name,dtype=str).fillna('')
 for c in cases:
  ix=frame[key].eq(c['document_id'])
  if not ix.any():continue
  frame.loc[ix,'reviewer']=REVIEWER
  if c['kind']=='house':
   frame.loc[ix,'ground_truth_distress']=c['finding']
   frame.loc[ix,'image_or_court_evidence']='instrument_pilot.json; '+c['evidence_url']
  else:
   frame.loc[ix,'instrument_unit_match']='MATCH' if c['sale_unit']==c['instrument_unit'] else 'MISMATCH'
   frame.loc[ix,'borrower_purchase_match']='UNVERIFIED' if c['sale_unit']==c['instrument_unit'] else 'REJECT_LINK_UNIT_MISMATCH'
   frame.loc[ix,'evidence_url']=c['evidence_url']
 frame.to_csv(ROOT/'audit'/name,index=False)

# Establish whether the confirmed mismatch enters any known-unit repeat pair.
raw=json.loads((BASE/'data/coop_sales_all.json').read_text())
def unit(r):
 a=(r.get('apartment_number') or '').strip().upper()
 if not a:
  address=r.get('address') or ''
  a=address.split(',',1)[1].strip().upper() if ',' in address else ''
 return ' '.join(a.split())
matched=[r for r in raw if str(r.get('bbl'))=='3011700041' and unit(r)=='1CD']
keys={(r['sale_date'][:10],float(r['sale_price'])) for r in matched}
assert keys=={('2020-02-17',1120000.0)},keys
(ROOT/'audit/mismatch_estimate_impact.json').write_text(json.dumps(dict(
 source='data/coop_sales_all.json',
 source_sha256=hashlib.sha256((BASE/'data/coop_sales_all.json').read_bytes()).hexdigest(),
 matched_source_records=matched,unique_unit_sales=len(keys),repeat_pairs_involving_case=0,
 interpretation='Reject financing link; do not recode as cash. This case contributes no repeat-sales pair, so its exclusion does not alter the reported co-op repeat-sales estimates.'),indent=2)+'\n')

results=pd.read_csv(ROOT/'results/reform_period_bandwidth_checks.csv')
main=results.query('window_width==100000 and threshold in [2000000,3000000]')
labels={'baseline_2020_2025':'2020--2025','pandemic_2020_2021':'2020--2021','later_2022_2025':'2022--2025','2019_H2_season_matched':'2019 H2','2019_Q4_season_matched':'2019 Q4'}
table=[r'\begin{table}[htbp]\centering\small',r'\caption{Reform comparisons by post period}\label{tab:targetedperiods}',r'\begin{tabular}{lrrrr}\toprule',r'Post period & $\Delta_{2m}$ & 95\% interval & $\Delta_{3m}$ & 95\% interval \\ \midrule']
for key,label in labels.items():
 rr=main[main.comparison.eq(key)].set_index('threshold')
 cells=[]
 for t in [2000000,3000000]:
  a=rr.loc[t];cells.extend([f'{a.estimate:.3f}',f'[{a.ci_low:.3f}, {a.ci_high:.3f}]'])
 table.append(label+' & '+' & '.join(cells)+r' \\')
table.extend([r'\bottomrule\end{tabular}',r'\notes{Changes in log above/below price-count ratios less the mean change at four placebo prices; $100{,}000$ windows. Reference period: 2016--2018, restricted to the same calendar months for the 2019 rows. Intervals use joint parcel-cluster CR0 scores and are pointwise. The 2019 rows may include grandfathered contracts. Periods overlap; separate significance levels do not test differences between periods. All 45 period/bandwidth comparisons are retained in the supplement.}',r'\end{table}'])


(ROOT/'paper/generated/targeted_periods.tex').write_text('\n'.join(table)+'\n')
print('Instrument pilot and targeted table regenerated from supplied evidence and results.')
