"""Bounded, prespecified checks using the frozen price sample; no new raw download.

All specified outcomes are reported. Period comparisons are descriptive absent
parallel local-distribution changes; pandemic and grandfathering are explicit.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
from scipy.stats import chi2
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results';SOURCE=ROOT/'inputs/4_full_pipeline/sample_2016_2025.csv.gz'
x=pd.read_csv(SOURCE,dtype={'bbl':str,'borough':str}).rename(columns={'sale_price':'price','sale_date':'date'});x.date=pd.to_datetime(x.date);x['year']=x.date.dt.year;x['month']=x.date.dt.month
_,cl=np.unique(x.bbl.fillna('MISSING_BORO_'+x.borough),return_inverse=True);G=cl.max()+1
p=x.price.to_numpy();PLACEBOS=[1500000,1750000,2250000,2500000]
def ratio(t,m,h):
    a=np.asarray(m)&(p>=t)&(p<t+h);b=np.asarray(m)&(p>=t-1.5*h)&(p<t-.5*h)
    na,nb=int(a.sum()),int(b.sum())
    if min(na,nb)==0:raise ValueError(('empty window',t,na,nb))
    score=np.bincount(cl,weights=a/na-b/nb,minlength=G)
    return np.log(na/nb),score,na,nb

def adjusted(t,m,h):
    v,s,a,b=ratio(t,m,h)
    for q in PLACEBOS:
        z,ss,_,_=ratio(q,m,h);v-=z/4;s-=ss/4
    return v,s,a,b

periods=[('baseline_2020_2025',x.year.between(2016,2018),x.year.between(2020,2025)),('pandemic_2020_2021',x.year.between(2016,2018),x.year.between(2020,2021)),('later_2022_2025',x.year.between(2016,2018),x.year.between(2022,2025)),('2019_H2_season_matched',x.year.between(2016,2018)&x.month.ge(7),x.year.eq(2019)&x.month.ge(7)),('2019_Q4_season_matched',x.year.between(2016,2018)&x.month.ge(10),x.year.eq(2019)&x.month.ge(10))]
rows=[];pre=[]
for h in [50000,100000,150000]:
    for t in [1000000,2000000,3000000]:
        for label,before,after in periods:
            v0,s0,a0,b0=adjusted(t,before,h);v1,s1,a1,b1=adjusted(t,after,h);d=v1-v0;se=np.linalg.norm(s1-s0)
            rows.append({'threshold':t,'window_width':h,'comparison':label,'estimate':d,'se':se,'ci_low':d-1.96*se,'ci_high':d+1.96*se,'pre_above':a0,'pre_below':b0,'post_above':a1,'post_below':b1,'relative_ratio_change_percent':100*np.expm1(d),'grandfathering_unresolved':label.startswith('2019')})
        vals=[];scores=[]
        v0,s0,_,_=adjusted(t,x.year.eq(2016),h)
        for y in [2017,2018]:
            v,s,_,_=adjusted(t,x.year.eq(y),h);vals.append(v-v0);scores.append(s-s0)
        vals=np.array(vals);scores=np.array(scores);cov=scores@scores.T;W=float(vals@np.linalg.solve(cov,vals))
        pre.append({'threshold':t,'window_width':h,'change_2017_vs_2016':vals[0],'change_2018_vs_2016':vals[1],'wald_chi2':W,'df':2,'p_value':float(chi2.sf(W,2)),'interpretation':'Joint pre-period stability diagnostic, not proof of parallel counterfactual evolution.'})
# A fixed small composition diagnostic at the main bandwidth.
geo=[]
for label,mask in [('Manhattan',x.borough.eq('1')),('Other_boroughs',x.borough.ne('1'))]:
    for t in [1000000,2000000,3000000]:
        v0,s0,a0,b0=adjusted(t,x.year.between(2016,2018)&mask,100000);v1,s1,a1,b1=adjusted(t,x.year.between(2020,2025)&mask,100000);d=v1-v0;se=np.linalg.norm(s1-s0)
        geo.append({'geography':label,'threshold':t,'estimate':d,'se':se,'ci_low':d-1.96*se,'ci_high':d+1.96*se,'pre_above':a0,'pre_below':b0,'post_above':a1,'post_below':b1})
pd.DataFrame(rows).to_csv(OUT/'reform_period_bandwidth_checks.csv',index=False);pd.DataFrame(pre).to_csv(OUT/'reform_preperiod_checks.csv',index=False);pd.DataFrame(geo).to_csv(OUT/'reform_geography_checks.csv',index=False)
(OUT/'design_check_provenance.json').write_text(json.dumps({'source':str(SOURCE),'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'rows':len(x),'full_download_performed':False,'comparisons':len(rows),'preperiod_tests':len(pre),'pointwise_intervals':True,'classification':'Exploratory robustness, all specified comparisons reported; no causal certification.'},indent=2))
print('MAIN BANDWIDTH PERIODS\n',pd.DataFrame(rows).query('window_width==100000').to_string(index=False))
print('PREPERIOD\n',pd.DataFrame(pre).to_string(index=False))
print('GEOGRAPHY\n',pd.DataFrame(geo).to_string(index=False))
