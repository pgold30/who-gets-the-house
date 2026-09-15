"""Read-only public sources; restartable per-request caches; no credentials."""
import csv,gzip,json,datetime as dt,urllib.request,urllib.parse,time,sys,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[1]
REP=ROOT/'inputs'
DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
CACHE=DATA/'api_cache'; CACHE.mkdir(exist_ok=True)
sys.path.insert(0,str(REP/'3_section4.9'))
from legacy_estimator import load_panel

def get(resource,params,tag):
    dest=CACHE/(tag+'.json')
    if dest.exists(): return json.loads(dest.read_text())
    url='https://data.cityofnewyork.us/resource/'+resource+'.json?'+urllib.parse.urlencode(params)
    for retry in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'NYC-paper-revision/1.0'}),timeout=120) as r: out=json.load(r)
            dest.write_text(json.dumps(out)); (CACHE/(tag+'.url.txt')).write_text(url+'\n')
            return out
        except Exception:
            if retry==4: raise
            time.sleep(2*(retry+1))

def main():
    _,pairs=load_panel(REP/'2_reproduce')
    bbls=sorted({a['bbl'] for a,z,da,dz in pairs})
    deeds=json.loads((REP/'3_section4.9/deeds_for_pairs.json').read_text())
    docids=set()
    for a,z,da,dz in pairs:
        for s,date in [(a,da),(z,dz)]:
            cand=[(abs((dt.date.fromisoformat(d)-date).days),did) for d,did in deeds.get(s['bbl'],[]) if abs((dt.date.fromisoformat(d)-date).days)<=45]
            if cand:
                best=min(x[0] for x in cand)
                docids.update(did for gap,did in cand if gap==best)
    tasks=[]
    for i in range(0,len(bbls),150):
        where='bbl in('+','.join(bbls[i:i+150])+')'
        tasks.append(('geo', '64uk-42ks', {'$select':'bbl,zipcode,cd,bct2020,version','$where':where,'$limit':50000},f'geo_{i:05}'))
    ids=sorted(docids)
    for i in range(0,len(ids),150):
        where="document_id in("+','.join("'"+s+"'" for s in ids[i:i+150])+')'
        tasks.append(('parties','636b-3b5g',{'$select':'document_id,party_type,name','$where':where+" AND party_type in('1','2')",'$limit':50000},f'parties_{i:05}'))
        tasks.append(('master','bnx9-e6tj',{'$select':'document_id,doc_type,document_date,document_amt,recorded_datetime','$where':where,'$limit':50000},f'master_{i:05}'))
    outputs={k:[] for k in ['geo','parties','master']}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures={pool.submit(get,res,params,tag):(kind,tag) for kind,res,params,tag in tasks}
        for j,f in enumerate(as_completed(futures)):
            kind,tag=futures[f]; rows=f.result(); assert len(rows)<50000,(tag,'possible truncation')
            outputs[kind]+=rows
            if j%25==0: print('fetched',j+1,'/',len(tasks),flush=True)
    for kind,rows in outputs.items():
        (DATA/(kind+'.json')).write_text(json.dumps(rows));print(kind,len(rows),flush=True)
    url='https://www.freddiemac.com/pmms/docs/PMMS_history.csv'
    rate=DATA/'MORTGAGE30US.csv'
    if not rate.exists():
        with urllib.request.urlopen(url,timeout=120) as r: (DATA/'PMMS_history.csv').write_bytes(r.read())
        raw=list(csv.DictReader((DATA/'PMMS_history.csv').open(encoding='utf-8-sig')))
        print('PMMS columns',list(raw[0]),flush=True)
    (DATA/'MORTGAGE30US.source.txt').write_text('https://www.freddiemac.com/pmms/pmms_archives\nFreddie Mac, Primary Mortgage Market Survey. Annual archive tables were retrieved with web tools and saved as pmms_web_YEAR.json after bulk download endpoints failed. parse_rates.py constructs the analysis CSV. Methodology changed November 17, 2022.\n')
    (DATA/'retrieval_metadata.json').write_text(json.dumps({'retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'house_bbls':len(bbls),'requested_deeds':len(ids),'sources':{'geography':'64uk-42ks','parties':'636b-3b5g','master':'bnx9-e6tj'},'rows':{k:len(v) for k,v in outputs.items()}},indent=2))
if __name__=='__main__': main()
