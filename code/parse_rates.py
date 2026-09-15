"""Parse saved official Freddie Mac archive excerpts retrieved with web tools.

Bulk HTTP downloads returned 403/404. Raw excerpts and URLs are retained so
every parsed observation can be traced to an official table. No imputation.
"""
import re,json,csv,datetime as dt
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data'
pattern=re.compile(r'L\d+: ((?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, (\d{4}))\s*\n(?:(?!L\d+: (?:January|February|March|April|May|June|July|August|September|October|November|December)).){0,400}?Average Rates\s*\|\s*([0-9.]+)%',re.S)
rates={}
for year in range(2015,2026):
    lines={}
    for p in sorted(DATA.glob(f'pmms_web_{year}*.json')):
        for number,line in re.findall(r'^L(\d+): ?(.*)$',json.loads(p.read_text()),re.M):
            lines[int(number)]=line
    cur=None;prev=-1
    for number,line in sorted(lines.items()):
        if number!=prev+1:cur=None
        prev=number
        m=re.fullmatch(r'((?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4})\s*',line)
        if m:cur=dt.datetime.strptime(m[1],'%B %d, %Y').date()
        m=re.search(r'Average Rates\s*\|\s*([0-9.]+)%',line)
        if m and cur:
            assert cur.year==year
            v=float(m[1])
            if cur in rates:assert rates[cur]==v
            rates[cur]=v;cur=None
ordered=sorted(rates)
gaps=[(str(a),str(b),(b-a).days) for a,b in zip(ordered,ordered[1:]) if (b-a).days>8]
print('rates',len(rates),'by year',{y:sum(d.year==y for d in rates) for y in range(2015,2026)},'gaps',gaps,flush=True)
with (DATA/'MORTGAGE30US.csv').open('w') as f:
    w=csv.writer(f);w.writerow(['observation_date','MORTGAGE30US']);w.writerows((str(d),rates[d]) for d in ordered)
(DATA/'rates_validation.json').write_text(json.dumps({'observations':len(rates),'long_gaps':gaps,'source':'https://www.freddiemac.com/pmms/pmms_archives','retrieval':'official annual archive excerpts saved as pmms_web_YEAR.json; bulk download unavailable','series':'30-year fixed-rate mortgage average, percentage points','methodology_change':'2022-11-17'},indent=2))
