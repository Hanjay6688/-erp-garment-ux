#!/usr/bin/env python3
"""T3: AW, AX, AY, AZ and BA as release candidates of the combined package, with the AO..AV guard set.

AW (close readiness engine) and AX (finished goods without a production source) passed T1 as development files
(supabase/dev/cp6_aw_t1_family.sql, cp6_ax_t1_family.sql). This builder wraps each T1 body unchanged (only the ledger
description stops saying "development install") with the guards AO..AV carry:
  * closed and drained admission, ledger and business tables locked (AV's blocks, verbatim);
  * admission: own marker, own capsule and own new tables absent;
  * every earlier file of the package (AC..AV, and AW for AX) present in both ledgers with the exact statements sha256,
    and nothing after the immediate predecessor;
  * the whole erp/public catalog pinned before and after (AV's query; the AW/AX capsules are left out by name like
    AO..AV's own);
  * every historical rollback capsule pinned by content hash, now including AO..AV (and AW for AX), and every AO..AV
    capsule checked for security, shape (AN template) and boundary like AV's per-capsule guards;
  * an own rollback capsule of the functions the file replaces (AW: 2; AX: 2, the payroll work-item validator and the
    merge RPC that learn the FG_REPAIR repair-wage source), completeness
    checked against every erp/public function before the body, and a before/after hash of every erp table (the install
    changes no data; new tables stay empty).
The capsule and catalog pins start as placeholders that refuse, until scripts/cp6_t3_release_package.py capture derives
the live values on the hosted-faithful chain; ledger pins cascade like the rest of the package. No rollback file yet
(NOT_TESTED, as for the whole package). Label: T3_PREP.

Usage: python scripts/cp6_t3_awx_release.py
"""
from pathlib import Path
import json,re,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import cp6_t3_release_package as package
import cp6_ba_build as ba

SRC=ROOT/'supabase/release/cp6-t3-src'
MIGRATIONS=ROOT/'supabase/migrations'
AV=next(MIGRATIONS.glob('*_erp_v2_6_20av_*.sql'))
FILES=[
    dict(key='AW',stamp='20260924010000',name='erp_v2_6_20aw_cp6_close_readiness_engine',version='v2.6.20aw',
         body=ROOT/'supabase/dev/cp6_aw_t1_family.sql',title='close readiness engine (one engine for preflight, close and the owner report)',
         description='Close readiness engine: preflight, close and report share one per-date engine',
         replaced=['erp.close_accounting_through(date,text)','erp.get_owner_financial_snapshot_v2(date,date,date)'],
         new_tables=['accounting_close_filings_v1','laundry_rate_owner_estimates_v1']),
    dict(key='AX',stamp='20260924010100',name='erp_v2_6_20ax_cp6_fg_unsourced_receipts',version='v2.6.20ax',
         body=ROOT/'supabase/dev/cp6_ax_t1_family.sql',title='finished goods without a production source',
         description='Finished goods without a production source: owner receipt with average HPP and reversal',
         replaced=['erp.merge_eligible_work_into_payroll_v2(uuid,jsonb,uuid,bigint)','erp.validate_payroll_work_item_source()'],
         new_tables=['fg_unsourced_receipts_v1','fg_unsourced_repair_wages_v1']),
    dict(key='AY',stamp='20260924010200',name='erp_v2_6_20ay_cp6_hpp_dated_from_goods',version='v2.6.20ay',
         body=ROOT/'supabase/dev/cp6_ay_t1_family.sql',title='PO HPP corrections dated from the goods',
         description='PO HPP corrections dated from the goods: FG from the lot date, COGS from the sale date',
         replaced=['erp.sync_po_hpp_to_gl(uuid,date)','erp.rebuild_po_hpp(uuid,text)'],new_tables=['po_hpp_gl_lot_state_v1','po_hpp_gl_material_state_v1']),
    dict(key='AZ',stamp='20260924010300',name='erp_v2_6_20az_cp6_material_recost_dated_from_movement',version='v2.6.20az',
         body=ROOT/'supabase/dev/cp6_az_t1_family.sql',title='material recost corrections dated from the physical movement',
         description='Material recost corrections dated from the physical movement: WIP from the cutting day, material until then',
         replaced=['erp.sync_material_cost_revaluation(uuid)','erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)',
                   'erp.sync_finished_po_wip_residual(uuid,date,text)','erp.guard_pocket_period_v1()',
                   'erp.sync_initial_import_bs_value_v1(uuid,date)','erp.sync_non_po_product_hpp_to_gl_v2620f(uuid,date,text,uuid,text)',
                   'erp.refresh_accessory_hpp_after_material_recost(uuid,text)','erp.reverse_qc(uuid,text)',
                   'erp.reverse_rework_completion(uuid,text)','erp.complete_initial_import_wip_v1(jsonb)',
                   'erp.post_material_supplier_invoice(uuid)','erp.post_material_purchase_cost_correction(uuid)'],new_tables=[]),
    dict(key='BA',stamp='20260925010000',name='erp_v2_6_20ba_cp6_audit_closure',version='v2.6.20ba',
         body=ROOT/'supabase/dev/cp6_ba_t1_family.sql',title='independent audit closure (import identity, dated WIP and advance capacity, WIP product binding, recost cents, selectors, single close filing)',
         description='Independent audit closure: import identity, dated WIP and advance capacity, WIP product binding, recost cents, selectors, single close filing',
         replaced=list(ba.REPLACED),new_tables=list(ba.NEW_TABLES)),
]
PLACEHOLDER='0'*64
# The package capsules AO..AV (AO..AW for AX) are checked like AV checks AO..AU; the capsules of this builder are left out
# of the catalog pin by name, as AO..AV leave out their own.
PACKAGE_CAPSULES=['ao','ap','aq','ar','as','at','au','av']
OWN_CAPSULES="'cp6_v2620av_rollback_capsule','cp6_v2620aw_rollback_capsule','cp6_v2620ax_rollback_capsule')"
SHAPE=("jsonb_build_object(\n"
       "   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid=%(rel)s),\n"
       "   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=%(rel)s and a.attnum>0 and not a.attisdropped),\n"
       "   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid=%(rel)s),\n"
       "   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid=%(rel)s))")
