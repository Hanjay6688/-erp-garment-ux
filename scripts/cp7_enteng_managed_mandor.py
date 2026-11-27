"""Apply the reviewed Mandor package through the managed project role."""

from hashlib import sha256
import json
from pathlib import Path
import re

import cp7_ow04_restore_bundle as catalog
from cp7_customer_credit.integration.source_triggers import trigger_guard
from cp7_enteng_managed_credit_corrections import temporary_roles
from cp7_enteng_managed_credit_release import IMMUTABLE_CENSUS
from cp7_enteng_managed_identity import IDENTITY_CALL
from cp7_enteng_managed_ow04_migration import PORTABLE_PROJECTION, digest_snapshot, seal_with_local_oid
from cp7_mandor_shop import composition as mandor


MIGRATION_NAME = 'enteng_uji_cp7_managed_mandor_shop'
SOURCE_ROOT = mandor.ROOT / 'scripts/current-mandor-shop-native-qualification/AFUI15_PARENT_ROOT_ACTUAL_INTAKE.json'
ARCHIVE_RECEIPT_SHA = 'fd7093bf782978535ebcad9ad37a9f3a496cbdcffa62d80f6b54b1f64e581a54'
CATALOG_SOURCE_SHA = '10d554f168b65e75a973572f1c0e27a1e02bd52a474e67444dc7fbe443e15563'
REFERENCES = ('NATIVE_PAYMENT_OWNER_REFERENCE.json','NATIVE_SALES_COMMAND_REFERENCE.json',
              'COMMAND_GUARD_NATIVE_REFERENCE.json')
MANAGED_IDENTITY = frozenset({
    'cp7_installment.access_now(text)',
    'cp7_installment.command(text,jsonb,uuid,text)',
    'cp7_payroll.access_now(text)',
    'cp7_payroll.settlement_command(text,jsonb,uuid,text)',
    'cp7_sales.access_now()',
    'cp7_sales.command(text,jsonb,uuid,text)',
})
NATIVE_SCOPE_ROLES = frozenset({'cp7_payroll_read','cp7_payroll_write','cp7_installment_read',
                                'cp7_installment_write','cp7_sales_read','cp7_sales_write'})
DECLARED_CENSUS_FKS = {
    ('cp7_mandor_shop.draft_buyers','sale_id'): 'erp.sales_headers',
    ('cp7_mandor_shop.sales','sale_id'): 'erp.sales_headers',
    ('cp7_mandor_shop.settlements','journal_id'): 'erp.journal_entries',
    ('cp7_mandor_shop.settlement_reversals','reversal_journal_id'): 'erp.journal_entries',
}
MANDOR_CONSTRAINT_PROJECTION = PORTABLE_PROJECTION.replace(
    "        else r - array['trigger_oid','function_oid'] end as portable",
    """        when r->>'name'='mandor_shop_journal_exact_at_commit' and r->>'relation'='erp.journal_entries'
          then (r - array['trigger_oid','function_oid','constraint']) ||
            jsonb_build_object('constraint',(r->'constraint') - 'oid')
        else r - array['trigger_oid','function_oid'] end as portable""")


def expected_source(archive_receipt):
    mandor.require(sha256(archive_receipt).hexdigest()==ARCHIVE_RECEIPT_SHA,
                   'Managed Mandor requires the verified source archive receipt')
    parent = mandor.admission.runtime_admission(SOURCE_ROOT.read_bytes())
    archive = json.loads(archive_receipt)
    mandor.require(all(archive[key]==parent[key] for key in ('head','run_id','job_id')),
                   'Mandor source archive and reviewed source differ')
    return dict(head=parent['head'],archive_sha256=archive['archive']['sha256'],
                checksum_receipt_sha256=ARCHIVE_RECEIPT_SHA)


def managed_definition(text):
    return IDENTITY_CALL.sub(lambda match: 'cp7_request_context.'+match[1].lower()+'()', text)


def canonical_functions(functions):
    reference = {}
    for filename in REFERENCES:
        for signature,row in json.loads((mandor.HERE/filename).read_bytes())['functions'].items():
            mandor.require(signature not in reference or reference[signature]==row,
                           'Mandor reviewed references disagree: '+signature)
            reference[signature] = row
    mandor.require(len(reference)==27 and MANAGED_IDENTITY<=reference.keys(),
                   'Mandor native reference set changed')
    for signature,row in reference.items():
        expected = [managed_definition(row[0]),*row[1:]] if signature in MANAGED_IDENTITY else row
        mandor.require(functions.get(signature)==expected,'Managed Mandor predecessor differs: '+signature)
    return reference


