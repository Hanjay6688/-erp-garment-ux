#!/usr/bin/env python3
"""AM transfer family, with exact AL admission and pre-use rollback."""
from pathlib import Path
import json
import cp6_v2620al_build_sql as prior
from cp6_v2620am_definitions import IDENTITIES, definitions

STAMP='20260921214120'
NAME='erp_v2_6_20am_cp6_transfer_integrity'
VERSION='v2.6.20am'
PREDECESSOR_HEAD='4e74e25270c6a062d98e1adaa58cf50ea22e2e8c'
PREDECESSOR_TREE='da287f7d1d0ef429e244fafef37e0bb4a1c42b94'
MIGRATION=Path(f'supabase/migrations/{STAMP}_{NAME}.sql')
ROLLBACK=Path(f'supabase/rollbacks/{STAMP}_{NAME}.rollback.sql')
PINS=Path('docs/evidence/cp6-am-runtime-pins.json')
INPUT=Path('docs/evidence/cp6-am-predecessor-functions.json')
CATALOG=Path('docs/evidence/cp6-am-al-catalog-pins.json')
PROVENANCE=Path('docs/evidence/cp6-am-cli-provenance.json')
BUILDER=Path('scripts/cp6_v2620am_build_sql.py')
DEFINITIONS=Path('scripts/cp6_v2620am_definitions.py')
sha,replace,block,rows=prior.sha,prior.replace,prior.block,prior.rows

DATA_ADMISSION = """
do $preexisting_transfer_v2620am$
begin
  if exists(select 1 from erp.material_transfers h where h.status<>'DRAFT' and
      (select count(*) from erp.material_stock_movements m
        where m.source_type='MATERIAL_TRANSFER' and m.source_id=h.id)
      <>2*(select count(*) from erp.material_transfer_items i where i.transfer_id=h.id))
    or exists(select 1 from erp.material_stock_movements m
      where m.source_type='MATERIAL_TRANSFER'
      group by m.source_id,m.material_id,m.roll_id
      having sum(m.qty_signed)<>0 or sum(m.qty_signed*m.unit_cost_snapshot)<>0)
    or exists(select 1 from erp.material_stock_movements rv
      join erp.material_stock_movements original on original.id=rv.reversal_of_id
      where original.source_type='MATERIAL_TRANSFER'
        and rv.unit_cost_snapshot is distinct from original.unit_cost_snapshot)
    or exists(select 1 from (
      select sum(m.qty_signed) over(partition by m.material_id,m.location_id,m.roll_id
        order by m.physical_at,m.system_created_at,m.id rows unbounded preceding) prefix
      from erp.material_stock_movements m where m.reversal_of_id is null
        and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
    ) history where prefix<0) then
    raise exception 'AM_PREEXISTING_TRANSFER_OR_LOCATION_HISTORY_REVIEW_REQUIRED';
  end if;
end
$preexisting_transfer_v2620am$;
"""


