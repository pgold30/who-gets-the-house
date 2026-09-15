"""Audit the co-op counting rule; unit/borrower identity remains unvalidated."""
import json,re,collections,bisect,datetime as dt
from pathlib import Path
import numpy as np,pandas as pd
from analyze_repeat_sales import time_design,estimate
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data';OUT=ROOT/'results'

def day(s):return dt.date.fromisoformat(s[:10]).toordinal()
def unit(s):
    a=(s.get('apartment_number') or '').strip().upper()
    if not a:
        address=s.get('address') or ''
        a=address.split(',',1)[1].strip().upper() if ',' in address else ''
    return ' '.join(a.split())
def count(ds,lo,hi):return bisect.bisect_right(ds,hi)-bisect.bisect_left(ds,lo)
def make_pairs(rows):
    out=[];by=collections.defaultdict(list)
    for r in rows:by[r['unit_key']].append(r)
    for key,ss in by.items():
        ss=sorted(ss,key=lambda s:(s['day'],s['price']))
        for a,z in zip(ss,ss[1:]):
            if z['day']-a['day']>=1095:out.append((a,z))
    return out
def analyze_pairs(pairs,method,tag):
    recs=[]
    for a,z in pairs:
        if not(a['eligible'] and z['eligible']):continue
        fa=a.get(method);fz=z.get(method)
        if fa not in [0,1] or fz not in [0,1]:continue
        recs.append({'bbl':a['bbl'],'borough':a['bbl'][0],'date_a':dt.date.fromordinal(a['day']),'date_z':dt.date.fromordinal(z['day']),'y':np.log(z['price']/a['price']),'financed_base_a':fa,'financed_base_z':fz})
    df=pd.DataFrame(recs)
    if len(df)<100:return {'tag':tag,'method':method,'pairs':len(df),'status':'too few pairs'}
    _,df['cluster']=np.unique(df.bbl,return_inverse=True)
    cf=((df.financed_base_a==0)&(df.financed_base_z==1)).sum();fc=((df.financed_base_a==1)&(df.financed_base_z==0)).sum()
    if min(cf,fc)<20:return {'tag':tag,'method':method,'pairs':len(df),'cf':int(cf),'fc':int(fc),'status':'too few switchers'}
    r,_,_,_=estimate(df,time_design(df),df.cluster.max()+1)
    return {'tag':tag,'method':method,**r}

