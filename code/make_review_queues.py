"""Instrument-review queues with stratum weights; does not invent adjudication."""
from pathlib import Path
import pandas as pd,json
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'results'
x=pd.read_csv(R/'coop_assignment_audit.csv.gz',dtype={'bbl':str,'base_unique_candidate_document_id':str})
x['stratum']=x.unique_base.map({-1:'ambiguous',0:'no_filing',1:'timing_unique'})
parts=[]
for label,g in x.groupby('stratum'):
    z=g.sample(n=min(30,len(g)),random_state=20260910).copy();z['stratum_population']=len(g);z['selection_probability']=len(z)/len(g);z['inverse_probability_weight']=len(g)/len(z);parts.append(z)
z=pd.concat(parts);z['instrument_unit_match']='UNREVIEWED';z['borrower_purchase_match']='UNREVIEWED';z['evidence_url']='';z['reviewer']=''
z.to_csv(R/'coop_instrument_review_queue.csv',index=False)
# Add weights and known document URLs to the reproducibly sampled distress queue.
h=pd.read_csv(ROOT/'data/house_pairs_enriched.csv.gz',dtype={'bbl':str});ep=[]
for side in ['a','z']:
    t=h[['bbl',f'date_{side}',f'buyer_lender_high_{side}',f'seller_lender_high_{side}',f'buyer_lender_broad_{side}',f'seller_lender_broad_{side}']].copy();t.columns=['bbl','date','bh','sh','bb','sb'];ep.append(t)
t=pd.concat(ep).drop_duplicates(['bbl','date']);t['stratum']='unflagged';t.loc[t.bb|t.sb,'stratum']='broad_only';t.loc[t.bh|t.sh,'stratum']='specific_institution';counts=t.stratum.value_counts()
d=pd.read_csv(R/'distress_adjudication_queue.csv',dtype={'bbl':str,'deed':str});n=d.stratum.value_counts();d['stratum_population']=d.stratum.map(counts);d['selection_probability']=d.stratum.map(n)/d.stratum_population;d['inverse_probability_weight']=1/d.selection_probability;d['document_url']=d.deed.map(lambda s:'https://a836-acris.nyc.gov/DS/DocumentSearch/DocumentImageView?doc_id='+s if isinstance(s,str) else '')
d.to_csv(R/'distress_adjudication_queue.csv',index=False)
(R/'review_queue_status.json').write_text(json.dumps({'distress_sample':len(d),'distress_reviewed':0,'coop_sample':len(z),'coop_reviewed':0,'seed':20260910,'status':'Queues and sampling weights complete; no ground-truth accuracy claim.'},indent=2))
print('Saved both 90-record weighted instrument-review queues; all ground-truth labels remain UNREVIEWED.')
