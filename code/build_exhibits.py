"""All numerical manuscript exhibits are generated from this release's results."""
import os,json
from pathlib import Path
import numpy as np,pandas as pd
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[1]/'tmp/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'results';O=ROOT/'paper/generated';O.mkdir(parents=True,exist_ok=True)
def read(n):return json.loads((R/n).read_text())
def f(x):return f'{100*x:.2f}'
def ci(x,scale=100):return '['+', '.join(f'{scale*v:.2f}' for v in x)+']'
def table(file,caption,label,headers,rows,note,columns=None):
    columns=columns or 'l'+'r'*(len(headers)-1)
    s='\\begin{table}[htbp]\n\\centering\\small\\singlespacing\n\\caption{'+caption+'}\\label{'+label+'}\n\\begin{tabular}{'+columns+'}\n\\toprule\n'+' & '.join(headers)+' \\\\\n\\midrule\n'
    s+='\n'.join(' & '.join(map(str,row))+' \\\\' for row in rows)
    s+='\n\\bottomrule\n\\end{tabular}\n\\notes{'+note+'}\n\\end{table}\n'
    (O/file).write_text(s)
S=read('repeat_sales_results.json');B=read('paired_full_refit_bootstrap.json');P=read('property_comparison.json');A=read('sample_and_classification_audit.json')
assert B['replications']==999
names=list(S)[:7];labels=['Original sample','Permit-free','+ Named institutions excluded','+ Buyer/seller type controls','Same geography-linked sample','+ Community-district/year','+ ZIP/year']
rows=[]
for n,l in zip(names,labels):
    r=S[n];bc=B['ci'].get(n+'|joint',r['ci_joint']);mark='*' if n+'|joint' in B['ci'] else ''
    rows.append([l,f"{r['pairs']:,}",f(r['pi_residual']),f(r['pi_joint']),ci(bc)+mark])
table('cumulative.tex','Cumulative house robustness','tab:cumulative',['Specification','Pairs','Residual','Joint','Joint 95\\% CI'],rows,'All estimates and intervals are log points. Every row includes borough-quarter effects. The last two rows are alternative geographic specifications added to the same linked baseline. Institutional exclusions use grantor and grantee name rules at both dates, not verified distress. Stars denote percentile intervals from 999 common parcel-bootstrap refits; other intervals use joint parcel influence functions (CR0). Intervals are pointwise. The residual and joint columns are different estimands.')
D=pd.read_csv(R/'paired_specification_differences.csv');rows=[]
for a,b,label in [('S2_named_institution_exclusion','S3_buyer_seller_controls','Party controls'),('S4_same_linked_sample','S5_community_district_year','Community-district/year'),('S4_same_linked_sample','S6_zip_year','ZIP/year'),('S0_original','S6_zip_year','Original to final')]:
    v=D[(D['from']==a)&(D.to==b)&(D.estimand=='joint')].iloc[0];cc=B['differences'].get(b+' minus '+a+'|joint',[v.ci_low,v.ci_high]);rows.append([label,f(v['difference']),ci(cc)])
table('paired.tex','Paired changes in the joint house contrast','tab:paired',['Comparison','Change','95\\% CI'],rows,'Log points. Differences use cross-specification covariance on original parcel clusters. ZIP/year and original-to-final intervals use the common full-refit bootstrap; the others use the joint analytic covariance. Party and geographic comparisons hold the relevant estimation sample fixed. Original-to-final also changes the sample.')
rows=[]
for typ in ['house','condo']:
    v=P[typ];rows.append([typ.title(),f"{v['pairs']:,}",v['cf'],v['fc'],f(v['pi_joint']),ci(v['ci_joint'])])
table('property.tex','House and condominium contrasts under common controls','tab:property',['Type','Pairs','$N_{cf}$','$N_{fc}$','Joint','95\\% CI'],rows,'Both rows use borough-quarter effects and adjacent eligible sales at least 1,095 days apart. All available eligible pairs are used; the cumulative house restrictions are not imposed on the condominium sample. Parcel-clustered CR0 intervals, in log points. Differences in coverage, ownership and financing measurement prevent a causal property-type interpretation.')
C=read('coop_estimate_sensitivity.json');rows=[]
for method,label in [('legacy_expanded','Expanded count rule'),('expanded_all_competitors','All competing sales'),('unique_strict','Unique timing: narrow'),('unique_base','Unique timing: base'),('unique_wide','Unique timing: wide')]:
    v=next(x for x in C if x['tag']=='adjacent_all_observed_unit_sales' and x['method']==method);rows.append([label,f"{v['pairs']:,}",v['cf'],v['fc'],f(v['pi_joint']),ci(v['ci_joint'])])