def verify_authority(cur,after,identity,plan):
    mandor.require(mandor.native_identity(cur,identity)==identity,'Mandor changed native OIDs or raw ACLs')
    for signature in plan['private_functions']:
        row = after['functions'][signature]
        grantees = {'postgres', *plan['private_execute_grants'].get(signature,[])}
        mandor.require(row[1]=='postgres' and {tuple(x) for x in row[18]}==
                       {(role,'postgres','EXECUTE',False) for role in grantees},'Mandor private EXECUTE differs: '+signature)
    for signature in plan['public_functions']:
        row = after['functions'][signature]
        mandor.require(row[1]==mandor.ROLE and row[4] and {tuple(x) for x in row[18]}==
                       {(role,mandor.ROLE,'EXECUTE',False) for role in (mandor.ROLE,'authenticated')},
                       'Mandor public EXECUTE differs: '+signature)
    for table in plan['tables']:
        row = after['relations'][table]
        mandor.require(row[0]=='postgres' and row[3] and all(item[:2]==['postgres','postgres'] for item in row[12]),
                       'Mandor private table authority differs: '+table)
    mandor.require(not any(after['roles'][mandor.ROLE][:7]) and
                   all(not any(row[1:]) for key,row in after['memberships'].items() if key.startswith(mandor.ROLE+':')),
                   'Mandor API role has undeclared authority')


def census_changes(before,after,plan):
    """Keep every raw existing row and admit only the released trigger and FK additions."""
    additions = {}
    for group,key in (('relations','relation'),('foreign_keys','oid'),('functions','identity'),('triggers','trigger_oid')):
        old = {row[key]:row for row in before[group]}
        new = {row[key]:row for row in after[group]}
        mandor.require(all(new.get(identity)==row for identity,row in old.items()),
                       'Mandor changed an existing OW04 source row in '+group)
        additions[group] = [row for row in after[group] if row[key] not in old]
    mandor.require(not additions['relations'],'Mandor changed the OW04 source relations')
    new_fks = {}
    for row in additions['foreign_keys']:
        value = row['semantic']
        relation, columns, parent = value['relation'],value['columns'],value['parent']
        mandor.require(len(columns)==1 and DECLARED_CENSUS_FKS.get((relation,columns[0]))==parent,
                       'Mandor added an undeclared OW04 source foreign key')
        mandor.require(value==dict(relation=relation,columns=columns,parent=parent,parent_columns=['id'],
                                   update_action='a',delete_action='a',match_type='s',deferrable=False,
                                   initially_deferred=False,validated=True), 'Mandor source FK semantics changed')
        new_fks[row['oid']] = value
    mandor.require(len(new_fks)==len(DECLARED_CENSUS_FKS),'Mandor source foreign key set incomplete')
    scoped = {row['relation'] for row in before['relations']}
    plan_triggers = {(item['relation'],item['name']):item for item in plan['triggers'] if item['relation'] in scoped}
    actual_triggers = {}
    ri = set()
    for row in additions['triggers']:
        mandor.require(row['enabled']=='O' and row['relation_owner']=='postgres', 'Unexpected Mandor trigger activation')
        if row['internal']:
            key = row['constraint']['oid']
            event = {9:'del',17:'upd'}.get(row['trigger_type'])
            fk = new_fks.get(key)
            mandor.require(fk and event and row['relation']==fk['parent'] and row['referenced_relation']==fk['relation']
                           and row['function']==f'pg_catalog.RI_FKey_noaction_{event}()'
                           and row['constraint']['semantic']==fk and not row['deferrable']
                           and not row['initially_deferred'] and row['argument_count']==0 and not row['columns']
                           and row['condition'] is None and row['parent_trigger'] is None,
                           'Mandor added an undeclared OW04 foreign-key attachment')
            ri.add((key,event))
        else:
            key = (row['relation'],row['name'])
            item = plan_triggers.get(key)
            mandor.require(item and row['deferrable']==item['deferrable']
                           and row['initially_deferred']==item['initially_deferred']
                           and bool(row['constraint'])==item['constraint']
                           and row['function'] in plan['private_functions'],
                           'Mandor added an undeclared OW04 source trigger: '+str(key))
            actual_triggers[key] = row
    mandor.require(set(actual_triggers)==set(plan_triggers) and ri=={(key,event) for key in new_fks for event in ('del','upd')}
                   and len(additions['triggers'])==len(plan_triggers)+len(ri),'Mandor source attachments incomplete')
    mandor.require(all(row['identity'] in {t['function'] for t in actual_triggers.values()}
                       and row['owner']=='postgres' and row['language']=='plpgsql' and row['result']=='trigger'
                       for row in additions['functions']), 'Mandor added an undeclared OW04 trigger function')
    return dict(ordinary_triggers=len(actual_triggers),foreign_keys=len(new_fks),internal_triggers=len(ri))