SECURITY=("not exists(select 1 from pg_class where oid=%(rel)s and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')\n"
          "   or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid=%(rel)s and a.grantee<>p.relowner)\n"
          "   or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid=%(rel)s and a.grantee<>'postgres'::regrole)\n"
          "   or exists(select 1 from pg_policy where polrelid=%(rel)s)\n"
          "   or exists(select 1 from pg_trigger where tgrelid=%(rel)s and not tgisinternal)")
DATA=("execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) "
      "from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;")
LEDGER_HASH="encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex')"
FUNCTIONS=("select p.oid::regprocedure::text as identity,encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') as definition_sha256,\n"
           "  array(select a::text from unnest(p.proacl)a order by a::text) as acl,pg_get_userbyid(p.proowner) as owner\n"
           " from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p')")


def block(text,name):
    m=re.search(r"do \$%s\$.*?end \$%s\$;\n"%(name,name),text,re.S)
    assert m,name
    return m.group(0)


def body(path,version,description):
    lines=path.read_text().splitlines(keepends=True)
    assert lines[2]=='begin;\n' and lines[-1]=='commit;\n'
    inner=''.join(lines[3:-1])
    marker=re.compile(r"insert into erp\.schema_migrations\(version,description\) values\('%s','[^']*'\);\n"%re.escape(version))
    assert len(marker.findall(inner))==1
    return marker.sub("insert into erp.schema_migrations(version,description) values('%s','%s');\n"%(version,description),inner)


def catalog_guard(inner,agg,code):
    return ("do $catalog_guard$\ndeclare actual jsonb;fingerprint text;object_count bigint;\nbegin\n select * into actual from (\n%s\n) catalog;\n"
            " select count(*),%s into object_count,fingerprint from jsonb_each_text(actual);\n if object_count<>0 or fingerprint is distinct from '%s' then\n"
            "  raise exception '%s';\n end if;\nend $catalog_guard$;\n")%(inner,agg,PLACEHOLDER,code)


def migration(key):
    [path]=sorted(MIGRATIONS.glob('*_erp_v2_6_20%s_*.sql'%key))
    stamp,name=re.match(r'(\d{14})_(.+)\.sql$',path.name).groups()
    return dict(marker='v2.6.20'+key,stamp=stamp,name=name,sha=package.sha(path.read_text()))


