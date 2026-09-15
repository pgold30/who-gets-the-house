"""Recompute comparable borough-quarter house/condo contrasts from archived panel."""
import json, numpy as np, pandas as pd
from analyze_repeat_sales import DATA, OUT, REP, design, estimate
from legacy_estimator import load_panel, build
rows,_=load_panel(REP/'2_reproduce')
results={}
for typ in ['house','condo']:
    pairs=build([r for r in rows if r['src']==typ],int(36*30.44))
    records=[]
    for a,z,da,dz in pairs:
        r={'bbl':a['bbl'],'borough':a['borough'],'date_a':da,'date_z':dz,'y':np.log(float(z['price'])/float(a['price']))}
        for side,s in [('a',a),('z',z)]:
            for w in ['base','strict','wide']:r[f'financed_{w}_{side}']=int(s[f'financed_{w}'])
        records.append(r)
    df=pd.DataFrame(records);_,df['cluster']=np.unique(df.bbl,return_inverse=True)
    results[typ]=estimate(df,design(df),df.cluster.max()+1)[0]
(OUT/'property_comparison.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2),flush=True)