def build():
    provenance=json.loads(PROVENANCE.read_text())
    assert provenance['generated_file']==MIGRATION.name and provenance['cli_version']=='2.116.0'
    assert provenance['empty_file_sha256']==sha(b'')
    original=json.loads(INPUT.read_text())
    assert (original['head'],original['tree'])==(PREDECESSOR_HEAD,PREDECESSOR_TREE)
    src={r[0]:r for r in original['functions']};assert set(src)==set(IDENTITIES)
    catalog={f['identity']:f for f in json.loads(CATALOG.read_text())['functions']}
    assert len(catalog)==533
    for identity,row in src.items():
        assert sha(row[1])==catalog[identity]['sha256']
    p=json.loads(prior.PINS.read_text())
    for path in (prior.MIGRATION,prior.ROLLBACK):
        assert sha(path.read_bytes())==p['source_pins'][str(path)]['sha256']
    defs=definitions(src)
    functions=[dict(identity=i,predecessor_sha256=sha(src[i][1]),installed_sha256=sha(d),
        owner=src[i][3],acl=sorted(src[i][2].strip('{}').split(',')))
        for i,d in zip(IDENTITIES,defs,strict=True)]
    old={m:rows(p['functions'],m) for m in ('predecessor','installed','restore')}
    new={m:rows(functions,m) for m in old}
    def advance(source):
        for before,tag in (('v2620al','__AM_CAP__'),('v2.6.20al','__AM_VER__'),('AL_','__AM_ERR__')):
            source=source.replace(before,tag)
        source=source.replace('v2620ak','v2620al').replace('v2.6.20ak','v2.6.20al')
        return source.replace('__AM_CAP__','v2620am').replace('__AM_VER__',VERSION).replace('__AM_ERR__','AM_').replace('<>224','<>225').replace('expected224','expected225')
    migration=advance(prior.MIGRATION.read_text())
    migration='-- CP6 AM: complete neutral transfers and location/roll history.\n'+migration[migration.index('begin;\n'):]
    migration=replace(migration,"where p.oid in("+','.join("'"+i+"'::regprocedure" for i in prior.IDENTITIES)+");",
        "where p.oid in("+','.join("'"+i+"'::regprocedure" for i in IDENTITIES)+");")
    admission=f"""do $predecessor_v2620am$
declare r record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='{prior.VERSION}')
     or exists(select 1 from erp.schema_migrations where version='{VERSION}')
     or to_regclass('erp.cp6_v2620am_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620al_rollback_capsule') is null then raise exception 'AM_REQUIRES_EXACT_AL_WITHOUT_AM_RESIDUE'; end if;
  if (select count(*) from supabase_migrations.schema_migrations where name='{prior.NAME}')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations where version='{prior.STAMP}' and name='{prior.NAME}'
       and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')='{sha(prior.MIGRATION.read_bytes())}')
     or exists(select 1 from supabase_migrations.schema_migrations where version>'{prior.STAMP}')
     or (select count(*) from erp.cp6_v2620al_rollback_capsule)<>2 then raise exception 'AM_REQUIRES_EXACT_AL_PLATFORM_CAPSULE'; end if;
  for r in select * from(values
    {new['predecessor']}
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') into v_actual
    from pg_proc p where p.oid=to_regprocedure(r.identity) and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then raise exception 'AM_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity; end if;
  end loop;
end
$predecessor_v2620am$;"""
    migration=block(migration,'do $predecessor_v2620am$','$predecessor_v2620am$;',admission)
    migration=replace(migration,'create table erp.cp6_v2620am_rollback_capsule(',
        DATA_ADMISSION+'\ncreate table erp.cp6_v2620am_rollback_capsule(')
    canonical='do $canonical_transfer_v2620am$\nbegin\n'+'\n'.join('  execute $definition$'+d+'$definition$;' for d in defs)+'\nend\n$canonical_transfer_v2620am$;'
    migration=block(migration,'do $canonical_opening_v2620am$','$canonical_opening_v2620am$;',canonical)
    migration=replace(migration,old['installed'],new['installed'])
    migration=migration.replace('(select count(*) from erp.cp6_v2620am_rollback_capsule)<>2','(select count(*) from erp.cp6_v2620am_rollback_capsule)<>6')
    migration=migration.replace('Opening BS and WIP values are checked before posting; master type errors persist per row','Every transfer line posts atomically; paired historical costs are neutral and location roll prefixes remain valid')
    MIGRATION.write_text(migration)
    rollback=advance(prior.ROLLBACK.read_text()).replace('-> exact AK.','-> exact AL.')
    rollback=rollback.replace('(select count(*) from erp.cp6_v2620am_rollback_capsule)<>2','(select count(*) from erp.cp6_v2620am_rollback_capsule)<>6')
    for mode in old:
        if old[mode] in rollback:rollback=rollback.replace(old[mode],new[mode])
    rollback=rollback.replace(prior.STAMP,STAMP).replace(prior.NAME,NAME)
    rollback=rollback.replace(sha(prior.MIGRATION.read_bytes()),sha(migration)).replace(sha(prior.MIGRATION.read_text().removesuffix('\n')),sha(migration.removesuffix('\n')))
    ROLLBACK.write_text(rollback)
    pins=dict(format='CP6_AM_RUNTIME_PINS_V1',stamp=STAMP,name=NAME,version=VERSION,
        predecessor_head=PREDECESSOR_HEAD,predecessor_tree=PREDECESSOR_TREE,functions=functions,
        boundary_count=225,predecessor_function_count=533,predecessor_table_count=227,
        comparison_run=35657686329,production_go=False,
        source_pins={str(path):dict(sha256=sha(path.read_bytes()),bytes=path.stat().st_size)
            for path in (BUILDER,DEFINITIONS,PROVENANCE,INPUT,CATALOG,prior.MIGRATION,prior.ROLLBACK,MIGRATION,ROLLBACK)})
    PINS.write_text(json.dumps(pins,indent=2)+'\n')
    print(json.dumps({'migration':sha(migration),'rollback':sha(rollback),'pins':sha(PINS.read_bytes())}))
    return pins


if __name__=='__main__':
    build()
