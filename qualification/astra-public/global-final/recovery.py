"""Exercise the S06 queue on an isolated, physically restored Global, with delivery disabled."""
from datetime import timedelta
from decimal import Decimal
import sys
import cp7_wa_forward_cases as wa
from common import *

ident_path=Path(os.environ['RUNNER_TEMP'])/'astra-recovery-ident.json'
def state(q,ids):
    owner=ids['owner']
    workspace=wa.rpc(q,'erp_list_my_reminders_v1',('ALL',200),owner)
    markers={ids['reminder'],ids.get('later')}
    docs={str(r['id']):{k:r.get(k)for k in ('id','title','status','row_version','due_at','created_at','updated_at')}for r in workspace['items'] if str(r['id']) in markers}
    admin(q)
    outbox=wa.outbox(q,ids['reminder'])
    digest=effects(q)
    for t in ['erp.manual_reminders','erp.audit_logs','cp7_alert_native.settings','cp7_alert_native.outbox']:
        digest[t]=first(q,"select md5(coalesce(string_agg(rowhash,'' order by rowhash),'')) from (select md5(to_jsonb(v)::text) rowhash from "+t+' v) d')
    funcs=first(q,"select jsonb_object_agg(p.oid::regprocedure::text,md5(pg_get_functiondef(p.oid))) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_alert_native' and p.proname in ('collect_tick','send_tick','analysis_tick','render','outbox_items')")
    jobs=q.execute("select jobid,jobname,active,schedule,command from cron.job where jobname in ('erp-wa-collect','erp-wa-send','erp-wa-analysis') order by jobname").fetchall()
    assert len(jobs)==3 and all(not r[2] for r in jobs)
    assert first(q,"select current_setting('cron.launch_active_jobs')")=='off'
    ext=dict(q.execute("select extname,extversion from pg_extension where extname in ('pg_cron','supabase_vault','pg_net')").fetchall())
    assert {'pg_cron','supabase_vault'} <= set(ext),ext
    workers=first(q,"select count(*) from cron.job_run_details where jobid=any(%s)",[r[0]for r in jobs])
    queue_exists=first(q,"select to_regclass('net.http_request_queue') is not null")
    queued=first(q,"select count(*) from net.http_request_queue") if queue_exists else None
    # The synthetic marker is verified by a digest. No decrypted Vault values ever leave the database.
    vault_hash=first(q,"select md5(decrypted_secret) from vault.decrypted_secrets where id=%s",ids['vault'])
    return dict(docs=docs,outbox=outbox,hashes=digest,functions=funcs,jobs=jobs,run_count=workers,http_queue=queued,http_queue_installed=queue_exists,vault_digest=vault_hash,
        versions=ext,sequences={t:first(q,'select jsonb_build_array(last_value,is_called) from '+t)for t in ('erp.audit_logs_id_seq','erp.cost_recalc_queue_id_seq')},
        enabled=first(q,'select (cp7_alert_native.current_settings()).enabled'))
def normal(v):
    return json.loads(json.dumps(v,default=str))
def main(phase):
    with psycopg.connect(**db()) as conn,conn.cursor() as q:
        seal=measure_seal(q)
        if phase=='seed':
            owner,_=actors(q)
            wa.save(q,owner,enabled=False,kinds=['MANUAL_REMINDER'],quiet_enabled=False,repeat_minutes=0)
            task=wa.reminder(q,owner,'Pengingat auditor untuk satu PO sintetis',wa.now(q)-timedelta(minutes=10))
            token=uuid.uuid4().hex
            vault=first(q,"select vault.create_secret(%s,%s,%s)",token,'astra25-'+uuid.uuid4().hex,'Penanda pemulihan sintetis')
            ident=dict(owner=owner,reminder=task['id'],vault=str(vault))
            collect=wa.tick(q,'collect_tick')
            obs=state(q,ident)
            assert task['id'] in obs['docs'] and not obs['enabled'] and obs['outbox']
            assert all(r['state']=='PENDING' and not r['attempts'] and r['dispatch'] is None for r in obs['outbox'])
            assert obs['vault_digest']==hashlib.md5(token.encode()).hexdigest()
            ident_path.write_text(json.dumps(ident))
            save('recovery-before',dict(seal=seal,observed=obs,collector=collect));return
        ident=json.loads(ident_path.read_text())
        before=read('recovery-before')['observed']
        if phase=='advance':
            v=state(q,ident)['docs'][ident['reminder']]
            wa.rpc(q,'erp_cancel_my_reminder_v1',(ident['reminder'],'Pembatalan sesudah cadangan sintetis',str(uuid.uuid4()),int(v['row_version'])),ident['owner'])
            later=wa.reminder(q,ident['owner'],'Pengingat sesudah cadangan sintetis',wa.now(q)+timedelta(days=1))
            ident['later']=later['id'];wa.tick(q,'collect_tick')
            obs=state(q,ident)
            assert later['id'] in obs['docs'] and obs['docs'][ident['reminder']]['status']=='CANCELLED'
            assert obs['hashes']['erp.audit_logs']!=before['hashes']['erp.audit_logs']
            ident_path.write_text(json.dumps(ident))
            save('recovery-later',dict(observed=obs));return
        assert phase=='restore'
        actual=normal(state(q,ident))
        assert actual==before,{'restore_difference':[k for k in actual if actual[k]!=before.get(k)]}
        assert ident['later'] not in actual['docs']
        sender=[wa.tick(q,'send_tick'),wa.tick(q,'send_tick')]
        assert all(row.get('outcome')=='WA_OFF'for row in sender),sender
        after=normal(state(q,ident))
        assert not after['enabled'] and [x['id'] for x in after['outbox']]==[x['id'] for x in before['outbox']]
        assert all(row['attempts']==0 and row['dispatch'] is None for row in after['outbox'])
        assert after['http_queue']==before['http_queue'] and after['http_queue'] in (None,0)
        assert after['run_count']==before['run_count']==0
        save('BR-T39',dict(outcome='PASS',seal=seal,compared_before_restore=actual==before,restored=actual,
                later_id=ident['later'],later_absent=True,send_ticks=sender,run_count_after=after['run_count'],http_queue_after=after['http_queue']))
if __name__=='__main__':
    try:main(sys.argv[1])
    except Exception as err:
        record_failure('BR-T39',err);raise