table('coop.tex','Co-operative assignment sensitivity','tab:coop',['Assignment rule','Pairs','$N_{cf}$','$N_{fc}$','Joint','95\\% CI'],rows,'Log points and building-clustered CR0 intervals. Every row forms adjacency using all observed known-unit sales before dropping ineligible endpoints and ambiguous financing. Timing uniqueness does not establish debtor identity or purchase purpose. No matched filing is a cash proxy, not proof of an unlevered purchase. These are fresh-extract estimates, not an exact reconstruction of unavailable legacy co-op microdata.')
F=read('financing_sensitivity.json');rows=[]
for w in ['strict','base','wide']:
    v=next(x for x in F if x['sample']=='S6_zip_year' and x['window']==w);rows.append(['Financing window: '+w,f"{v['pairs']:,}",f(v['pi_joint']),ci(v['ci_joint'])])
for name,label in [('S7_stable_financing','Stable labels at both dates'),('S8_broad_lender_exclusion','Broader institution exclusion'),('S9_unique_deed_amount_match','Unique deed / amount match')]:
    v=S[name];rows.append([label,f"{v['pairs']:,}",f(v['pi_joint']),ci(v['ci_joint'])])
table('sensitivity.tex','Classification and linkage sensitivity','tab:sensitivity',['Restriction','Pairs','Joint','95\\% CI'],rows,'All rows use the ZIP-year model, with borough-quarter and buyer/seller controls. Log points; parcel CR0 intervals. Stable labels agree between strict and wide windows at both dates. Amount consistency requires a unique nearest deed within 45 days and positive consideration within the larger of one dollar and one percent of the DOF price. These tests concern internal consistency, not classification accuracy.')
CR=read('credit_both_sale_dates.json')['S6_zip_year']['separate_date_rate_interactions'];CT=read('credit_calendar_trend_sensitivity.json')['model'];rows=[]
for j,label in [(2,'First-sale financing $\\times$ rate'),(3,'Second-sale financing $\\times$ rate')]:
    rows.append([label,f(CR['beta'][j]),'('+f(CR['beta_se'][j])+')',f(CT['beta'][j]),'('+f(CT['beta_se'][j])+')'])
table('credit.tex','Credit conditions at both sale dates','tab:credit',['Interaction','Baseline','SE','+ Trends','SE'],rows,'Coefficients in log points per one percentage point of the mortgage rate. Both models include the full geographic house controls and two financing-switch indicators. The second adds separate financing-specific linear calendar trends at both sale dates. Rates are the latest published weekly PMMS value on or before sale, centered on 4 percent; calendar trends are centered on 2020. Standard errors cluster by parcel. The coefficients are exploratory associations.')
N=pd.read_csv(R/'notch_difference_in_differences.csv');N=N[N.placebos.str.contains(',')];rows=[]
for v in N.itertuples():rows.append([f'\\${v.threshold/1e6:g}m',f'{v.difference_in_log_ratios:.3f}',ci([v.ci_low,v.ci_high],1),f'{v.percent_change_relative_ratio:.1f}'])
table('notches.tex','Changes in local price-count ratios around transfer-tax thresholds','tab:notches',['Threshold','Log-ratio change','95\\% CI','Relative change (\\%)'],rows,'The 2016--2018 to 2020--2025 change in the log above/below count ratio, less the mean change at four placebo prices (\\$1.5m, \\$1.75m, \\$2.25m, \\$2.5m). The above window is $[X,X+100{,}000)$ and the below window $[X-150{,}000,X-50{,}000)$; at \\$500,000 the above window excludes $X$, where the lower city rate still applies. All 2019 observations are omitted. Joint parcel CR0 intervals include overlapping-window covariance. Relative change is $100(\\exp(\\widehat\\Delta)-1)$, not lost sales or welfare.')
H=pd.read_csv(R/'charm_composition_adjusted.csv');rows=[]
for v in H.itertuples():rows.append([f'\\${v.threshold/1e6:g}m',v.exact_price_sales,v.charm_sales,f(v.adjusted_financed_share_difference),ci([v.ci_low,v.ci_high])])
table('charm.tex','Financing composition at exact and one-dollar-below prices','tab:charm',['Threshold','Selected sales','$X-1$ sales','Difference','95\\% CI'],rows,'Common 2020--2025 four-borough house/condo sample. Difference in financed share (percentage points), $X-1$ minus $X$, from a linear probability model with threshold, borough-year and property-type-year effects. Parcel CR0 intervals. Exact-price cells are small and selected. At \\$500,000 both prices face the lower city rate. These are financing-composition contrasts, not estimates of economic incidence.')
# The inversion is explicitly a scenario grid, not an estimated model.
rows=[];grid=[]
for q in [.1,.2,.3]:
    row=[f'{q:.1f}']
    for typ,b in [('house',S['S6_zip_year']['pi_joint']),('condo',P['condo']['pi_joint'])]:
        d=np.expm1(b)*(1-q)/q;row.append(f'{100*d:.1f}');grid.append({'property':typ,'q_failure_scenario':q,'gap_log':b,'implied_d':d})
    rows.append(row)
