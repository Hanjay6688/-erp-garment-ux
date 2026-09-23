"""Capture the native catalog of AV rev2 on exact AU in one rolled-back transaction; never a release gate.

Runs from the frozen AU writer checkout (ca7f095) on a disposable clone of the
exact AN boundary; AS/AT/AU are installed by their own closed-admission
runtimes. The proposal is applied inside a transaction that is rolled back.
Artifacts cannot be downloaded from the writer container, so the compact
capture (new object hashes, changed object keys, canonical definition hashes)
is also printed as one JSON line for extraction from the job log.
"""
from pathlib import Path
import hashlib,json,os,subprocess,sys,traceback
import psycopg

AUDITOR=Path(__file__).resolve().parents[1]
FROZEN='ca7f09556397801c50a2277bdb65b1bf019f9a05'
sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(AUDITOR/'scripts'))
import cp6_av_definitions as proposal
import cp6_au_trial as writer
import cp6_au_runtime as runtime
import cp6_ao_ap_runtime as prior
import cp6_successor_regression as boundary
from cp6_ao_ap_inventory import sha,function_pins

OUT=AUDITOR/'cp6-proof/av-capture'


def main():
    report=dict(status='INCOMPLETE',production_go=False,independent_acceptance=False,
                writer_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                auditor_head=subprocess.check_output(['git','-C',str(AUDITOR),'rev-parse','HEAD'],text=True).strip(),
                definitions_sha256=sha((AUDITOR/'scripts/cp6_av_definitions.py').read_bytes()),
                schema_sha256=sha(proposal.SCHEMA),triggers_sha256=sha(proposal.TRIGGERS))
    primary=None
    try:
        assert report['writer_head']==FROZEN,'AV_CAPTURE_WRITER_NOT_FROZEN_AU'
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:prior.verified(cur,'AN');primary=boundary.snapshot(cur)
        writer.install_at()
        report['au_install']=runtime.change('install',boundary.PG,os.environ['CP6_ADMISSION_CONTROL_PGURL'])['status']
        with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
            runtime.verified(cur);baseline=boundary.snapshot(cur)
            before=dict(objects=cur.execute(runtime.build.INVENTORY_SQL).fetchone()[0],functions=function_pins(cur))
            report['before_sha256']={k:sha(json.dumps(before[k],sort_keys=True,ensure_ascii=False)) for k in ('objects','functions')}
            report['before_counts']={k:len(v) for k,v in before.items()}
            report['old_definitions_match']={i:cur.execute('select pg_get_functiondef(to_regprocedure(%s))',(i,)).fetchone()[0]==old for i,old in proposal.OLD.items()}
            assert all(report['old_definitions_match'].values()),report['old_definitions_match']
            cur.execute('set local role postgres')
            cur.execute(proposal.SCHEMA,prepare=False)
            for text in proposal.NEW_FUNCTIONS.values():
                cur.execute(text,prepare=False)
            for identity in proposal.NEW_FUNCTIONS:
                cur.execute(f'revoke all on function {identity} from public,anon,authenticated,service_role')
            for text in proposal.FUNCTIONS.values():
                cur.execute(text,prepare=False)
            cur.execute(proposal.TRIGGERS,prepare=False)
            after=dict(objects=cur.execute(runtime.build.INVENTORY_SQL).fetchone()[0],functions=function_pins(cur))
            report['after_counts']={k:len(v) for k,v in after.items()}
            report['new_objects']={k:v for k,v in sorted(after['objects'].items()) if k not in before['objects']}
            report['removed_objects']=sorted(set(before['objects'])-set(after['objects']))
            report['changed_existing_objects']=sorted(k for k in before['objects'] if k in after['objects'] and before['objects'][k]!=after['objects'][k])
            canonical={i:cur.execute('select pg_get_functiondef(to_regprocedure(%s))',(i,)).fetchone()[0] for i in list(proposal.FUNCTIONS)+list(proposal.NEW_FUNCTIONS)}
            wanted={**proposal.FUNCTIONS,**proposal.NEW_FUNCTIONS}
            report['canonical_matches']={i:canonical[i]==wanted[i] for i in canonical}
            report['canonical_mismatch_text']={i:canonical[i] for i in canonical if canonical[i]!=wanted[i]}
            report['new_function_pins']={i:after['functions'][i] for i in proposal.NEW_FUNCTIONS}
            report['changed_function_pins']={i:after['functions'][i] for i in proposal.FUNCTIONS}
            cur.execute('savepoint coverage')
            try:
                result=cur.execute('select erp.assert_new_stock_cutoff_coverage_v1()').fetchone()[0]
                report['coverage']=dict(references=result['references'],new_stock_fact_tables=result['new_stock_fact_tables'])
                cur.execute('release savepoint coverage')
            except psycopg.Error as exc:
                report['coverage']=dict(error=str(exc).splitlines()[0]);cur.execute('rollback to savepoint coverage')
            report['native_product_references']=[r[0] for r in cur.execute("""select distinct format('%s.%s.%s',n.nspname,c.relname,a.attname)
                from pg_constraint fk join pg_class c on c.oid=fk.conrelid join pg_namespace n on n.oid=c.relnamespace
                join pg_attribute a on a.attrelid=c.oid and a.attnum=any(fk.conkey)
                where fk.contype='f' and fk.confrelid='erp.products'::regclass and fk.conrelid<>'erp.products'::regclass order by 1""").fetchall()]
            conn.rollback()
            runtime.verified(cur)
            report['complete_boundary_restored']=boundary.snapshot(cur)==baseline
            assert report['complete_boundary_restored']
            assert 'error' not in report['coverage'],report['coverage']
            assert all(report['canonical_matches'].values()),sorted(report['canonical_mismatch_text'])
            report['status']='CAPTURE_PASS'
    except Exception as exc:
        report.update(error=str(exc),traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN')
            report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        if not report['primary_unchanged'] or report['clone_remaining']:report['status']='INCOMPLETE'
        OUT.mkdir(parents=True,exist_ok=True)
        (OUT/'CATALOG.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    compact={k:v for k,v in report.items() if k!='traceback'}
    print('AV_CAPTURE_JSON '+json.dumps(compact,sort_keys=True,default=str),flush=True)
    assert report['status']=='CAPTURE_PASS',report.get('error')


if __name__=='__main__':main()
