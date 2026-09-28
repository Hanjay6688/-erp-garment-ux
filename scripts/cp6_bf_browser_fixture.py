"""BF committed browser clone only. Master prerequisites; UI performs the SKU mutation."""
from urllib.parse import urlparse
import json,os,sys,uuid
import psycopg
import cp6_bf_probe as bf
from cp6_bd_modes import _fixture_usage

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];p=urlparse(target)
    assert p.hostname in ('127.0.0.1','localhost') and p.path=='/cp6_auditor_browser','BF_BROWSER_COPY_ONLY'
    value=json.loads(sys.argv[2])
    with psycopg.connect(target) as conn,conn.cursor() as cur:
      with _fixture_usage(cur):
        if sys.argv[1]=='create':
          tag='BFUI-'+uuid.uuid4().hex[:8];labels=['27'] if value['singleton'] else ['31','32','33','34']
          rows=bf.products(cur,labels,tag);out=dict(tag=tag,sku=tag+'-SKU',roots=[p for p,s in rows],sizes=[tag+'-'+s for s in labels],old_sku='CP6-E-'+tag)

        elif sys.argv[1]=='read':
          bf.b.api.admin(cur)
          groups=cur.execute('select s.sku,s.revision,v.settings,(select count(*) from erp.bf_sku_members_v1 m where m.version_id=v.id) from erp.bf_skus_v1 s join erp.bf_sku_versions_v1 v on v.sku_id=s.id and v.revision=s.revision where s.sku=%s',(value['sku'],)).fetchall()
          prices=cur.execute('select price::text from erp.product_price_versions where product_id=any(%s::uuid[]) order by product_id,effective_from',(value['roots'],)).fetchall()
          out=dict(groups=groups,prices=prices,stock=bf.one(cur,'select count(*) from erp.fg_stock_movements where product_id=any(%s::uuid[])',value['roots']))
        else:raise ValueError('BF_BROWSER_OPERATION')
      if sys.argv[1]=='create':conn.commit()
      else:conn.rollback()
    print(json.dumps(out,default=str))
if __name__=='__main__':main()