def reseal(cur,before,statement,plan):
    after = trigger_guard.capture(cur)
    changes = census_changes(before,after,plan)
    raw, _ = digest_snapshot(cur,before)
    updated_raw, portable = digest_snapshot(cur,after,MANDOR_CONSTRAINT_PROJECTION)
    mandor.require(re.findall(r"if actual_sha256 is distinct from '([0-9a-f]{64})'then",statement)==[raw],
                   'Mandor predecessor OW04 trigger guard is not sealed to the existing source')
    mandor.require(statement.count('$function$')==2,'Unexpected OW04 census definition delimiter')
    statement = statement.replace(raw,updated_raw,1).replace('$function$','$ow04_source_trigger_runtime$').strip()
    cur.execute(seal_with_local_oid(statement,updated_raw,portable,trigger_guard.CAPTURE_SQL,MANDOR_CONSTRAINT_PROJECTION),
                prepare=False)
    cur.execute('select cp7_credit.assert_source_native_trigger_census_v1()')
    return changes


def apply(cur,archive_receipt):
    mandor.sources()
    archived_source = expected_source(archive_receipt)
    # Check the PostgreSQL 17.12 catalogue reader. The only query change from
    # the reviewed Mandor reader omits the engine-generated pg_attver counter.
    mandor.require(sha256(Path(catalog.__file__).read_bytes()).hexdigest()==CATALOG_SOURCE_SHA and len(catalog.QUERIES)==22,
                   'Managed Mandor catalogue reader changed')
    plan = json.loads((mandor.HERE/'INSTALL_PLAN.json').read_bytes())
    mandor.require(cur.execute("select current_user,session_user,current_setting('is_superuser')").fetchone()
                   ==('postgres','postgres','off'),'Mandor requires the managed project role')
    with mandor.metadata_context(cur):
        cur.execute('select cp7_credit.assert_source_native_trigger_census_v1()')
        census = trigger_guard.capture(cur)
        original_seal = cur.execute('select pg_get_functiondef(%s::regprocedure)',(IMMUTABLE_CENSUS,)).fetchone()[0]
        cur.execute('lock table erp.journal_lines,erp.payroll_deductions,erp.payroll_settlements,erp.contractors,erp.customers,erp.chart_accounts in share row exclusive mode')
        before = catalog._catalog_rows(cur)
        mandor.require(mandor.SCHEMA not in before['schemas'] and mandor.ROLE not in before['roles'],
                       'Mandor managed installation refuses an existing module')
        original = canonical_functions(before['functions'])
        payment,_ = mandor.native_payment_routes.derive(original)
        sales,_ = mandor.native_sales_routes.derive(original)
        guards,_ = mandor.command_guard_routes.derive(original,payment)
        definitions = payment|sales|guards
        for signature in definitions.keys() & MANAGED_IDENTITY:
            definitions[signature] = managed_definition(definitions[signature])
        facades,_ = mandor.native_dispatch.derive(original)
        replay_sql,_ = mandor.replay_routes.derive((mandor.HERE/'allocation.sql').read_bytes(),facades)
        for name,ddl in replay_sql.items():
            mandor.require(plan['source_fragments'][name]==mandor.pin(ddl.encode()),'Mandor reviewed fragment changed: '+name)
        for columns in json.loads((mandor.HERE/'NATIVE_SCHEMA_REFERENCE.json').read_bytes())['columns'].values():
            for key,row in columns.items():
                mandor.require(before['columns'].get(key)==row,'Mandor reviewed native column changed: '+key)
        identity = mandor.native_identity(cur,definitions)
        roles = {role for row in identity.values() for role in (row[2],row[4]) if role!='postgres'}
        mandor.require(roles==NATIVE_SCOPE_ROLES,'Mandor native release owner set changed: '+str(sorted(roles)))
        public_items = cur.execute("select nspacl::text[] from pg_namespace where nspname='public'").fetchone()[0]
        for name in mandor.ORDER:
            ddl = replay_sql[name] if name in replay_sql else (mandor.HERE/name).read_text()
            cur.execute(ddl,prepare=False)
        cur.execute(replay_sql['composed_facades_with_native_dispatch.sql'],prepare=False)
        mandor.normalize_private(cur,plan)
        with temporary_roles(cur,sorted(roles)):
            mandor.replace_native(cur,definitions,identity)
        mandor.public_schema_transition(cur,public_items,before['schemas']['public'][0])
        after = catalog._catalog_rows(cur)
        mandor.transition(before,after,definitions,plan)
        verify_authority(cur,after,identity,plan)
        census_proof = reseal(cur,census,original_seal,plan)
        sealed = catalog._catalog_rows(cur)
        previous,now = after['functions'][IMMUTABLE_CENSUS],sealed['functions'][IMMUTABLE_CENSUS]
        mandor.require(previous[1:]==now[1:] and previous[0]!=now[0],'Mandor modified OW04 guard authority')
        after['functions'][IMMUTABLE_CENSUS] = now
        mandor.require(after==sealed,'Mandor OW04 seal changed additional database objects')
        return dict(source=archived_source,verified_native_reference=27,all_22_groups_verified=True,
                    native_adapters=len(definitions),private_functions=len(plan['private_functions']),
                    public_rpcs=len(plan['public_functions']),source_census_delta=census_proof,
                    production_go=False,independent_acceptance=False)