def main():
    raw=json.loads((DATA/'coop_sales_all.json').read_text());seen=set();sales=[];audit=collections.Counter()
    for r in raw:
        b=str(r.get('bbl') or '');u=unit(r)
        try:p=float(r.get('sale_price') or 0);d=day(r['sale_date'])
        except (ValueError,KeyError):audit['bad_price_date']+=1;continue
        if len(b)!=10:audit['bad_bbl']+=1;continue
        key=(b,u,d,p)
        if key in seen:audit['exact_duplicate_rows']+=1;continue
        seen.add(key)
        eligible=300000<p<6000000 and dt.date(2016,1,1).toordinal()<=d<=dt.date(2025,12,31).toordinal() and b[0]!='5' and bool(u)
        sales.append({'bbl':b,'unit_key':b+'|'+u,'unit_known':bool(u),'day':d,'price':p,'eligible':eligible})
    master={r['document_id']:day(r['recorded_datetime']) for r in json.loads((DATA/'coop_inic_master.json').read_text()) if r.get('recorded_datetime')}
    parcels=collections.defaultdict(set)
    legals_p = DATA/'coop_legals.json'
    if not legals_p.exists() and (DATA/'coop_legals.json.gz').exists():
        import gzip
        legals_raw = json.loads(gzip.decompress((DATA/'coop_legals.json.gz').read_bytes()))
    else:
        legals_raw = json.loads(legals_p.read_text())
    for r in legals_raw:
        did=r['document_id']
        if did not in master:continue
        try:b=f"{int(r['borough'])}{int(r['block']):05d}{int(r['lot']):04d}"
        except (ValueError,KeyError):continue
        parcels[did].add(b)
    filings=collections.defaultdict(list)
    for did,bb in parcels.items():
        if len(bb)==1:filings[next(iter(bb))].append((master[did],did))
    for b in filings:filings[b].sort()
    by=collections.defaultdict(list)
    for s in sales:by[s['bbl']].append(s)
    methods=['legacy_expanded','expanded_all_competitors','unique_strict','unique_base','unique_wide']
    counts=collections.defaultdict(collections.Counter);mapping=[];claim_usage=collections.Counter()
    for b,ss in by.items():
        dates=sorted(s['day'] for s in ss);legacy_dates=sorted(s['day'] for s in ss if s['eligible'])
        ff=filings.get(b,[]);fd=[x[0] for x in ff]
        for s in ss:
            if not s['eligible']:continue
            d=s['day'];k=count(legacy_dates,d-45,d+45);ka=count(dates,d-45,d+45);m=count(fd,d-60,d+135)
            s['legacy_expanded']=0 if m==0 else 1 if m>=k else -1
            s['expanded_all_competitors']=0 if m==0 else 1 if m>=ka else -1
            diag={'bbl':b,'unit_key':s['unit_key'],'sale_day':str(dt.date.fromordinal(d)),'legacy_k':k,'all_sales_k':ka,'expanded_m':m,'extra_competitors':ka-k}
            for name,lo,hi in [('unique_strict',-15,30),('unique_base',-15,90),('unique_wide',-15,180)]:
                left=bisect.bisect_left(fd,d+lo);right=bisect.bisect_right(fd,d+hi);nf=right-left
                # A filing is uniquely attributable by timing only if no other
                # observed co-op sale of ANY price/unit completeness can claim it.
                nc=count(dates,fd[left]-hi,fd[left]-lo) if nf==1 else None
                label=0 if nf==0 else 1 if nf==1 and nc==1 else -1
                s[name]=label
                if name=='unique_base':
                    diag.update(base_candidate_filings=nf,base_filing_competing_sales=nc,base_unique_candidate_document_id=ff[left][1] if nf==1 else "")
                    if label==1:claim_usage[ff[left][1]]+=1
            for name in methods:
                counts[name][str(s[name])]+=1;diag[name]=s[name]
            mapping.append(diag)
    assert max(claim_usage.values(),default=0)<=1,'reused supposedly unique filing'
    pd.DataFrame(mapping).to_csv(OUT/'coop_assignment_audit.csv.gz',index=False)
    eligible=[s for s in sales if s['eligible']]
    # Hold adjacency fixed before deleting ambiguous financing observations.
    # Known-unit sales outside the analysis band also block false repeat pairs.
    pairs=make_pairs([s for s in sales if s['unit_known'] and s['bbl'][0]!='5'])
    estimates=[]
    for method in methods:estimates.append(analyze_pairs(pairs,method,'adjacent_all_observed_unit_sales'))
    # Reconstruct original code's ordering to isolate the effect of bridging
    # an intervening sale after dropping ambiguous financing observations.
    legacy_classified=[s for s in eligible if s['legacy_expanded']>=0]
    oldpairs=make_pairs(legacy_classified)
    estimates.append(analyze_pairs(oldpairs,'legacy_expanded','legacy_drop_then_pair'))
    sameband=make_pairs(eligible)
    estimates.append(analyze_pairs(sameband,'legacy_expanded','pair_eligible_band_before_classification'))
    oldkeys={(a['unit_key'],a['day'],z['day']) for a,z in oldpairs}
    properkeys={(a['unit_key'],a['day'],z['day']) for a,z in pairs}
    pd.DataFrame([{k:v for k,v in x.items() if not isinstance(v,list)} for x in estimates]).to_csv(OUT/'coop_estimate_sensitivity.csv',index=False)
    (OUT/'coop_estimate_sensitivity.json').write_text(json.dumps(estimates,indent=2))
    ma=pd.DataFrame(mapping)
    summary={'raw_sales':len(raw),'deduplicated_valid_sales_all_prices':len(sales),'eligible_four_borough_sales':len(eligible),'missing_unit_all_sales':sum(not s['unit_known'] for s in sales),'exclusions':dict(audit),'inic_master_records':len(master),'inic_single_parcel':sum(len(v) for v in filings.values()),'inic_multi_parcel':sum(len(v)>1 for v in parcels.values()),'classification_counts':{k:dict(v) for k,v in counts.items()},'legacy_financed_to_unique_base':pd.crosstab(ma.legacy_expanded,ma.unique_base).to_dict(),'legacy_financed_without_any_base_window_filing':int(((ma.legacy_expanded==1)&(ma.base_candidate_filings==0)).sum()),'sales_with_competitors_omitted_by_old_sample_filter':int((ma.extra_competitors>0).sum()),'old_repeat_pairs_bridging_intervening_observed_unit_sale':len(oldkeys-properkeys),'maximum_unique_filing_reuse':max(claim_usage.values(),default=0),'validation_status':'Timing-uniqueness and internal-consistency audit; no verified borrower-to-buyer or filing-image match. Zero filings is absence of a matched record, not proven cash financing. Not a verified loan-level classification.','data_vintage':'Fresh public extract; may differ from archived estimates because of data updates, deduplication, geography and adjacency restrictions.'}
    (OUT/'coop_classification_audit.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)
    for r in estimates:print(r,flush=True)
    print('DONE',flush=True)
if __name__=='__main__':main()
