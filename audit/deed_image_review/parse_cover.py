import re,glob,json,os
def norm(s): return re.sub(r'[^A-Z0-9]','',re.sub(r'\b(STREET|ST|AVENUE|AVE|ROAD|RD|PLACE|PL|COURT|CT|DRIVE|DR|APT\.?.*)$','',s.upper()))
out={}
for f in sorted(glob.glob('ocr/*.txt')):
    d=os.path.basename(f)[:-4]; t=open(f).read()
    cover=t.split(f'=== images/{d}_p02')[0]
    L=[x.strip() for x in cover.split('\n')]
    def after(tag):
        for i,x in enumerate(L):
            if tag in x.upper():
                blk=[y for y in L[i+1:i+5] if y and not y.upper().startswith(('CROSS','OR','YEAR','REEL','PAGE','PARTIES','FEES','X','XI'))]
                return blk[:3]
        return []
    g=after('GRANTOR/SELLER'); b=after('GRANTEE/BUYER')
    m=re.search(r'Real Property Transfer Tax:\s*\n?\s*([\d,]+\.\d\d)',cover)
    rptt=None
    if m: rptt=float(m.group(1).replace(',',''))
    else:
        i=cover.find('NYC Real Property Transfer Tax')
        m2=re.search(r'([\d,]{1,9}\.\d\d)',cover[i:i+80]) if i>=0 else None
        rptt=float(m2.group(1).replace(',','')) if m2 else None
    nys=None
    j=cover.find('NYS Real Estate Transfer Tax')
    if j>=0:
        m3=re.search(r'([\d,]{1,9}\.\d\d)',cover[j:j+80]); nys=float(m3.group(1).replace(',','')) if m3 else None
    same=None
    if len(g)>=2 and len(b)>=2: same = norm(g[1])==norm(b[1])
    out[d]={'first_grantor':g,'first_grantee':b,'cover_first_addresses_same':same,'nyc_rptt':rptt,'nys_rett':nys,'consideration_implied_by_nys_tax_at_0.4pct':(round(nys/0.004) if nys is not None else None)}
json.dump(out,open('cover_parse.json','w'),indent=1)
for d,v in out.items(): print(d,v['cover_first_addresses_same'],v['nyc_rptt'],v['nys_rett'],v['consideration_implied_by_nys_tax_at_0.4pct'],v['first_grantor'][:2],'|',v['first_grantee'][:2])
