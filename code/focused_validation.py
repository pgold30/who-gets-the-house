"""Finite, offline influence and record-consistency audit; no truth labels inferred."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from analyze_repeat_sales import ROOT, DATA, OUT, REP, design, estimate, residualize, old


def main():
    d=pd.read_csv(DATA/'house_pairs_enriched.csv.gz',dtype={'bbl':str,'borough':str,'zipcode':str,'cd':str,'deed_a':str,'deed_z':str})
    d=d[d.permit_free & ~d.lender_high & d.geo_linked].copy().reset_index(drop=True)
    for s in ['a','z']:d['date_'+s]=pd.to_datetime(d['date_'+s]).dt.date
    assert len(d)==6006 and not d.duplicated(['bbl','date_a','date_z']).any()
    G=int(d.cluster.max()+1);X=design(d,'zipcode',True)
    base,_,influence,_=estimate(d,X,G)
    fa=d.financed_base_a.to_numpy();fz=d.financed_base_z.to_numpy()
    Q=np.column_stack([(fa==0)&(fz==1),(fa==1)&(fz==0)]).astype(float)
    R=np.column_stack([residualize(X,q) for q in Q.T]);k=R@np.linalg.solve(R.T@R,np.array([.5,-.5]))
    assert abs(k@d.y.to_numpy()-base['pi_joint'])<1e-10
    assert np.max(np.abs(X.T@k))<1e-7
    assert np.allclose(k@Q,[.5,-.5],atol=1e-9)
    d['coefficient_weight']=k;d['parcel_influence']=influence[d.cluster]
    d['switch_group']=np.select([Q[:,0]==1,Q[:,1]==1],['cash_to_financed','financed_to_cash'],default='unchanged')
    par=d.groupby('bbl',sort=True).agg(borough=('borough','first'),zipcode=('zipcode','first'),pairs=('bbl','size'),influence=('parcel_influence','first'),absolute_outcome_weight=('coefficient_weight',lambda s:float(np.abs(s).sum())))
    par['absolute_influence']=par.influence.abs();par=par.sort_values('absolute_influence',ascending=False,kind='stable')
    par.to_csv(OUT/'focused_parcel_influence.csv')
    # Reconstruct exactly which archived rows created each pair; do not resolve
    # duplicate parcel/date candidates by an undocumented first-match merge.
    raw,pairs=old.load_panel(REP/'2_reproduce')
    source={}
    for a,z,da,dz in pairs:
        key=(a['bbl'],da,dz);assert key not in source;source[key]=(a,z)
    assert len(source)>=len(d)
    panel=pd.read_csv(REP/'2_reproduce/panel2.csv.gz',dtype={'bbl':str,'borough':str})
    houses=panel[panel.src.eq('house') & panel.borough.ne('5')]
    counts=houses.groupby(['bbl','date']).size()
    audit=[]
    for i,row in d.iterrows():
        a,z=source[(row.bbl,row.date_a,row.date_z)]
        assert abs(np.log(float(z['price'])/float(a['price']))-row.y)<1e-12
        assert (row.date_z-row.date_a).days>=1095
        for side,sale in [('a',a),('z',z)]:
            flags=[int(sale['financed_'+w]) for w in ['strict','base','wide']]
            assert flags[0]<=flags[1]<=flags[2]
            for w in ['strict','base','wide']:assert int(sale['financed_'+w])==int(row['financed_'+w+'_'+side])
            d.loc[i,'source_date_rows_'+side]=int(counts.loc[(row.bbl,str(row['date_'+side]))])
            d.loc[i,'source_mort_amt_'+side]=float(sale['mort_amt'])
            audit.append({'bbl':row.bbl,'date':str(row['date_'+side]),'side':side,'financed_base':flags[1],
                          'price':float(sale['price']),'mort_amt':float(sale['mort_amt']),
                          'source_date_rows':int(counts.loc[(row.bbl,str(row['date_'+side]))])})
    ep=pd.DataFrame(audit).drop_duplicates(['bbl','date'])
    ep['scheduled_loan_to_price']=ep.mort_amt/ep.price
    ambiguous=d.source_date_rows_a.gt(1)|d.source_date_rows_z.gt(1)
    zero_mort=((d.financed_base_a==1)&(d.source_mort_amt_a<=0))|((d.financed_base_z==1)&(d.source_mort_amt_z<=0))
    ep[(ep.source_date_rows>1)|((ep.financed_base==1)&(ep.mort_amt<=0))].to_csv(OUT/'focused_source_exceptions.csv',index=False)
    # Added after discovering duplicate source dates, before inspecting their
    # outcomes: report the exclusion rather than assuming duplicate rows valid.
    fits=[]
    def run(name,mask,selected=False):
        ss=d.loc[mask].copy();v,_,_,_=estimate(ss,design(ss,'zipcode',True),G)
        fits.append({'specification':name,'outcome_selected':selected,**v})
        print(name,len(ss),round(100*v['pi_joint'],3),flush=True)
    fits.append({'specification':'reference','outcome_selected':False,**base})
    for n in [1,5,10,30,60]:run('drop_top_absolute_influence_'+str(n),~d.bbl.isin(par.head(n).index),True)
    run('drop_top_positive_influence_60',~d.bbl.isin(par.sort_values('influence',ascending=False).head(60).index),True)
    for b in sorted(d.borough.unique()):run('leave_borough_'+b+'_out',d.borough.ne(b))
    for z in d.zipcode.value_counts().head(3).index:run('leave_largest_zip_'+z+'_out',d.zipcode.ne(z))
    safeguard=d.financing_stable & d.deed_unique_a & d.deed_unique_z & d.amount_match_a & d.amount_match_z & ~d.lender_broad
    run('joint_record_consistency_restrictions',safeguard)
    run('exclude_ambiguous_source_dates',~ambiguous)
    run('exclude_financed_without_positive_amount',~zero_mort)
    run('joint_safeguards_and_source_checks',safeguard & ~ambiguous & ~zero_mort)
    pd.DataFrame(fits).to_csv(OUT/'focused_validation_refits.csv',index=False)
    # Exact linear sensitivity to outcome shifts, not financing-label flips.
    ranked=par.sort_values('absolute_outcome_weight',ascending=False)
    stress=[]
    for n in [10,30,60,120]:
        sel=d.bbl.isin(ranked.head(n).index).to_numpy();mass=float(np.abs(k[sel]).sum())
        for fraction in [.5,1.]:
            delta=base['pi_joint']*fraction/mass
            shifted=d.y.to_numpy()-sel*np.sign(k)*delta
            expected=base['pi_joint']*(1-fraction)
            assert abs(k@shifted-expected)<1e-10
            stress.append({'parcels':n,'pairs':int(sel.sum()),'reduction_fraction':fraction,'uniform_log_outcome_shift':delta,'max_multiplicative_growth_factor':float(np.exp(delta)), 'resulting_contrast':float(k@shifted)})
    pd.DataFrame(stress).to_csv(OUT/'focused_outcome_perturbation_scenarios.csv',index=False)
    # Sampling file is blinded to prices, financing predictions and selection.
    rng=np.random.default_rng(20260922);selected=[]
    for group in ['cash_to_financed','financed_to_cash']:
        population=d.index[d.switch_group.eq(group)].to_numpy();chosen=rng.choice(population,20,replace=False)
        for i in chosen:selected.append((int(i),'probability_sample',group,20/len(population)))
    selected_ids={v[0] for v in selected}
    for i in d.index[d.bbl.isin(par.head(10).index)]:
        if i not in selected_ids:selected.append((int(i),'targeted_influence',d.loc[i,'switch_group'],None))
    selected_ids={v[0] for v in selected}
    for i in d.index[zero_mort]:
        if i not in selected_ids:selected.append((int(i),'targeted_missing_loan_amount',d.loc[i,'switch_group'],None))
    rng.shuffle(selected);blind=[];key=[]
    for j,(i,kind,group,prob) in enumerate(selected,1):
        row=d.loc[i];case=f'H{j:03d}'
        key.append({'case_id':case,'pair_row':i,'sample_kind':kind,'switch_group':group,'pair_selection_probability':prob,'inverse_probability_weight':None if prob is None else 1/prob,'bbl':row.bbl,'date_a':str(row.date_a),'date_z':str(row.date_z),'flag_a':int(row.financed_base_a),'flag_z':int(row.financed_base_z),'log_price_growth':row.y,'parcel_influence':row.parcel_influence})
        for side in ['a','z']:
            deed=row['deed_'+side]
            blind.append({'case_id':case,'endpoint':side,'bbl':row.bbl,'sale_date':str(row['date_'+side]),'deed_document_id':deed,
                          'deed_url':f'https://a836-acris.nyc.gov/DS/DocumentSearch/DocumentImageView?doc_id={deed}' if pd.notna(deed) else '',
                          'purchase_mortgage_document_id':'NOT_PRESERVED_IN_ARCHIVED_PANEL','purchase_financing_evidence':'UNREVIEWED',
                          'distress_evidence':'UNREVIEWED','borrower_buyer_match':'UNREVIEWED','collateral_match':'UNREVIEWED',
                          'purchase_vs_refinance':'UNREVIEWED','source_pages':'','reviewer':'','second_reviewer':'','notes':''})
    pd.DataFrame(blind).to_csv(ROOT/'audit/focused_blinded_house_review.csv',index=False)
    pd.DataFrame(key).to_csv(ROOT/'audit/focused_review_ANALYST_KEY.csv',index=False)
    summary={'reference':base,'weight_reconstruction_error':float(abs(k@d.y.to_numpy()-base['pi_joint'])),
        'unique_pairs':len(d),'unique_parcels':len(par),'ambiguous_source_date_pairs':int(ambiguous.sum()),
        'pairs_with_financed_endpoint_without_positive_amount':int(zero_mort.sum()),
        'unique_endpoints':len(ep),'financed_endpoints':int(ep.financed_base.sum()),
        'financed_endpoints_without_positive_mortgage_amount':int(((ep.financed_base==1)&(ep.mort_amt<=0)).sum()),
        'cash_endpoints_with_positive_mortgage_amount':int(((ep.financed_base==0)&(ep.mort_amt>0)).sum()),
        'largest_parcel_local_deletion_approximation_logpoints':float(100*par.iloc[0].absolute_influence),
        'absolute_influence_share_top_10':float(par.head(10).absolute_influence.sum()/par.absolute_influence.sum()),
        'fits':fits,'perturbation_scenarios':stress,'blinded_review_pairs':len(selected),'probability_review_pairs':40,
        'probability_sample_scope':'Two financing-switch arms only; weights do not represent unchanged-financing pairs or all NYC sales.',
        'independent_human_cases_completed_this_pass':0,'classification_error_rates_estimated':False,
        'limits':'Influence-selected deletion intervals are not post-selection-valid. Flag agreement is not truth. Outcome perturbations hold labels/design fixed and are not misclassification bounds.'}
    (OUT/'focused_validation.json').write_text(json.dumps(summary,indent=2))


if __name__=='__main__':main()