def admission(f,capsule):
    new=' or '.join("to_regclass('erp.%s') is not null"%t for t in f['new_tables']) or 'false'
    return ("do $admission$ begin\n if exists(select 1 from erp.schema_migrations where version='%s') or to_regclass('%s') is not null\n  or %s\n"
            " then raise exception '%s_EXACT_PREDECESSOR_WITHOUT_SUCCESSOR_REQUIRED';end if;\nend $admission$;\n")%(f['version'],capsule,new,f['key'])


def predecessor(code,previous):
    return ("do $predecessor$\nbegin\n if exists(select 1 from supabase_migrations.schema_migrations where version>'%s') then raise exception '%s_EXACT_PREDECESSOR_REQUIRED';end if;\nend $predecessor$;\n"
            )%(previous[-1]['stamp'],code)


def prior_platform(code,previous):
    """Every earlier file of the package, in both ledgers, with the exact statements sha256 (AV checks each of AO..AU)."""
    rows=json.dumps(previous,separators=(',',':'))
    return ("do $prior_platform$\ndeclare r record;\nbegin\n for r in select * from jsonb_to_recordset('%s'::jsonb) as x(marker text,stamp text,name text,sha text) loop\n"
            "  if not exists(select 1 from erp.schema_migrations where version=r.marker)\n"
            "   or (select count(*) from supabase_migrations.schema_migrations where name=r.name)<>1\n"
            "   or not exists(select 1 from supabase_migrations.schema_migrations where version=r.stamp and name=r.name\n"
            "    and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')=r.sha) then\n"
            "   raise exception '%s_PRIOR_PLATFORM_DRIFT: %%',r.name;\n  end if;\n end loop;\nend $prior_platform$;\n")%(rows,code)


def historical(av_history,capsules,code):
    pins=dict(av_history['pins']);pins.update({c:PLACEHOLDER for c in capsules})
    text=("do $historical_capsules$\ndeclare r record;actual text;\nbegin\n for r in select * from jsonb_each_text('%s'::jsonb) loop\n"
          "  execute format($caps$%s$caps$,r.key) into actual;\n  if actual is distinct from r.value then raise exception '%s_HISTORICAL_CAPSULE_DRIFT: %%',r.key;end if;\n"
          " end loop;\nend $historical_capsules$;\n")%(json.dumps(pins,sort_keys=True,separators=(',',':')),av_history['query'],code)
    parsed=package.history(text)
    assert parsed and parsed['pins']==pins and parsed['query']==av_history['query']
    return text


def prior_capsules(code,capsules):
    """AV's per-capsule checks for every package capsule: owner-only access, AN shape, one complete boundary."""
    rels=','.join("'erp.%s'"%c for c in capsules)
    return ("do $prior_capsules$\ndeclare r record;expected jsonb;actual jsonb;bad bigint;\nbegin\n"
            " select %s into expected;\n"
            " for r in select unnest(array[%s]::regclass[]) as rel loop\n"
            "  if %s then raise exception '%s_PRIOR_CAPSULE_SECURITY: %%',r.rel;end if;\n"
            "  select %s into actual;\n"
            "  if actual is distinct from expected then raise exception '%s_PRIOR_CAPSULE_SHAPE_DRIFT: %%',r.rel;end if;\n"
            "  execute format($b$select count(*) filter(where boundary_snapshot is null or not(boundary_snapshot ?& array['before','after','platform_before','markers_before']))\n"
            "   +(case when count(distinct boundary_snapshot)=1 then 0 else 1 end) from %%s$b$,r.rel) into bad;\n"
            "  if bad<>0 then raise exception '%s_PRIOR_CAPSULE_BOUNDARY: %%',r.rel;end if;\n"
            " end loop;\nend $prior_capsules$;\n")%(SHAPE%dict(rel="'erp.cp6_v2620an_rollback_capsule'::regclass"),rels,SECURITY%dict(rel='r.rel'),code,
                                                      SHAPE%dict(rel='r.rel'),code,code)


