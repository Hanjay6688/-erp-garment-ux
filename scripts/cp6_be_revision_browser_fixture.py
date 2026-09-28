"""Prepare 52 real allocation histories in the disposable browser copy only."""
from datetime import date
from urllib.parse import urlparse
import os,json,sys
import psycopg
import cp6_be_revision_probe as r
from cp6_bd_modes import _fixture_usage

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];p=urlparse(target)
    assert p.hostname in ('127.0.0.1','localhost') and p.path=='/cp6_auditor_browser','BE_REV_BROWSER_COPY_ONLY'
    f=json.loads(sys.argv[2])
    with psycopg.connect(target) as conn,conn.cursor() as cur:
      with _fixture_usage(cur):
        if sys.argv[1]=='create':out=r.pocket_many(cur,date.fromisoformat(f['today']),25,23)
        elif sys.argv[1]=='read':out=dict(state=r.one(cur,'select erp.pocket_period_state_v1(%s)',f['id']),
          stock=r.one(cur,'select count(*) from erp.material_stock_movements'),ledger=r.be.pocket_probe.amounts(cur),
          cancellations=r.one(cur,"select count(*) from erp.pocket_period_events where pool_id=%s and kind='CANCEL'",f['id']))
        else:raise ValueError('BE_REV_BROWSER_OPERATION')
      if sys.argv[1]=='create':conn.commit()
      else:conn.rollback()
    print(json.dumps(out,default=str))
if __name__=='__main__':main()
