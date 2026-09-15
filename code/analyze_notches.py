"""Common-period notch samples and paired pre/post-placebo contrasts."""
import json
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
REP=ROOT/'inputs'
THRESHOLDS=[500000,1000000,1500000,1750000,2000000,2250000,2500000,3000000]
PLACEBOS=[1500000,1750000,2250000,2500000]

def logratio(df,X,period):
    p=df.price.to_numpy();m=np.asarray(period)
    above=m&(p>=X)&(p<X+100000)
    if X==500000:above=m&(p>X)&(p<=X+100000)
    below=m&(p>=X-150000)&(p<X-50000)
    a=int(above.sum());b=int(below.sum())
    assert a and b,(X,a,b)
    influence=above/a-below/b
    cl=np.bincount(df.cluster,weights=influence,minlength=df.cluster.max()+1)
    r={'threshold':X,'above':a,'below':b,'log_ratio':float(np.log(a/b)),'ratio':a/b,'se_log_ratio':float(np.linalg.norm(cl))}
    return r,cl

def main():
    df=pd.read_csv(REP/'4_full_pipeline/sample_2016_2025.csv.gz',dtype={'bbl':str,'borough':str}).rename(columns={'sale_price':'price','sale_date':'date'})
    df.date=pd.to_datetime(df.date);df['year']=df.date.dt.year
    missing_bbl=int(df.bbl.isna().sum())
    # Retain original density counts; conservatively cluster unidentified parcels
    # together within borough, instead of treating missing records as independent.
    df['cluster_key']=df.bbl.fillna('MISSING_BBL_BORO_'+df.borough)
    _,df['cluster']=np.unique(df.cluster_key,return_inverse=True)
    # 2019 excluded entirely: avoids anticipation, transition and grandfathering.
    pre=df.year.between(2016,2018);post=df.year.between(2020,2025)
    out=[];diffs={};joint=[]
    for X in THRESHOLDS:
        r0,i0=logratio(df,X,pre);r1,i1=logratio(df,X,post)
        out.extend([{'period':'2016-2018',**r0},{'period':'2020-2025',**r1}])
        diffs[X]=(r1['log_ratio']-r0['log_ratio'],i1-i0)
    for X in [500000,1000000,2000000,3000000]:
        for controls in [PLACEBOS]+[[p] for p in PLACEBOS]:
            value=diffs[X][0]-np.mean([diffs[p][0] for p in controls]);influence=diffs[X][1]-np.mean([diffs[p][1] for p in controls],axis=0)
            se=float(np.linalg.norm(influence))
            joint.append({'threshold':X,'placebos':','.join(map(str,controls)),'difference_in_log_ratios':value,'se':se,'ci_low':value-1.96*se,'ci_high':value+1.96*se,'percent_change_relative_ratio':100*np.expm1(value)})
    pd.DataFrame(out).to_csv(OUT/'notch_prepost_counts.csv',index=False)
    pd.DataFrame(joint).to_csv(OUT/'notch_difference_in_differences.csv',index=False)
    # Annual placebo-adjusted contrasts expose pre-trends and post heterogeneity.
    annual=[]
    for year in range(2016,2026):
        rows={X:logratio(df,X,df.year==year) for X in THRESHOLDS}
        for X in [1000000,2000000,3000000]:
            r,i=rows[X];baseline=np.mean([rows[p][0]['log_ratio'] for p in PLACEBOS]);ci=i-np.mean([rows[p][1] for p in PLACEBOS],axis=0)
            annual.append({'year':year,**r,'placebo_adjusted_log_ratio':r['log_ratio']-baseline,'adjusted_se':float(np.linalg.norm(ci))})
    pd.DataFrame(annual).to_csv(OUT/'notch_annual_placebo_adjusted.csv',index=False)
    # Directly matched financing sample: EXACTLY same dates and four boroughs at
    # every threshold, with separate house/condo estimates rather than mixing types.
    panel=pd.read_csv(REP/'2_reproduce/panel2.csv.gz',dtype={'bbl':str,'borough':str})
    panel['year']=pd.to_datetime(panel.date).dt.year
    panel=panel[(panel.borough!='5')&panel.year.between(2020,2025)].copy()
    _,panel['cluster']=np.unique(panel.bbl,return_inverse=True)
    charm=[];finratio=[];counts=[]
    for typ in ['all','house','condo']:
        sub=panel if typ=='all' else panel[panel.src==typ].copy()
        for X in [500000,1000000,2000000,3000000]:
            p=sub.price.to_numpy();fin=sub.financed_base.to_numpy();g=sub.cluster.to_numpy();G=panel.cluster.max()+1
            local=(p>=X-150000)&(p<=X+150000)
            nlocal=int(local.sum())
            for window in ['strict','base','wide']:
                f=sub['financed_'+window].to_numpy()
                a=p==X-1;b=p==X;na=int(a.sum());nb=int(b.sum())
                pa=float(f[a].mean()) if na else None;pb=float(f[b].mean()) if nb else None
                if na and nb:
                    influence=a*(f-pa)/na-b*(f-pb)/nb;cl=np.bincount(g,weights=influence,minlength=G);se=float(np.linalg.norm(cl));delta=pa-pb
                else:se=delta=None
                charm.append({'type':typ,'threshold':X,'financing_window':window,'n_X_minus_1':na,'n_X':nb,'financed_share_X_minus_1':pa,'financed_share_X':pb,'difference':delta,'se_difference':se,'ci_low':delta-1.96*se if delta is not None else None,'ci_high':delta+1.96*se if delta is not None else None,'same_tax_side':X==500000,'common_period':'2020-2025','local_sales':nlocal,'small_cell':min(na,nb)<30})
            for year in range(2020,2026):
                for boro in sorted(sub.borough.unique()):
                    m=(sub.year.to_numpy()==year)&(sub.borough.to_numpy()==boro)&local
                    counts.append({'type':typ,'threshold':X,'year':year,'borough':boro,'local_sales':int(m.sum()),'financed':int(fin[m].sum()),'cash':int((1-fin[m]).sum())})
            for f in [0,1]:
                for window in ['strict','base','wide']:
                    m=sub['financed_'+window].to_numpy()==f
                    try:r,inf=logratio(sub,X,m);finratio.append({'type':typ,'financed':f,'window':window,**r})
                    except AssertionError:pass
    pd.DataFrame(charm).to_csv(OUT/'charm_common_post_reform.csv',index=False)
    pd.DataFrame(finratio).to_csv(OUT/'notch_common_post_financing.csv',index=False)
    pd.DataFrame(counts).to_csv(OUT/'notch_common_post_sample_composition.csv',index=False)
    (OUT/'notch_audit.json').write_text(json.dumps({'full_sales':len(df),'duplicate_rows':int(df.duplicated(['bbl','date','price']).sum()),'pre_2016_2018':int(pre.sum()),'post_2020_2025':int(post.sum()),'common_post_matched_sales':len(panel),'common_post_by_type':panel.src.value_counts().to_dict(),'common_post_by_year':{str(k):v for k,v in panel.year.value_counts().sort_index().to_dict().items()},'method':'log count ratios; parcel-clustered joint delta-method inference, including covariance from overlapping windows and repeated parcels','limitations':['Not a bunching welfare estimate.','Parallel evolution across threshold and placebo locations is an assumption.','National reform coincides with market changes; annual diagnostics are essential.','Financing is a record-window proxy, not randomized.','Wald charm-share intervals are exploratory and unreliable in very small cells.','Five-hundred-thousand dollars is a same-tax-side charm comparison; it cannot identify statutory payer response.']},indent=2))
    print(pd.DataFrame(joint).query("placebos == '1500000,1750000,2250000,2500000'").to_string(index=False),flush=True)
    print('DONE',flush=True)
if __name__=='__main__':main()