def capsule_create(f,capsule):
    ids=','.join("'%s'"%i for i in f['replaced'])
    text=("create table %(c)s(like erp.cp6_v2620an_rollback_capsule including all);\n"
          "alter table %(c)s enable row level security;\n"
          "revoke all on %(c)s from public,anon,authenticated,service_role;\n")%dict(c=capsule)
    if f['replaced']:
        text+=("insert into %s(object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot)\n"
               "select format('%%I.%%I(%%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),i.identity,pg_get_functiondef(p.oid),\n"
               " encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),\n"
               " array(select a::text from unnest(p.proacl)a order by a::text),pg_get_userbyid(p.proowner)\n"
               "from unnest(array[%s]) i(identity)\njoin pg_proc p on p.oid=i.identity::regprocedure join pg_namespace n on n.oid=p.pronamespace;\n")%(capsule,ids)
    # Every erp/public function before the body, to prove afterwards that the capsule holds every one the body changed.
    text+="create temp table cp6_release_functions on commit drop as\n%s;\n"%FUNCTIONS
    return text


def before_data(capsule):
    return ("do $before_data$ declare v_table text;v_hash jsonb;v_before jsonb; begin\n v_before:='{}'::jsonb;\n"
            " for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace\n"
            "  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','%s']::text[]) order by 1 loop\n"
            "  %s\n  v_before:=v_before||jsonb_build_object(v_table,v_hash);\n end loop;\n"
            " create temp table cp6_release_boundary on commit drop as select jsonb_build_object('before',v_before,\n"
            "  'platform_before',(select %s from supabase_migrations.schema_migrations t),\n"
            "  'markers_before',(select %s from erp.schema_migrations t)) snapshot;\nend $before_data$;\n")%(capsule.split('.')[1],DATA,LEDGER_HASH,LEDGER_HASH)


def after_data(f,capsule):
    new="array[%s]::text[]"%','.join("'%s'"%t for t in f['new_tables'])
    return ("update %(c)s set installed_definition_sha256=encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex');\n"
            "do $after_data$ declare v_table text;v_hash jsonb;v_after jsonb;v_before jsonb; begin\n v_after:='{}'::jsonb;\n"
            " for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace\n"
            "  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','%(t)s']::text[]) order by 1 loop\n"
            "  %(data)s\n  v_after:=v_after||jsonb_build_object(v_table,v_hash);\n end loop;\n"
            " select snapshot->'before' into v_before from pg_temp.cp6_release_boundary;\n"
            " if (v_after-%(new)s) is distinct from v_before or exists(select 1 from unnest(%(new)s) t where (v_after->t->>'count') is distinct from '0')\n"
            "  then raise exception '%(k)s_INSTALL_CHANGED_DATA';end if;\n"
            " if exists(with live as (%(fn)s) select 1 from pg_temp.cp6_release_functions f left join live x on x.identity=f.identity\n"
            "  where f.identity<>all(coalesce((select array_agg(object_regidentity) from %(c)s),'{}'))\n"
            "  and (x.identity is null or (x.definition_sha256,x.acl,x.owner) is distinct from (f.definition_sha256,f.acl,f.owner)))\n"
            "  then raise exception '%(k)s_CAPSULE_INCOMPLETE';end if;\n"
            " update %(c)s set boundary_snapshot=(select snapshot from pg_temp.cp6_release_boundary)||jsonb_build_object('after',v_after);\n"
            "end $after_data$;\n")%dict(c=capsule,t=capsule.split('.')[1],data=DATA,new=new,k=f['key'],fn=FUNCTIONS)


