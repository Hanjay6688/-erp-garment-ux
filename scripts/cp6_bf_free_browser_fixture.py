"""Only master prerequisites on the committed browser copy; the UI saves the SKU."""
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp6_bf_free_probe as free
from cp6_bd_modes import _fixture_usage

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];p=urlparse(target)
    assert p.hostname in ('127.0.0.1','localhost') and p.path=='/cp6_auditor_browser','SKU_FREE_BROWSER_COPY_ONLY'
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        with _fixture_usage(cur):
            f=free.master_fixture(cur)
            sizes=[free.one(cur,'select size_code from erp.sizes where id=%s',s) for _,s in f['rows']]
            out=dict(tag=sizes[0].rsplit('-',1)[0],sku=f['g']['sku'],roots=[r for r,_ in f['rows']],sizes=sizes,rates=f['rates'])
        conn.commit()
    print(json.dumps(out))
if __name__=='__main__':main()
