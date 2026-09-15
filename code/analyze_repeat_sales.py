"""Cumulative repeat-sales estimates with joint parcel-clustered inference.

Original symmetry: residualize outcome, then contrast switch-arm means.
Joint symmetry: jointly fit switch-arm indicators and nuisance covariates.
Neither identifies execution certainty without further restrictions.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import sys,json,csv,gzip,re,collections,datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.linalg import lsqr
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; OUT=ROOT/'results'; OUT.mkdir(exist_ok=True)
REP=ROOT/'inputs'
sys.path.insert(0,str(REP/'3_section4.9'))
import legacy_estimator as old
SEED=20260909
ENTITY=re.compile(r'\b(LLC|L\.?L\.?C|INC|CORP|CORPORATION|COMPANY|LP|L\.?P|LLP|LTD|REALTY|PROPERTIES|HOLDINGS?|ASSOCIATES|PARTNERS\w*|VENTURES?|CAPITAL|EQUITIES|GROUP|ENTERPRISES?|DEVELOPMENT|BUILDERS?|CONSTRUCTION|MANAGEMENT|INVESTMENTS?|FUND|BANK|HOUSING|AUTHORITY)\b',re.I)
TRUST=re.compile(r'\b(TRUST|TRUSTEE|ESTATE|EXECUTOR|EXECUTRIX|ADMINISTRATOR)\b',re.I)
BROAD=re.compile(r'\b(BANK|MORTGAGE|SERVICING|LOAN|FEDERAL NATIONAL|FANNIE MAE|FREDDIE MAC|SECRETARY OF HOUSING|CERTIFICATEHOLDERS|MERS|SAVINGS|NATIONAL ASSOCIATION)\b',re.I)
# Identifiable financial institutions, still NOT a legal foreclosure classification.
HIGH=re.compile(r'\b(WELLS FARGO|JPMORGAN|JP MORGAN|J P MORGAN|BANK OF AMERICA|DEUTSCHE BANK|U\.?\s*S\.?\s*BANK|US BANK|CITIBANK|CITIMORTGAGE|HSBC BANK|BANK OF NEW YORK|FEDERAL NATIONAL MORTGAGE|FEDERAL HOME LOAN MORTGAGE|FANNIE MAE|FREDDIE MAC|SECRETARY OF HOUSING|HUD|OCWEN|NATIONSTAR|DITECH|BAC HOME LOANS|BANK OF AMER|PNC BANK|ONEWEST BANK|INDYMAC|WASHINGTON MUTUAL|EMIGRANT|GREEN TREE SERVICING|NEW YORK COMMUNITY BANK)\b',re.I)

def residualize(X,y):
    norms=np.sqrt(np.asarray(X.power(2).sum(axis=0)).ravel()); keep=norms>1e-12
    Z=X[:,keep].multiply(1/norms[keep]).tocsr()
    sol=lsqr(Z,y,atol=2e-11,btol=2e-11,iter_lim=10000)
    if sol[1] not in (0,1,2,4,5): raise RuntimeError(('lsqr did not converge',sol[1],sol[2]))
    return y-Z@sol[0]

def time_design(df,local=None):
    trip=[]; labels={}
    for i,r in enumerate(df.itertuples()):
        for sign,date in [(-1,r.date_a),(1,r.date_z)]:
            q=(date.year-2016)*4+(date.month-1)//3
            keys=[]
            if q: keys.append(('boro_q',r.borough,q))
            if local and date.year!=2016: keys.append((local,getattr(r,local),date.year))
            for key in keys:
                j=labels.setdefault(key,len(labels)); trip.append((i,j,sign))
    if trip:
        a,b,c=zip(*trip); X=sparse.coo_matrix((c,(a,b)),shape=(len(df),len(labels))).tocsr()
    else: X=sparse.csr_matrix((len(df),0))
    return X

def design(df,local=None,controls=False):
    X=time_design(df,local)
    if controls:
        # Difference of sale-specific buyer and seller type indicators. Natural
        # persons form the omitted category; missingness has its own indicator.
        C=np.array([(df[f'{role}_{cat}_z']-df[f'{role}_{cat}_a']).to_numpy() for role in ['buyer','seller'] for cat in ['entity','trust','unknown']]).T
        X=sparse.hstack([X,sparse.csr_matrix(C)],format='csr')
    return X

def cluster_sum(v,ids,G):
    if v.ndim==1: return np.bincount(ids,weights=v,minlength=G)
    return np.column_stack([np.bincount(ids,weights=v[:,j],minlength=G) for j in range(v.shape[1])])

def estimate(df,X,G,window='base',extra=None):
    y=df.y.to_numpy(); fa=df[f'financed_{window}_a'].to_numpy(); fz=df[f'financed_{window}_z'].to_numpy()
    cf=(fa==0)&(fz==1); fc=(fa==1)&(fz==0)
    Q=np.column_stack([cf,fc]).astype(float)
    if extra is not None: Q=np.column_stack([Q,extra])
    r=residualize(X,y)
    c=.5*(cf/cf.sum()-fc/fc.sum()); mc=residualize(X,c)
    pi=c@r
    inf=mc*r-.5*cf/cf.sum()*r[cf].mean()+.5*fc/fc.sum()*r[fc].mean()
    R=np.column_stack([residualize(X,Q[:,j]) for j in range(Q.shape[1])])
    gram=R.T@R
    assert np.linalg.matrix_rank(gram)==len(gram), 'nonidentified target coefficient'
    inv=np.linalg.inv(gram); beta=inv@(R.T@y); e=r-R@beta
    score=(R@inv)*e[:,None]
    contrast=np.zeros(len(beta));contrast[:2]=[.5,-.5]
    influence=cluster_sum(inf,df.cluster.to_numpy(),G)
    joint_inf=cluster_sum(score@contrast,df.cluster.to_numpy(),G)
    coeff_inf=cluster_sum(score,df.cluster.to_numpy(),G)
    result={'pairs':len(df),'parcels':df.bbl.nunique(),'cf':int(cf.sum()),'fc':int(fc.sum()),'nuisance_columns':X.shape[1],
        'pi_residual':float(pi),'asym_residual':float(r[cf].mean()+r[fc].mean()),
        'pi_joint':float(beta@contrast),'asym_joint':float(beta[0]+beta[1]),
        'se_residual':float(np.linalg.norm(influence)),'se_joint':float(np.linalg.norm(joint_inf)),
        'beta':beta.tolist(),'beta_se':np.sqrt((coeff_inf**2).sum(axis=0)).tolist(),
        'switch_information_fraction':float(np.trace(gram[:2,:2])/np.trace(Q[:,:2].T@Q[:,:2])),
        'max_nuisance_score':float(np.max(np.abs(X.T@e)))}
    for key in ['residual','joint']:
        result['ci_'+key]=[result['pi_'+key]-1.96*result['se_'+key],result['pi_'+key]+1.96*result['se_'+key]]
    return result,influence,joint_inf,coeff_inf

def prepare():
    rows,P=old.load_panel(REP/'2_reproduce'); hp=old.load_permits(REP/'2_reproduce')
    dm=json.loads((REP/'3_section4.9/deeds_for_pairs.json').read_text())
    gr=collections.defaultdict(lambda:collections.defaultdict(list))
    for x in json.loads((DATA/'parties.json').read_text()):gr[x['document_id']][x['party_type']].append(x.get('name','').strip().upper())
    masters={x['document_id']:x for x in json.loads((DATA/'master.json').read_text())}
    geo={str(int(float(x['bbl']))):x for x in json.loads((DATA/'geo.json').read_text())}
    audit=[]; name_audit=collections.Counter(); records=[]
    for a,z,da,dz in P:
        rec={'bbl':a['bbl'],'borough':a['borough'],'date_a':da,'date_z':dz,'y':np.log(float(z['price'])/float(a['price'])),'permit_free':not hp(a['bbl'],da,dz)}
        gg=geo.get(a['bbl'],{});rec.update(zipcode=gg.get('zipcode',''),cd=gg.get('cd',''))
        for side,s,date in [('a',a,da),('z',z,dz)]:
            for f in ['base','strict','wide']:rec[f'financed_{f}_{side}']=int(s[f'financed_{f}'])
            candidates=[(abs((dt.date.fromisoformat(d)-date).days),did) for d,did in dm.get(s['bbl'],[]) if abs((dt.date.fromisoformat(d)-date).days)<=45]
            gap=min((g for g,did in candidates),default=None)
            nearest=sorted({did for g,did in candidates if g==gap})
            did=nearest[0] if len(nearest)==1 else None
            master=masters.get(did,{})
            amt=float(master.get('document_amt') or 0)
            price=float(s['price']); amount_match=amt>0 and abs(amt-price)<=max(1,price*.01)
            rec[f'deed_{side}']=did or '';rec[f'deed_unique_{side}']=bool(did);rec[f'amount_match_{side}']=amount_match
            audit.append({'bbl':s['bbl'],'sale_date':str(date),'deed':did,'nearest_gap_days':gap,'nearest_ties':len(nearest),'amount_match_1pct':amount_match,'dof_price':price,'document_amount':amt})
            for role,typ in [('buyer','2'),('seller','1')]:
                ns=[n for n in gr.get(did,{}).get(typ,[]) if n]
                ent=any(ENTITY.search(n) for n in ns)
                tr=not ent and any(TRUST.search(n) for n in ns)
                for cat,value in [('entity',ent),('trust',tr),('unknown',not ns)]:rec[f'{role}_{cat}_{side}']=int(value)
                rec[f'{role}_lender_high_{side}']=any(HIGH.search(n) for n in ns)
                rec[f'{role}_lender_broad_{side}']=any(BROAD.search(n) for n in ns)
                for n in ns:
                    if BROAD.search(n) or HIGH.search(n):name_audit[(n,role,bool(HIGH.search(n)),bool(BROAD.search(n)))]+=1
        records.append(rec)
    df=pd.DataFrame(records);_,df['cluster']=np.unique(df.bbl,return_inverse=True)
    df['geo_linked']=(df.zipcode.str.fullmatch(r'\d{5}') & df.cd.ne(''))
    for level in ['high','broad']:
        df['lender_'+level]=df[[f'{r}_lender_{level}_{s}' for r in ['buyer','seller'] for s in ['a','z']]].any(axis=1)
    df['financing_stable']=np.all(np.column_stack([df[f'financed_strict_{s}']==df[f'financed_wide_{s}'] for s in ['a','z']]),axis=1)
    df.to_csv(DATA/'house_pairs_enriched.csv.gz',index=False)
    pd.DataFrame(audit).drop_duplicates(['bbl','sale_date']).to_csv(OUT/'deed_match_audit.csv',index=False)
    pd.DataFrame([{'name':n,'role':r,'specific_institution_rule':h,'broad_rule':b,'pair_endpoint_occurrences':v,'validation_status':'name-rule audit only; foreclosure/REO not legally validated'} for (n,r,h,b),v in name_audit.items()]).sort_values('pair_endpoint_occurrences',ascending=False).to_csv(OUT/'lender_name_audit.csv',index=False)
    pd.DataFrame(rows).to_csv(DATA/'four_borough_panel.csv.gz',index=False)
    return df,P

def main():
    df,P=prepare();G=df.cluster.max()+1
    masks={}
    masks['S0_original']=np.ones(len(df),bool)
    masks['S1_permit_free']=df.permit_free
    masks['S2_named_institution_exclusion']=df.permit_free&~df.lender_high
    masks['S3_buyer_seller_controls']=masks['S2_named_institution_exclusion']
    masks['S4_same_linked_sample']=masks['S3_buyer_seller_controls']&df.geo_linked
    masks['S5_community_district_year']=masks['S4_same_linked_sample']
    masks['S6_zip_year']=masks['S4_same_linked_sample']
    masks['S7_stable_financing']=masks['S6_zip_year']&df.financing_stable
    masks['S8_broad_lender_exclusion']=masks['S6_zip_year']&~df.lender_broad
    masks['S9_unique_deed_amount_match']=masks['S6_zip_year']&df.amount_match_a&df.amount_match_z&df.deed_unique_a&df.deed_unique_z
    specs={}; influences=[]; labels=[]; designs={}
    for i,(name,mask) in enumerate(masks.items()):
        sub=df.loc[mask].copy(); local='cd' if name.startswith('S5') else 'zipcode' if i>=6 else None
        X=design(sub,local,i>=3)
        result,inf,jinf,_=estimate(sub,X,G);specs[name]=result;designs[name]=(sub,X)
        influences.extend([inf,jinf]);labels.extend([name+'|residual',name+'|joint'])
        print(name,result,flush=True)
    assert abs(specs['S0_original']['pi_residual']-.11142999677171206)<1e-9
    assert abs(specs['S1_permit_free']['pi_residual']-.09341893684354056)<1e-9
    IF=np.column_stack(influences);cov=IF.T@IF
    np.savez_compressed(OUT/'joint_influence_functions.npz',influence=IF,labels=np.array(labels),parcel=df.drop_duplicates('cluster').sort_values('cluster').bbl.to_numpy())
    pd.DataFrame(cov,index=labels,columns=labels).to_csv(OUT/'joint_covariance.csv')
    comparisons=[]
    for first,last in [('S0_original','S1_permit_free'),('S1_permit_free','S2_named_institution_exclusion'),('S2_named_institution_exclusion','S3_buyer_seller_controls'),('S3_buyer_seller_controls','S4_same_linked_sample'),('S4_same_linked_sample','S5_community_district_year'),('S4_same_linked_sample','S6_zip_year'),('S6_zip_year','S7_stable_financing'),('S6_zip_year','S8_broad_lender_exclusion'),('S6_zip_year','S9_unique_deed_amount_match'),('S0_original','S6_zip_year')]:
        for kind in ['residual','joint']:
            a=labels.index(first+'|'+kind);b=labels.index(last+'|'+kind)
            delta=specs[last]['pi_'+kind]-specs[first]['pi_'+kind];se=float(np.linalg.norm(IF[:,b]-IF[:,a]))
            comparisons.append({'from':first,'to':last,'estimand':kind,'difference':delta,'se':se,'ci_low':delta-1.96*se,'ci_high':delta+1.96*se})
    pd.DataFrame(comparisons).to_csv(OUT/'paired_specification_differences.csv',index=False)
    flat=[]
    for name,r in specs.items():
        flat.append({'specification':name,**{k:v for k,v in r.items() if not isinstance(v,list)},**{f'ci_{kind}_{end}':r['ci_'+kind][j] for kind in ['residual','joint'] for j,end in enumerate(['low','high'])}})
    pd.DataFrame(flat).to_csv(OUT/'cumulative_robustness.csv',index=False)
    (OUT/'repeat_sales_results.json').write_text(json.dumps(specs,indent=2))
    # Financing-window sensitivity uses identical pairs, including the index fit.
    fs=[]
    for name in ['S0_original','S1_permit_free','S6_zip_year']:
        sub,X=designs[name]
        for window in ['strict','base','wide']:
            r,_,_,_=estimate(sub,X,G,window);fs.append({'sample':name,'window':window,**r})
    (OUT/'financing_sensitivity.json').write_text(json.dumps(fs,indent=2))
    # Credit conditions at both transaction dates. Last available weekly rate;
    # rate levels are absorbed by calendar controls. Rate interactions are not
    # an instrument for financing, denial rates, or execution risk.
    rates=pd.read_csv(DATA/'MORTGAGE30US.csv');rd=np.array(pd.to_datetime(rates.iloc[:,0]).dt.date);rv=pd.to_numeric(rates.iloc[:,1],errors='coerce').to_numpy()
    good=np.isfinite(rv);rd=rd[good];rv=rv[good]
    credit={}
    for name in ['S1_permit_free','S6_zip_year']:
        sub,X=designs[name]
        ra=rv[np.searchsorted(rd,sub.date_a.to_numpy(),side='right')-1]-4
        rz=rv[np.searchsorted(rd,sub.date_z.to_numpy(),side='right')-1]-4
        fa=sub.financed_base_a.to_numpy();fz=sub.financed_base_z.to_numpy()
        extras=np.column_stack([fa*ra,fz*rz])
        r,_,_,ci=estimate(sub,X,G,extra=extras)
        # Restricted counterpart imposes the same rate slope in levels at both dates.
        common=extras[:,1]-extras[:,0]
        rc,_,_,_=estimate(sub,X,G,extra=common)
        diff=r['beta'][2]+r['beta'][3];se=float(np.linalg.norm(ci[:,2]+ci[:,3]))
        credit[name]={'separate_date_rate_interactions':r,'same_level_slope_restriction':rc,'first_plus_second_slope_test':{'estimate':diff,'se':se,'ci':[diff-1.96*se,diff+1.96*se]},'coefficients':['cash_to_fin','fin_to_cash','fin_first*(rate_first-4)','fin_second*(rate_second-4)']}
    (OUT/'credit_both_sale_dates.json').write_text(json.dumps(credit,indent=2))
    support={}
    for field in ['cd','zipcode']:
        sub=designs['S6_zip_year'][0]; counts=collections.Counter()
        for r in sub.itertuples():
            for date in [r.date_a,r.date_z]:counts[(getattr(r,field),date.year)]+=1
        support[field]={'areas':sub[field].nunique(),'area_year_cells':len(counts),'cells_fewer_than_5_endpoints':sum(v<5 for v in counts.values()),'median_endpoints_per_cell':float(np.median(list(counts.values())))}
    audit={'all_pairs':len(df),'geography_linked_pairs':int(df.geo_linked.sum()),'permit_free':int(df.permit_free.sum()),'specific_institution_pairs':int(df.lender_high.sum()),'broad_lender_pairs':int(df.lender_broad.sum()),'financing_stable_pairs':int(df.financing_stable.sum()),'support':support,'unknown_party_endpoints':{f'{r}_{s}':int(df[f'{r}_unknown_{s}'].sum()) for r in ['buyer','seller'] for s in ['a','z']},'unique_deed_endpoints':int(df.deed_unique_a.sum()+df.deed_unique_z.sum()),'total_endpoints':2*len(df)}
    # Sensitivity allowing arbitrary dependence within ZIP code, with the same
    # fitted model. This is descriptive inference with relatively few clusters.
    for name in ['S4_same_linked_sample','S6_zip_year']:
        sub,X=designs[name];codes,idx=np.unique(sub.zipcode,return_inverse=True);cp=sub.copy();cp['cluster']=idx
        r,_,_,_=estimate(cp,X,len(codes));audit[name+'_zip_clustered']=r
    (OUT/'sample_and_classification_audit.json').write_text(json.dumps(audit,indent=2))
    # Shared parcel draws verify the two-step influence-function calculation by
    # actually refitting the index on the first two cumulative specifications.
    rng=np.random.default_rng(SEED); draws=[]
    bootnames=['S0_original','S1_permit_free','S4_same_linked_sample','S6_zip_year']
    for b in range(999):
        w=rng.multinomial(G,np.repeat(1/G,G));vals=[]
        for name in bootnames:
            sub,X=designs[name];ww=w[sub.cluster.to_numpy()];keep=ww>0;sw=np.sqrt(ww[keep]);XX=X[keep].multiply(sw[:,None]).tocsr()
            y=sub.y.to_numpy()[keep];rr=residualize(XX,y*sw)/sw
            fa=sub.financed_base_a.to_numpy()[keep];fz=sub.financed_base_z.to_numpy()[keep]
            cf=(fa==0)&(fz==1);fc=(fa==1)&(fz==0)
            vals.append(.5*(np.average(rr[cf],weights=ww[keep][cf])-np.average(rr[fc],weights=ww[keep][fc])))
            Q=np.column_stack([cf,fc]).astype(float)*sw[:,None]
            R=np.column_stack([residualize(XX,Q[:,j]) for j in range(2)])
            beta=np.linalg.solve(R.T@R,R.T@(y*sw))
            vals.append(.5*(beta[0]-beta[1]))
        draws.append(vals)
        if b%100==0: print('paired full bootstrap',b,flush=True)
    draws=np.array(draws);np.save(OUT/'paired_full_refit_bootstrap.npy',draws)
    blabels=[name+'|'+kind for name in bootnames for kind in ['residual','joint']]
    bootout={'replications':len(draws),'seed':SEED,'labels':blabels,'ci':{label:np.percentile(draws[:,j],[2.5,97.5]).tolist() for j,label in enumerate(blabels)},'differences':{},'method':'common multinomial resampling of original parcel clusters; index and controls refitted in each specification and draw'}
    for a,b in [(0,1),(2,3),(0,3)]:
        for k,kind in enumerate(['residual','joint']):
            key=bootnames[b]+' minus '+bootnames[a]+'|'+kind
            bootout['differences'][key]=np.percentile(draws[:,2*b+k]-draws[:,2*a+k],[2.5,97.5]).tolist()
    (OUT/'paired_full_refit_bootstrap.json').write_text(json.dumps(bootout,indent=2))
    print('DONE',flush=True)
if __name__=='__main__':main()