table('inversion.tex','Relisting-loss scenarios implied by the observed contrasts','tab:inversion',['Failure probability $q$','Houses: $100d^*$','Condos: $100d^*$'],rows,'Scenario calculations from $d^*=(\\exp(\\pi)-1)(1-q)/q$. Houses use the full geographic joint estimate; condos use the borough-quarter joint estimate. They have different covariate sets and populations. Values of $q$ are illustrative assumptions, not estimated contract-failure probabilities. No common relisting technology is imposed as an empirical fact.')
(R/'model_inversion_scenarios.json').write_text(json.dumps(grid,indent=2))
macros={'HouseGap':f(S['S6_zip_year']['pi_joint']),'HouseCI':ci(B['ci']['S6_zip_year|joint']),'GeoChange':f(S['S6_zip_year']['pi_joint']-S['S4_same_linked_sample']['pi_joint']),'GeoCI':ci(B['differences']['S6_zip_year minus S4_same_linked_sample|joint']),'CondoGap':f(P['condo']['pi_joint']),'CondoCI':ci(P['condo']['ci_joint']),'InitialGap':f(S['S0_original']['pi_joint']),'PartyChange':f(S['S3_buyer_seller_controls']['pi_joint']-S['S2_named_institution_exclusion']['pi_joint'])}
(O/'numbers.tex').write_text('\n'.join('\\newcommand{\\'+k+'}{'+v+'}' for k,v in macros.items())+'\n')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(figsize=(8,4));y=np.arange(len(names))
for off,key,color,label in [(-.13,'residual','#976143','Outcome-only residual'),(.13,'joint','#1e5a78','Joint coefficient')]:
    vals=np.array([100*S[n]['pi_'+key] for n in names]);se=np.array([100*S[n]['se_'+key] for n in names]);ax.errorbar(vals,y+off,xerr=1.96*se,fmt='o',ms=4,capsize=2,label=label,color=color)
ax.set_yticks(y,labels);ax.invert_yaxis();ax.set_xlabel('Log points');ax.legend(frameon=False,loc='lower right',fontsize=8);ax.grid(axis='x',alpha=.2);fig.tight_layout();fig.savefig(O/'robustness.png',dpi=230);plt.close(fig)
annual=pd.read_csv(R/'notch_annual_placebo_adjusted.csv');fig,axes=plt.subplots(1,3,figsize=(8,2.8))
for ax,t in zip(axes,[1000000,2000000,3000000]):
    z=annual[annual.threshold==t];ax.axvspan(2018.5,2019.5,color='#eeeeee');ax.errorbar(z.year,z.placebo_adjusted_log_ratio,yerr=1.96*z.adjusted_se,fmt='o-',ms=3,capsize=2,color='#1e5a78');ax.set_title(f'${t/1e6:g} million');ax.set_xticks([2016,2019,2022,2025]);ax.grid(alpha=.15)
axes[0].set_ylabel('Adjusted log count ratio');fig.tight_layout();fig.savefig(O/'annual.png',dpi=230);plt.close(fig)
(R/'publication_numbers.json').write_text(json.dumps({'release':'WGTH-2026-09-10-JHE-S1','macros':macros,'source_bootstrap_replications':B['replications']},indent=2))
print('Generated nine tables, two figures, scenario grid and manuscript macros.',flush=True)
