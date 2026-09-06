import sys, json; sys.path.insert(0, __import__('os').path.dirname(__file__))
import sim_v6_ext as E, numpy as np
from multiprocessing import Pool
def job(a):
    label,kw,reg,seed=a; return label,reg,seed,E.run(reg,seed,p=E.variant(**kw))
if __name__=="__main__":
    pts={"oo_arrivals=34":dict(oo_arrivals=34),"listings=10":dict(listings_per_district=10),"oo_arrivals=25":dict(oo_arrivals=25)}
    jobs=[(l,kw,r,E.SEED+100*i) for l,kw in pts.items() for r in ["unconstrained","static_cap","wfq","contention_duty"] for i in range(12)]
    with Pool(2) as pool: res=pool.map(job,jobs,chunksize=1)
    R={}
    for l,r,s,m in res: R.setdefault(l,{}).setdefault(r,{})[s]=m
    out={}
    for l in pts:
        u=R[l]["unconstrained"]
        print("==",l, "inst share unc %.3f"%np.mean([u[s]['inst_share'] for s in u]))
        for r in ["static_cap","wfq","contention_duty"]:
            d=np.array([100*R[l][r][s]['welfare']/u[s]['welfare'] for s in u]); st=np.array([100*(R[l][r][s]['starvation_rate']-u[s]['starvation_rate']) for s in u])
            print(f"   {r:16} welfare idx mean {d.mean():7.3f}  paired se {d.std(ddof=1)/np.sqrt(12):.3f}  | starvation change {st.mean():+6.2f} pp (se {st.std(ddof=1)/np.sqrt(12):.2f})")
            out[f"{l}|{r}"]=dict(welfare_index=d.mean(),se=d.std(ddof=1)/np.sqrt(12),dstarv=st.mean())
    # Table 6 verification rows with 8 reps
    print("== Table 6 verification (8 reps): capacity 3 and 10")
    jobs=[(f"cap{c}",dict(inst_capacity=c),r,E.SEED+100*i) for c in (3,10) for r in ["unconstrained","static_cap","wfq","contention_duty"] for i in range(8)]
    with Pool(2) as pool: res=pool.map(job,jobs,chunksize=1)
    R={}
    for l,r,s,m in res: R.setdefault(l,{}).setdefault(r,{})[s]=m
    for l in ("cap3","cap10"):
        u=R[l]["unconstrained"]; bw=np.mean([u[s]['welfare'] for s in u]); bs=np.mean([u[s]['starvation_rate'] for s in u])
        print(f"   {l}: unc inst share {np.mean([u[s]['inst_share'] for s in u]):.4f} starv {bs:.4f} | " + " | ".join(f"{r}: dstarv {100*(np.mean([R[l][r][s]['starvation_rate'] for s in u])-bs):+.1f}pp welf {100*np.mean([R[l][r][s]['welfare'] for s in u])/bw:.2f}" for r in ["static_cap","wfq","contention_duty"]))
    json.dump(out,open('flipcheck.json','w'),indent=1)
