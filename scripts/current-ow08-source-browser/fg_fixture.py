"""Retained Native FG/QC fixtures; browser witnesses only navigation/readability."""
from pathlib import Path
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from cp7_fg_correction_source import cases as fg
import cp7_ow04_restore_bundle as catalog
operation=sys.argv[1];payload=json.loads(sys.stdin.read())
url=os.environ['AUDITOR_BROWSER_DB_URL'];address=urlparse(url)
assert address.hostname in('127.0.0.1','localhost')and address.path=='/cp6_auditor_browser'
with psycopg.connect(url)as connection,connection.cursor()as cur:
    assert cur.execute('select current_database()').fetchone()[0]=='cp6_auditor_browser'
    fg.b.api.admin(cur)
    if operation=='state':
        result=catalog._data(cur);connection.rollback()
    elif operation=='prepare':
        grant=not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if grant:cur.execute('grant usage on schema erp to authenticated')
        try:
            today=date.fromisoformat(payload['today'])
            blocked=fg.chain(cur,today,'BLOCKUI');sale=fg.draft_sale(cur,blocked,2);adjustment=fg.adjust(cur,blocked,'-1')
            history=fg.history(cur,blocked)
            assert history['reversible']is False
            assert sale['number']in history['reversal_blocker']and adjustment['number']in history['reversal_blocker']
            inv=fg.chain(cur,today,'INVUI');a=fg.adjust(cur,inv,'-1');fg.fgadj.action(cur,'REVERSE',a['posted']);fg.b.api.admin(cur)
            movement=cur.execute("""select id::text,source_type,source_id::text from erp.fg_stock_movements
                where reversal_of_id=%s and source_type='FG_MOVEMENT_REVERSAL'""",(a['movement'],)).fetchall()
            assert len(movement)==1
            lot=fg.one(cur,'select lot_number from erp.fg_lots where id=%s',(inv['lot'],))
            result=dict(blocked=dict(qc_id=blocked['qc'],qc_number=blocked['qc_number'],blocker=history['reversal_blocker'],sale=sale['number'],adjustment=adjustment['number']),
                inverse=dict(lot_id=inv['lot'],lot_number=lot,movement_id=movement[0][0],source_type=movement[0][1],source_id=movement[0][2],adjustment_id=a['id'],number=a['number']),
                fixture_source='EXISTING_NATIVE_CHAIN_ADJUSTMENT_AND_INVERSE_NOT_SCREEN_CREATION')
        except Exception:
            connection.rollback();raise
        finally:
            fg.b.api.admin(cur)
            if grant:cur.execute('revoke usage on schema erp from authenticated')
        connection.commit()
    else:raise ValueError('UNDECLARED_OW08_FG_FIXTURE_OPERATION')
print(json.dumps(result,default=str))
