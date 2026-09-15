"""Explicit sensitivity to missing parcel ids, repeated tuples and property type."""
import json
import numpy as np,pandas as pd
from analyze_notches import ROOT,REP,OUT,PLACEBOS,logratio

def contrasts(df,label):
    df=df.copy();df['year']=pd.to_datetime(df.date).dt.year
    key=df.bbl.fillna('MISSING_BORO_'+df.borough.astype(str));_,df['cluster']=np.unique(key,return_inverse=True)
    diffs={}
    for X in PLACEBOS+[1000000,2000000,3000000]:
        a,ai=logratio(df,X,df.year.between(2016,2018));b,bi=logratio(df,X,df.year.between(2020,2025));diffs[X]=(b['log_ratio']-a['log_ratio'],bi-ai)
    out=[]
    for X in [1000000,2000000,3000000]:
        d=diffs[X][0]-np.mean([diffs[p][0] for p in PLACEBOS]);i=diffs[X][1]-np.mean([diffs[p][1] for p in PLACEBOS],axis=0);se=float(np.linalg.norm(i))
        out.append({'sample':label,'sales':len(df),'threshold':X,'difference_in_log_ratios':d,'se':se,'ci_low':d-1.96*se,'ci_high':d+1.96*se})
    return out

if __name__=='__main__':
    full=pd.read_csv(REP/'4_full_pipeline/sample_2016_2025.csv.gz',dtype={'bbl':str,'borough':str}).rename(columns={'sale_price':'price','sale_date':'date'})
    missing=full.bbl.isna();out=contrasts(full[~missing],'nonmissing_parcel_ids')
    out+=contrasts(full[~missing].drop_duplicates(['bbl','date','price']),'collapse_identical_stored_tuples_sensitivity_only')
    panel=pd.read_csv(REP/'2_reproduce/panel2.csv.gz',dtype={'bbl':str,'borough':str});panel=panel[panel.borough!='5']
    out+=contrasts(panel,'four_borough_matched_panel')
    for typ,ss in panel.groupby('src'):out+=contrasts(ss,'four_borough_'+typ)
    pd.DataFrame(out).to_csv(OUT/'notch_sample_sensitivity.csv',index=False)
    (OUT/'notch_missingness_note.json').write_text(json.dumps({'missing_bbl':int(missing.sum()),'repeated_bbl_date_price_tuples':int(full.duplicated(['bbl','date','price']).sum()),'treatment':'Original density counts retained. Missing BBL rows are clustered together within borough. Nonmissing-only results and tuple-collapse sensitivity are also reported.','caution':'Identical BBL/date/price tuples can be different co-op units; the archived density sample lacks unit identifiers. Tuple collapse is a sensitivity exercise, not verified deduplication.'},indent=2))
    print(pd.DataFrame(out).to_string(index=False),flush=True)