def capsule_guard(f,capsule):
    return ("do $capsule_guard$\ndeclare expected jsonb;actual jsonb;boundary jsonb;\nbegin\n"
            " if %(sec)s\n   or (select count(*) from %(c)s)<>%(n)d then raise exception '%(k)s_CAPSULE_SECURITY_OR_COUNT';end if;\n"
            " select %(an)s into expected;\n select %(own)s into actual;\n"
            " if actual is distinct from expected then raise exception '%(k)s_CAPSULE_SHAPE_DRIFT';end if;\n"
            " select boundary_snapshot into boundary from %(c)s limit 1;\n"
            " if %(n)d>0 and (boundary is null or exists(select 1 from %(c)s where boundary_snapshot is distinct from boundary)\n"
            "  or not(boundary ?& array['before','after','platform_before','markers_before'])) then raise exception '%(k)s_CAPSULE_BOUNDARY';end if;\n"
            " if exists(select 1 from %(c)s where object_regidentity<>all(array[%(ids)s]::text[])\n"
            "   or definition_sha256 is distinct from encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex')\n"
            "   or installed_definition_sha256 is null or installed_definition_sha256=definition_sha256\n"
            "   or installed_definition_sha256 is distinct from encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex'))\n"
            "  then raise exception '%(k)s_CAPSULE_SOURCE_DRIFT';end if;\n"
            "end $capsule_guard$;\n")%dict(sec=SECURITY%dict(rel="'%s'::regclass"%capsule),c=capsule,n=len(f['replaced']),k=f['key'],
                                          an=SHAPE%dict(rel="'erp.cp6_v2620an_rollback_capsule'::regclass"),own=SHAPE%dict(rel="'%s'::regclass"%capsule),
                                          ids=','.join("'%s'"%i for i in f['replaced']) or "''")


def build():
    av=AV.read_text()
    closed=block(av,'closed_admission');business=block(av,'lock_business')
    guard=package.catalog_blocks(av)[1]
    assert guard['inner'].count("'cp6_v2620av_rollback_capsule')")==1
    inner=guard['inner'].replace("'cp6_v2620av_rollback_capsule')",OWN_CAPSULES)
    av_history=package.history(av)
    SRC.mkdir(parents=True,exist_ok=True)
    previous=[migration(k) for k in package.KEYS[:package.KEYS.index('av')+1]]
    capsules=['cp6_v2620%s_rollback_capsule'%k for k in PACKAGE_CAPSULES]
    out=[]
    for f in FILES:
        code=f['key'];capsule='erp.cp6_v2620%s_rollback_capsule'%code.lower()
        text=("-- CP6 %s: %s. Release candidate of the T3 combined package; closed, drained maintenance required.\n"
              "begin;\n"
              "-- Built by scripts/cp6_t3_awx_release.py from %s (sha256 %s): the T1 body below is unchanged apart from the\n"
              "-- ledger description; guards follow AO..AV. Capsule and catalog pins are placeholders until the T3 capture.\n"
              "set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';set local search_path='';\n"
              "set local role postgres;\n")%(code,f['title'],f['body'].relative_to(ROOT),package.sha(f['body'].read_text()))
        text+=closed
        text+="lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;\n"
        text+=business+admission(f,capsule)+predecessor(code,previous)+prior_platform(code,previous)
        # AW and AX leave out the capsules AV..AX by name; each later file adds the capsules after AX up to its own
        # (AY: ay; AZ: ay, az), so the AY text is unchanged.
        later=[c['key'].lower() for c in FILES[FILES.index(f)::-1] if c['key'] not in ('AW','AX')][::-1]
        own=inner if code in ('AW','AX') else inner.replace("'cp6_v2620ax_rollback_capsule')","'cp6_v2620ax_rollback_capsule',%s)"%
                                                              ','.join("'cp6_v2620%s_rollback_capsule'"%k for k in later))
        text+=catalog_guard(own,guard['agg'],code+'_PREDECESSOR_CATALOG_DRIFT')
        text+=historical(av_history,capsules,code)+prior_capsules(code,capsules)
        text+=capsule_create(f,capsule)+before_data(capsule)
        text+=body(f['body'],f['version'],f['description'])
        text+=catalog_guard(own,guard['agg'],code+'_INSTALLED_CATALOG_DRIFT')
        text+=after_data(f,capsule)+capsule_guard(f,capsule)
        text+="commit;\n"
        assert len(package.catalog_blocks(text))==2 and package.history(text)
        path=SRC/('%s_%s.sql'%(f['stamp'],f['name']))
        path.write_text(text)
        out.append((path.relative_to(ROOT),package.sha(text)))
        previous=previous+[dict(marker=f['version'],stamp=f['stamp'],name=f['name'],sha=package.sha(text))]
        capsules=capsules+[capsule.split('.')[1]]
    for p,s in out:print(p,s)


if __name__=='__main__':build()
