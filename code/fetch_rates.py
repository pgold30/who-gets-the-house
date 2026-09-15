"""Obtain the public historical PMMS series from an official download endpoint."""
import urllib.request,csv,io,json,datetime as dt
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data'
URLS=['https://www.freddiemac.com/pmms/archive?year='+str(y) for y in range(2015,2026)]
def attempt(url):
    try:
        with urllib.request.urlopen(url,timeout=60) as r:data=r.read()
        return url,data,None
    except Exception as e:return url,None,str(e)
if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=4) as pool:
        for url,data,error in pool.map(attempt,URLS):
            print(url,error or (len(data),data[:60]),flush=True)
            if data:
                dest=DATA/('pmms_archive_'+url.split('=')[-1]+'.html')
                dest.write_bytes(data);dest.with_suffix(dest.suffix+'.source.txt').write_text(url+'\n')
