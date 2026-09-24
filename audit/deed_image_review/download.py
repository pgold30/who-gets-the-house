import csv,re,urllib.request,urllib.error,time,json,os,glob,sys
q=list(csv.DictReader(open('/Users/pablo/Downloads/paper_nyc/ASTRA_AUDIT_2026-09-24_V3/deed_review_queue.csv')))
H={'User-Agent':'Mozilla/5.0'}
meta=json.load(open('page_counts.json')) if os.path.exists('page_counts.json') else {}
def get(url):
    for k in range(8):
        try: return urllib.request.urlopen(urllib.request.Request(url,headers=H),timeout=60).read()
        except urllib.error.HTTPError as e:
            print('HTTP',e.code,url[-40:],'sleep',30*(k+1),flush=True); time.sleep(30*(k+1))
        except Exception as e:
            print('ERR',e,flush=True); time.sleep(10*(k+1))
    raise RuntimeError(url)
for r in q:
    d=r['document_id']
    have=glob.glob(f'images/{d}_p*.tif')
    if d not in meta:
        html=get(f'https://a836-acris.nyc.gov/DS/DocumentSearch/DocumentImageView?doc_id={d}').decode()
        m=re.search(r'hid_TotalPages%22%3A(\d+)',html); meta[d]=int(m.group(1)) if m else 0
        json.dump(meta,open('page_counts.json','w'),indent=1); time.sleep(3)
    for p in range(1,meta[d]+1):
        f=f'images/{d}_p{p:02d}.tif'
        if os.path.exists(f) and os.path.getsize(f)>1000: continue
        b=get(f'https://a836-acris.nyc.gov/DS/DocumentSearch/GetImage?doc_id={d}&page={p}')
        if not b.startswith(b'II*') and not b.startswith(b'MM'): raise RuntimeError('not a TIFF '+f)
        open(f,'wb').write(b); time.sleep(2)
    print('done',d,meta[d],flush=True)
print('ALL DONE',len(meta),sum(meta.values()),flush=True)
