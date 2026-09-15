"""Targeted numerical, classification and composition checks."""
import json,sys,collections
from pathlib import Path
import numpy as np,pandas as pd
from scipy import sparse
from scipy.stats import norm
from analyze_repeat_sales import ROOT,DATA,OUT,REP,design,estimate,residualize,cluster_sum

def main():
    df=pd.read_csv(DATA/'house_pairs_enriched.csv.gz',dtype={'bbl':str,'borough':str,'zipcode':str,'cd':str})
    for col in ['date_a','date_z']:df[col]=pd.to_datetime(df[col]).dt.date
    G=df.cluster.max()+1
    sub=df[df.permit_free&~df.lender_high&df.geo_linked].copy();X=design(sub,'zipcode',True)
    result,inf,jinf,_=estimate(sub,X,G)
    # Finite differences perturb a parcel weight and refit all nuisance terms.
    checks=[];rng=np.random.default_rng(20260910)
    cluster_choices=rng.choice(sub.cluster.unique(),5,replace=False)
    for cluster in cluster_choices:
        eps=1e-4;w=1+eps*(sub.cluster.to_numpy()==cluster);sw=np.sqrt(w);XX=X.multiply(sw[:,None]).tocsr()
        y=sub.y.to_numpy();r=residualize(XX,y*sw)/sw
        fa=sub.financed_base_a.to_numpy();fz=sub.financed_base_z.to_numpy();cf=(fa==0)&(fz==1);fc=(fa==1)&(fz==0)
        pi=.5*(np.average(r[cf],weights=w[cf])-np.average(r[fc],weights=w[fc]))
        Q=np.column_stack([cf,fc])*sw[:,None];R=np.column_stack([residualize(XX,Q[:,j]) for j in range(2)]);beta=np.linalg.solve(R.T@R,R.T@(y*sw));joint=.5*(beta[0]-beta[1])
        for kind,value,reference,derivative in [('residual',pi,result['pi_residual'],inf[cluster]),('joint',joint,result['pi_joint'],jinf[cluster])]:
            err=abs((value-reference)/eps-derivative)
            checks.append({'cluster':int(cluster),'estimand':kind,'finite_difference':(value-reference)/eps,'analytic_derivative':float(derivative),'absolute_error':err})
            assert err<1e-7,(kind,err)
    (OUT/'influence_function_numerical_checks.json').write_text(json.dumps(checks,indent=2))
    # Explicit test of a coefficient at both dates, after allowing financing-
    # specific linear calendar trends. Rates are lagged to latest available week.
    rates=pd.read_csv(DATA/'MORTGAGE30US.csv');dates=np.array(pd.to_datetime(rates.iloc[:,0]).dt.date);values=rates.iloc[:,1].to_numpy()
    ra=values[np.searchsorted(dates,sub.date_a,side='right')-1]-4;rz=values[np.searchsorted(dates,sub.date_z,side='right')-1]-4
    fa=sub.financed_base_a.to_numpy();fz=sub.financed_base_z.to_numpy()
    ta=np.array([(d-pd.Timestamp('2020-01-01').date()).days/365.25 for d in sub.date_a]);tz=np.array([(d-pd.Timestamp('2020-01-01').date()).days/365.25 for d in sub.date_z])
    extras=np.column_stack([fa*ra,fz*rz,fa*ta,fz*tz])
    r,_,_,_=estimate(sub,X,G,extra=extras)
    (OUT/'credit_calendar_trend_sensitivity.json').write_text(json.dumps({'model':r,'coefficients':['cash_to_fin','fin_to_cash','fin_first*(rate_first-4)','fin_second*(rate_second-4)','fin_first*(first_calendar_date-2020)','fin_second*(second_calendar_date-2020)'],'interpretation':'Exploratory rate associations conditional on separate linear financing trends. No exogenous credit shock is identified.'},indent=2))
    # Window agreement is an internal consistency statistic, not classification accuracy.
    panel=pd.read_csv(REP/'2_reproduce/panel2.csv.gz',dtype={'bbl':str,'borough':str});panel=panel[panel.borough!='5']
    win=[]
    for typ,ss in panel.groupby('src'):
        for f in ['base','strict','wide']:
            win.append({'type':typ,'window':f,'sales':len(ss),'financed_share':float(ss['financed_'+f].mean()),'disagreements_with_base':int((ss['financed_'+f]!=ss.financed_base).sum())})
        assert np.all(ss.financed_strict<=ss.financed_base) and np.all(ss.financed_base<=ss.financed_wide)
    pd.DataFrame(win).to_csv(OUT/'financing_window_agreement.csv',index=False)
    # Charm pricing: same post-reform sample; joint partial regression conditions
    # on borough-by-year and property-type-by-year composition.
    panel['year']=pd.to_datetime(panel.date).dt.year;panel=panel[panel.year.between(2020,2025)].copy()
    selected=[]
    for threshold in [500000,1000000,2000000,3000000]:
        ss=panel[panel.price.isin([threshold-1,threshold])].copy();ss['threshold']=threshold;ss['charm']=(ss.price==threshold-1).astype(int);selected.append(ss)
    pp=pd.concat(selected,ignore_index=True);labels=[]
    # Threshold fixed effects keep different base financing propensities separate.
    X=pd.get_dummies(pp[['threshold']].astype(str),dtype=float)
    for name,series in [('boro_year',pp.borough.astype(str)+'_'+pp.year.astype(str)),('type_year',pp.src.astype(str)+'_'+pp.year.astype(str))]:
        X=pd.concat([X,pd.get_dummies(series,prefix=name,dtype=float)],axis=1)
    X=sparse.csr_matrix(X.to_numpy());Q=np.column_stack([(pp.threshold.eq(t)&pp.charm.eq(1)).astype(float) for t in [500000,1000000,2000000,3000000]])
    R=np.column_stack([residualize(X,Q[:,j]) for j in range(4)]);inv=np.linalg.inv(R.T@R);y=pp.financed_base.to_numpy();b=inv@(R.T@y);e=residualize(X,y)-R@b
    _,g=np.unique(pp.bbl,return_inverse=True);IF=cluster_sum((R@inv)*e[:,None],g,g.max()+1);se=np.sqrt((IF**2).sum(axis=0))
    out=[]
    for j,t in enumerate([500000,1000000,2000000,3000000]):out.append({'threshold':t,'adjusted_financed_share_difference':b[j],'se':se[j],'ci_low':b[j]-1.96*se[j],'ci_high':b[j]+1.96*se[j],'exact_price_sales':int(pp.threshold.eq(t).sum()),'charm_sales':int((pp.threshold.eq(t)&pp.charm.eq(1)).sum()),'same_tax_side':t==500000})
    pd.DataFrame(out).to_csv(OUT/'charm_composition_adjusted.csv',index=False)
    # Save an adjudication queue rather than manufacture ground-truth labels.
    matches=pd.read_csv(OUT/'deed_match_audit.csv',dtype={'bbl':str,'deed':str})
    endpoints=[]
    for side in ['a','z']:
        ss=df[['bbl',f'date_{side}',f'buyer_lender_high_{side}',f'seller_lender_high_{side}',f'buyer_lender_broad_{side}',f'seller_lender_broad_{side}']].copy()
        ss.columns=['bbl','sale_date','buyer_high','seller_high','buyer_broad','seller_broad'];ss.sale_date=ss.sale_date.astype(str);endpoints.append(ss)
    ee=pd.concat(endpoints).drop_duplicates(['bbl','sale_date']).merge(matches,on=['bbl','sale_date'],how='left',validate='one_to_one')
    ee['stratum']=np.select([ee.buyer_high|ee.seller_high,ee.buyer_broad|ee.seller_broad],['specific_institution','broad_only'],default='unflagged')
    sample=pd.concat([ss.sample(n=min(30,len(ss)),random_state=20260910) for _,ss in ee.groupby('stratum')])
    sample['ground_truth_distress']='UNREVIEWED';sample['image_or_court_evidence']='';sample['reviewer']=''
    sample.to_csv(OUT/'distress_adjudication_queue.csv',index=False)
    print('Numerical derivative checks passed; composition, financing and adjudication files saved.',flush=True)
if __name__=='__main__':main()
