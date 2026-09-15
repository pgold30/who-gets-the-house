"""Retrieve fresh co-op audit data, with count-checked offset pagination."""
import json
from concurrent.futures import ThreadPoolExecutor,as_completed
from fetch_enrichment import get,DATA

def bulk(res,select,where,order,tag):
    n=int(get(res,{'$select':'count(*) as n','$where':where},tag+'_count')[0]['n'])
    print(tag,'expected',n,flush=True)
    def page(off):
        return get(res,{'$select':select,'$where':where,'$order':order,'$limit':50000,'$offset':off},tag+f'_{off:07}')
    rows=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for f in as_completed([pool.submit(page,off) for off in range(0,n,50000)]): rows+=f.result()
    assert len(rows)==n,(tag,len(rows),n)
    (DATA/(tag+'.json')).write_text(json.dumps(rows)); print(tag,'saved',len(rows),flush=True)
    return rows

if __name__=='__main__':
    # Include all sale prices and records without unit identifiers in the competing-sale count.
    sales=bulk('w2pb-icbu','sale_price,sale_date,borough,bbl,building_class_category,apartment_number,address',
        "sale_date >= '2015-01-01T00:00:00' AND sale_date < '2027-01-01T00:00:00' AND (building_class_category like '09%' OR building_class_category like '10%' OR building_class_category like '17%')",
        'sale_date,bbl,apartment_number,sale_price,address','coop_sales_all')
    master=bulk('sv7x-dduq','document_id,doc_type,recorded_datetime,document_amt',
        "document_id > '2015' AND document_id < '2027' AND doc_type='INIC'",'document_id','coop_inic_master')
    # All personal-property legals allow explicit multi-parcel exclusion. Pagination
    # never skips repeated document ids at a page boundary.
    bulk('uqqa-hym2','document_id,borough,block,lot,property_type',
        "document_id > '2015' AND document_id < '2027'",'document_id,borough,block,lot','coop_legals')
