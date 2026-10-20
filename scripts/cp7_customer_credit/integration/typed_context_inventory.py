"""Closed OW04 predecessor-context census. Read-only; emits refusal guards only.

Caller must first run the real predecessor verifiers and the exact R4-05 guard
verifier. No namespace prefix is trusted, no grant or Native guard is changed.
Capture BEFORE creating the four OW04 schemas; verify AFTER excludes exactly
those four schemas. Missing read visibility is an explicit blocker.
"""
from hashlib import sha256
from pathlib import Path
import json
import re

NEW_SCHEMAS = ('cp7_credit', 'ow04_ordinal_wrapper', 'ow04_source_proposal', 'ow04_pure_kernel')
PLAN_TABLE = 'cp7_plan_native.apply_own_drafts'
PLAN_READER = 'cp7_credit._has_ambient_plan_apply_scope()'
PLAN_READER_BODY = 'select exists(select 1 from cp7_plan_native.apply_own_drafts where txid=pg_catalog.pg_current_xact_id());'
DISPATCH = (
    'cp7_sales.command_context', 'erp.cutting_bridge_execution_context',
    'erp.bs_resolution_execution_context', 'erp.cp6_laundry_qc_execution_context',
    'cp7_procurement.execution_context', 'cp7_material.execution_context',
    'cp7_supplier_return.execution_context', 'cp7_payroll.execution_context',
    'cp7_payroll.settlement_context', 'cp7_attendance.command_context',
)
# name, source, owner, has_backend_pid, transaction_column, transaction_type_oid, RLS.
# Every name is explicit; *_v1, transaction-only and xid8 shapes are intentional.
SPECS = (
 ('erp.cutting_bridge_execution_context','supabase/migrations/20260903070931_erp_v2_6_18a_cutting_bridge_reconciliation.sql','postgres',True,'transaction_id',20,True),
 ('erp.bs_resolution_execution_context','supabase/migrations/20260903070932_erp_v2_6_19_cp5_bs_resolution_recovery.sql','postgres',True,'transaction_id',20,True),
 ('erp.cp6_laundry_qc_execution_context','supabase/migrations/20260904111157_erp_v2_6_20_cp6_laundry_qc_fg_authoritative.sql','postgres',True,'transaction_id',20,True),
 ('erp.invoice_recost_execution_context','supabase/release/cp6-t3/20260922135612_erp_v2_6_20ao_cp6_invoice_retail.sql','postgres',False,'transaction_id',20,True),
 ('erp.pocket_fabric_execution_context','supabase/release/cp6-t3/20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql','postgres',True,'transaction_id',20,True),
 ('erp.product_identity_mutation_context_v1','supabase/release/cp6-t3/20260923045944_erp_v2_6_20au_cp6_controlled_product_lifecycle.sql','postgres',True,'transaction_id',20,True),
 ('erp.bc_execution_context_v1','supabase/release/cp6-t3/20260925030000_erp_v2_6_20bc_cp6_accessory_service_returns.sql','postgres',True,'transaction_id',20,True),
 ('erp.bd_execution_context_v1','supabase/release/cp6-t3/20260925040000_erp_v2_6_20bd_cp6_laundry_prices_invoices.sql','postgres',True,'transaction_id',20,True),
 ('erp.be_execution_context_v1','supabase/release/cp6-t3/20260926050000_erp_v2_6_20be_cp6_conversion_redye_pocket.sql','postgres',True,'transaction_id',20,True),
 ('erp.bf_context_v1','supabase/release/cp6-t3/20260928134500_erp_v2_6_20bf_cp6_commercial_ranges_vendor_credit.sql','postgres',True,'transaction_id',20,True),
 ('cp7_procurement.execution_context','scripts/cp7-src/procurement/bootstrap.sql','cp7_procure_write',True,'transaction_id',20,True),
 ('cp7_material.execution_context','scripts/cp7-src/materials/bootstrap.sql','cp7_material_write',True,'transaction_id',20,True),
 ('cp7_supplier_return.execution_context','scripts/cp7-src/supplier-returns/bootstrap.sql','cp7_return_write',True,'transaction_id',20,True),
 ('cp7_payroll.execution_context','scripts/cp7-src/payroll/notes.sql','cp7_nota_write',True,'transaction_id',20,True),
 ('cp7_payroll.settlement_context','scripts/cp7-src/payroll/settlement-write.sql','cp7_payroll_write',True,'transaction_id',20,True),
 ('cp7_attendance.command_context','scripts/cp7-src/payroll/attendance-write.sql','cp7_attendance_write',True,'transaction_id',20,True),
 ('cp7_sales.command_context','scripts/cp7-src/sales/commands.sql','cp7_sales_write',True,'transaction_id',20,True),
 ('cp7_receipt_fix.context','scripts/cp7-src/procurement/correction.sql','postgres',True,'transaction_id',20,True),
 ('cp7_note.context','scripts/cp7-src/sales/correction.sql','postgres',True,'transaction_id',20,True),
 ('cp7_sales_return_correction.context','scripts/cp7-src/sales/return-correction.sql','postgres',True,'transaction_id',20,True),
 ('cp7_payment_correction.context','scripts/cp7-src/sales/payment-correction.sql','cp7_sales_write',True,'transaction_id',20,True),
 ('cp7_supplier_payment_create.context','scripts/cp7-src/invoices/payment-create.sql','cp7_invoice_write',True,'transaction_id',20,True),
 ('cp7_supplier_payment_correction.context','scripts/cp7-src/invoices/payment-correction.sql','cp7_invoice_write',True,'transaction_id',20,True),
 ('cp7_misc.command_context','scripts/cp7-src/finance/misc.sql','cp7_misc_write',True,'transaction_id',20,True),
 ('cp7_installment.command_context','scripts/cp7-src/payroll/installments.sql','cp7_installment_write',True,'transaction_id',20,True),
 ('cp7_kasbon.command_context','scripts/cp7-src/payroll/kasbon.sql','postgres',True,'transaction_id',20,True),
 ('cp7_cutting_correction.pickup_context','scripts/cp7-src/cutting-correction/pickup.sql','postgres',True,'transaction_id',20,True),
 ('cp7_guard.compound_scope','scripts/cp7-src/finance/dated-guards.sql','postgres',False,'txid',20,False),
 ('cp7_guard.compound_touch','scripts/cp7-src/finance/dated-guards.sql','postgres',False,'txid',20,False),
 ('cp7_plan_native.apply_own_drafts','scripts/cp7-src/plan-native/bootstrap.sql','cp7_plan_writer',False,'txid',5069,True),
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(value):
    return sha256(value.encode()).hexdigest()


def source_manifest(repo, verified_dispatch):
    if tuple(verified_dispatch) != DISPATCH:
        raise ValueError('OW04_VERIFIED_DISPATCH_CHANGED')
    result = []
    for name, source, owner, backend, transaction, typ, rls in SPECS:
        text = (Path(repo) / source).read_text()
        match = re.search(r'create\s+table\s+' + re.escape(name) + r'\s*\(', text, re.I)
        if match is None:
            raise ValueError('OW04_CONTEXT_SOURCE_DECLARATION_CHANGED: ' + name)
        body = text[match.end():text.find(');', match.end())]
        datatype = 'xid8' if typ == 5069 else '(?:bigint|int8)'
        if not re.search(r'\b' + transaction + r'\s+' + datatype + r'\b', body, re.I) \
                or bool(re.search(r'\bbackend_pid\b', body)) != backend:
            raise ValueError('OW04_CONTEXT_SOURCE_SHAPE_CHANGED: ' + name)
        result.append(dict(name=name, source=source, source_sha256=digest(text),
            source_line=text.count('\n', 0, match.start()) + 1, owner=owner,
            backend=backend, transaction_column=transaction, transaction_type_oid=typ, rls=rls))
    if len({x['name'] for x in result}) != len(result):
        raise ValueError('OW04_CONTEXT_DUPLICATE_SOURCE')
    return sorted(result, key=lambda x: x['name'])


# No namespace-prefix condition. ANY named transaction_id or txid column enters
# the census, including a wrong type, so type drift cannot hide a table.
# Permanent AND unlogged ordinary/partitioned/foreign relations are included.
CENSUS_SQL = r"""select jsonb_build_object(
 'name',n.nspname||'.'||c.relname,'oid',c.oid::text,'owner',pg_get_userbyid(c.relowner),
 'relkind',c.relkind::text,'persistence',c.relpersistence::text,'rls',c.relrowsecurity,'force_rls',c.relforcerowsecurity,
 'acl',c.relacl::text[],
 'columns',(select jsonb_agg(jsonb_build_object('num',a.attnum,'name',a.attname,'type',a.atttypid::integer,
   'typmod',a.atttypmod,'notnull',a.attnotnull,'acl',a.attacl::text[],'identity',a.attidentity::text,
   'generated',a.attgenerated::text,'default',pg_get_expr(d.adbin,d.adrelid))order by a.attnum)
  from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum
  where a.attrelid=c.oid and a.attnum>0 and not a.attisdropped),
 'constraints',(select coalesce(jsonb_agg(jsonb_build_object('name',k.conname,'type',k.contype::text,
   'keys',k.conkey,'foreign_table',k.confrelid::text,'foreign_keys',k.confkey,
   'deferrable',k.condeferrable,'deferred',k.condeferred,'definition',pg_get_constraintdef(k.oid,false))order by k.conname),'[]')
  from pg_constraint k where k.conrelid=c.oid),
 'policies',(select coalesce(jsonb_agg(jsonb_build_object('name',p.polname,'command',p.polcmd::text,
   'roles',p.polroles,'permissive',p.polpermissive,'using',pg_get_expr(p.polqual,p.polrelid),
   'check',pg_get_expr(p.polwithcheck,p.polrelid))order by p.polname),'[]')from pg_policy p where p.polrelid=c.oid),
 'reader_select',has_table_privilege('postgres',c.oid,'SELECT'),
 'reader_schema_usage',has_schema_privilege('postgres',n.oid,'USAGE'),
 'reader_row_security_active',row_security_active(c.oid),
 'owner_select',has_table_privilege(c.relowner,c.oid,'SELECT'),
 'owner_schema_usage',has_schema_privilege(c.relowner,n.oid,'USAGE'),
 'owner_role',(select jsonb_build_object('login',r.rolcanlogin,'inherit',r.rolinherit,'superuser',r.rolsuper,
  'createdb',r.rolcreatedb,'createrole',r.rolcreaterole,'replication',r.rolreplication,'bypassrls',r.rolbypassrls)
  from pg_roles r where r.oid=c.relowner),
 'outsider_rights',(select jsonb_object_agg(r,has_table_privilege(r,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))
  from unnest(array['anon','authenticated','service_role','cp7_capture'])r)
)from pg_class c join pg_namespace n on n.oid=c.relnamespace
where c.relkind in('r','p','f')and c.relpersistence in('p','u')
 and not n.nspname=any(%s::text[])
 and exists(select 1 from pg_attribute a where a.attrelid=c.oid and a.attnum>0 and not a.attisdropped and a.attname in('transaction_id','txid'))
order by n.nspname collate "C",c.relname collate "C"
"""


def validate_census(rows, manifest):
    shapes = {(s[0],s[2],s[3],s[4],s[5],s[6])for s in SPECS}
    supplied = {(s['name'],s['owner'],s['backend'],s['transaction_column'],s['transaction_type_oid'],s['rls'])for s in manifest}
    if supplied != shapes or len(manifest) != len(SPECS):
        raise ValueError('OW04_CONTEXT_SOURCE_MEMBERSHIP_CHANGED')
    expected = {x['name']: x for x in manifest}
    actual = {x['name']: x for x in rows}
    if len(actual) != len(rows) or set(actual) != set(expected):
        raise ValueError('OW04_CONTEXT_CENSUS_CHANGED: ' + canonical(dict(
            missing=sorted(set(expected)-set(actual)), unknown=sorted(set(actual)-set(expected)))))
    for name, row in actual.items():
        spec = expected[name]
        columns = {a['name']: a for a in row['columns']}
        t = columns.get(spec['transaction_column'])
        b = columns.get('backend_pid')
        if t is None or t['type'] != spec['transaction_type_oid'] or t['notnull'] is not True \
                or (b is not None) != spec['backend'] \
                or (b is not None and (b['type'] != 23 or b['notnull'] is not True)):
            raise ValueError('OW04_CONTEXT_CATALOG_SHAPE_CHANGED: ' + name)
        if row['owner'] != spec['owner'] or row['rls'] is not spec['rls'] \
                or row['relkind'] != 'r' or row['persistence'] != 'p':
            raise ValueError('OW04_CONTEXT_CATALOG_METADATA_CHANGED: ' + name)
        if name == PLAN_TABLE:
            if not row['owner_select'] or not row['owner_schema_usage'] or row['owner_role'] != dict(
                    login=False,inherit=False,superuser=False,createdb=False,createrole=False,replication=False,bypassrls=True):
                raise ValueError('OW04_PLAN_CONTEXT_OWNER_VISIBILITY_CHANGED')
        elif not row['reader_select'] or not row['reader_schema_usage'] or row['reader_row_security_active']:
            raise ValueError('OW04_CONTEXT_READER_CANNOT_SEE_ALL_ROWS: ' + name)
        # apply_own_drafts deliberately grants cp7_capture two SELECT columns;
        # table privilege is still absent. Exact column ACLs are retained above.
        if any(row['outsider_rights'].values()):
            raise ValueError('OW04_CONTEXT_OUTSIDER_PRIVILEGE: ' + name)
    return rows


def capture(cur, repo, verified_dispatch):
    if cur.execute('select current_user').fetchone() != ('postgres',):
        raise ValueError('OW04_CONTEXT_READER_IDENTITY_CHANGED')
    manifest = source_manifest(repo, verified_dispatch)
    rows = [x[0] for x in cur.execute(CENSUS_SQL, ([],)).fetchall()]
    validate_census(rows, manifest)
    return dict(contract_version='ow04.typed-context-census.v1', manifest=manifest,
        verified_dispatch=list(verified_dispatch), catalog=rows, catalog_sha256=digest(canonical(rows)),
        manifest_sha256=digest(canonical(manifest)), source_authority='VERIFIED_PREDECESSOR_REQUIRED_BY_CALLER')


def verify(cur, repo, receipt):
    manifest = source_manifest(repo, receipt['verified_dispatch'])
    if manifest != receipt['manifest'] or digest(canonical(manifest)) != receipt['manifest_sha256']:
        raise ValueError('OW04_CONTEXT_SOURCE_MANIFEST_CHANGED')
    if cur.execute('select current_user').fetchone() != ('postgres',):
        raise ValueError('OW04_CONTEXT_READER_IDENTITY_CHANGED')
    rows = [x[0] for x in cur.execute(CENSUS_SQL, (list(NEW_SCHEMAS),)).fetchall()]
    validate_census(rows, manifest)
    if rows != receipt['catalog'] or digest(canonical(rows)) != receipt['catalog_sha256']:
        raise ValueError('OW04_CONTEXT_BASELINE_METADATA_CHANGED')
    reader = verify_plan_reader(cur)
    return dict(contract_version='ow04.typed-context-census-verified.v1', contexts=len(rows),
        catalog_sha256=receipt['catalog_sha256'], exact_new_schema_exclusions=list(NEW_SCHEMAS),plan_reader=reader)


def plan_reader_sql():
    """Run only after cp7_credit exists; adds no existing table/schema grant."""
    return ("create function cp7_credit._has_ambient_plan_apply_scope()returns boolean "
        "language sql stable security definer set search_path=''set TimeZone='UTC'as $plan_scope$"+
        PLAN_READER_BODY+"$plan_scope$;\n"
        "grant create on schema cp7_credit to cp7_plan_writer;\n"
        "alter function "+PLAN_READER+" owner to cp7_plan_writer;\n"
        "revoke all on schema cp7_credit from cp7_plan_writer;\n"
        "revoke all on function "+PLAN_READER+" from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;\n"
        "grant execute on function "+PLAN_READER+" to postgres;\n")


def verify_plan_reader(cur):
    row = cur.execute("select pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig,"
        "p.prorettype='boolean'::regtype,p.pronargs,p.prosrc from pg_proc p where p.oid=%s::regprocedure",(PLAN_READER,)).fetchone()
    if row != ('cp7_plan_writer',True,'s',['search_path=\"\"','TimeZone=UTC'],True,0,PLAN_READER_BODY):
        raise ValueError('OW04_PLAN_CONTEXT_READER_CHANGED')
    acl = cur.execute("select case when x.grantee=0 then 'PUBLIC'else pg_get_userbyid(x.grantee)end,"
        "x.privilege_type,x.is_grantable from pg_proc p cross join lateral "
        "aclexplode(coalesce(p.proacl,acldefault('f',p.proowner)))x where p.oid=%s::regprocedure order by 1,2,3",(PLAN_READER,)).fetchall()
    if set(acl) != {('cp7_plan_writer','EXECUTE',False),('postgres','EXECUTE',False)}:
        raise ValueError('OW04_PLAN_CONTEXT_READER_ACL_CHANGED')
    if cur.execute("select has_schema_privilege('cp7_plan_writer','cp7_credit','USAGE,CREATE')").fetchone() != (False,):
        raise ValueError('OW04_PLAN_CONTEXT_READER_SCHEMA_LEAK')
    return dict(signature=PLAN_READER,owner='cp7_plan_writer',predicate_sha256=digest(PLAN_READER_BODY),private_acl_exact=True)


def _predicate(spec):
    name = spec['name']
    if re.fullmatch(r'[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*', name) is None:
        raise ValueError('OW04_CONTEXT_IDENTIFIER_NOT_TRUSTED')
    transaction = spec['transaction_column']
    if transaction not in ('transaction_id','txid'):
        raise ValueError('OW04_CONTEXT_TRANSACTION_COLUMN_UNTRUSTED')
    clock = 'pg_catalog.pg_current_xact_id()' if spec['transaction_type_oid'] == 5069 else 'pg_catalog.txid_current()'
    return ('c.backend_pid=pg_catalog.pg_backend_pid() and ' if spec['backend'] else '') + 'c.' + transaction + '=' + clock


def render_guards(receipt):
    manifest = receipt['manifest']
    if digest(canonical(manifest)) != receipt['manifest_sha256'] \
            or digest(canonical(receipt['catalog'])) != receipt['catalog_sha256']:
        raise ValueError('OW04_CONTEXT_RECEIPT_CHANGED')
    validate_census(receipt['catalog'], manifest)
    expected = sorted(x[0] for x in SPECS)
    if sorted(x['name'] for x in manifest) != expected:
        raise ValueError('OW04_CONTEXT_SOURCE_MEMBERSHIP_CHANGED')
    own = "row(c.actor,c.action,c.sale_id)is not distinct from row(auth.uid(),'RETURN'::text,p_sale)"
    no_ambient = []
    own_only = []
    for spec in manifest:
        table = '.'.join('"' + p + '"' for p in spec['name'].split('.'))
        query = ('select 1 where '+PLAN_READER if spec['name']==PLAN_TABLE else
            'select 1 from ' + table + ' c where ' + _predicate(spec))
        no_ambient.append(query)
        own_only.append(query + (' and not(' + own + ')' if spec['name']=='cp7_sales.command_context' else ''))
    body1 = 'if exists(' + ' union all '.join(no_ambient) + ")then raise exception using errcode='42501',message='CP7_CREDIT_AMBIENT_CONTEXT_REFUSED';end if;"
    body2 = "if p_sale is null or(select count(*)from cp7_sales.command_context c where c.backend_pid=pg_catalog.pg_backend_pid()and c.transaction_id=pg_catalog.txid_current()and " + own + ")<>1 or exists(" + ' union all '.join(own_only) + ")then raise exception using errcode='42501',message='CP7_CREDIT_ONLY_OWN_RETURN_CONTEXT_REQUIRED';end if;"
    def function(name, args, body):
        sig = 'cp7_credit.' + name + ('(uuid)' if args else '()')
        return "create function cp7_credit." + name + '(' + args + ")returns void language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $context_guard$begin " + body + 'end $context_guard$;\n' + 'alter function ' + sig + ' owner to postgres;\nrevoke all on function ' + sig + ' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;\n'
    return dict(no_ambient=function('assert_no_ambient_native_context','',body1),
        only_own_return=function('assert_only_own_return_native_context','p_sale uuid',body2))
