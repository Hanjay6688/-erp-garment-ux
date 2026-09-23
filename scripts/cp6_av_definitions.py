"""AV rev2 candidate definitions, written in exact pg_get_functiondef form.

One identity family successor on top of exact AU:
- AU-R1: the successor cutoff reads one source of NEW_STOCK physical instants.
- Owner decision 1C (handoff §14): a found (OUT_OF_NOWHERE) manual BS is a new
  physical fact. It is validated as NEW_STOCK on the version active at its
  physical time and bounds a successor. LEGACY manual BS and opening BS stay
  existing stock and are not validated against the version period (their
  physical dates are historical and may precede the SKU record).
- Owner decision 2A: GOOD returned by rework is existing stock of the BS
  version. It is validated as EXISTING_STOCK and never bounds a successor.
- AV-GUARD-01: coverage is a fail-closed registry of every column that
  references a product, read from the catalog structure instead of function
  text, so SQL spelling cannot hide a new product fact table.

The manual BS origin lives in an insert-only table because
classify_bs_case_v2 clears bs_cases.untracked_type once a cause is known.
Rows created before this successor have no origin record and keep AU behaviour.
"""
from pathlib import Path
import json,re
import cp6_au_definitions as au

ROOT=Path(__file__).resolve().parents[1]
EDIT='erp.edit_product_identity_effective(uuid,text,uuid,uuid,text,uuid,text,timestamp with time zone,text)'
MANUAL='erp.create_manual_bs_case_v2(jsonb,uuid)'
REWORK='erp.post_rework_completion(uuid)'
HELPER='erp.latest_new_stock_physical_at_v1(uuid)'
COVERAGE='erp.assert_new_stock_cutoff_coverage_v1()'
ORIGIN_GUARD='erp.guard_bs_case_manual_origin_immutable_v1()'
ORIGINS='bs_case_manual_origins_v1'
PRIVATE_ACL=['postgres=X/postgres']
HELPER_TABLES=('bs_case_manual_origins_v1','bs_cases','fg_lots','rework_orders')


def canonical_from_migration(relative,name):
    """The last CREATE OR REPLACE of a function in a migration, already in pg_get_functiondef form."""
    text=(ROOT/relative).read_text()
    start=[m.start() for m in re.finditer(r'CREATE OR REPLACE FUNCTION erp\.'+name+r'\(',text)][-1]
    body=text.index('AS $function$',start)+len('AS $function$')
    return text[start:text.index('$function$',body)+len('$function$')]+'\n'


def replace_once(text,old,new):
    assert text.count(old)==1,('AV_SOURCE_ANCHOR',old[:60])
    return text.replace(old,new)


OLD={
    EDIT:au.FUNCTIONS[EDIT],
    MANUAL:canonical_from_migration('supabase/migrations/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql','create_manual_bs_case_v2'),
    REWORK:canonical_from_migration('supabase/migrations/20260916202400_erp_v2_6_20aj_cp6_rework_output_lineage.sql','post_rework_completion'),
}

FUNCTIONS={
    EDIT:replace_once(replace_once(OLD[EDIT],
        "v_used boolean; v_eff timestamptz:=coalesce(p_effective_from,clock_timestamp());\n",
        "v_used boolean; v_eff timestamptz:=coalesce(p_effective_from,clock_timestamp()); v_last timestamptz;\n"),
        """  if exists(select 1 from erp.fg_lots l where l.product_id=p.id and l.produced_at>=v_eff) then
    raise exception 'Tanggal efektif SKU akan memotong histori produksi yang sudah tercatat';
  end if;
""","""  v_last:=erp.latest_new_stock_physical_at_v1(p.id);
  if v_last>=v_eff then
    raise exception 'Tanggal efektif SKU akan memotong histori produksi yang sudah tercatat (fakta fisik stok baru terakhir %). Pilih tanggal efektif sesudahnya.',v_last;
  end if;
"""),
    MANUAL:replace_once(replace_once(OLD[MANUAL],
        "  if v_cached is not null then return v_cached; end if;\n",
        """  if v_cached is not null then return v_cached; end if;
  if v_type='OUT_OF_NOWHERE' and nullif(p_payload->>'product_id','') is not null then
    perform erp.assert_product_identity_time(nullif(p_payload->>'product_id','')::uuid,v_physical,'NEW_STOCK');
  end if;
"""),
        "  ) returning * into v_case;\n",
        """  ) returning * into v_case;
  insert into erp.bs_case_manual_origins_v1(bs_case_id,origin_type) values(v_case.id,v_type);
"""),
    REWORK:replace_once(OLD[REWORK],
        """      raise exception 'GOOD rework return requires native production PO and product lineage';
    end if;
""","""      raise exception 'GOOD rework return requires native production PO and product lineage';
    end if;
    perform erp.assert_product_identity_time(b.product_id,v_completed_at,'EXISTING_STOCK');
"""),
}

# Every column that references a product, classified once. Only NEW_STOCK_FACT
# columns carry a physical instant that bounds a successor; the helper must read
# each of them. Keys are schema.table.column; a new reference or a renamed one
# fails the guard until it is classified here.
REGISTRY={
    'erp.accessory_bom_versions.product_id':['MASTER','Effective-dated accessory BOM; no stock instant'],
    'erp.bs_cases.product_id':['NEW_STOCK_FACT','physical_at of QC/laundry BS and manual OUT_OF_NOWHERE BS'],
    'erp.contractor_accessory_reimbursement_entitlements.product_id':['DERIVED','Accounting entitlement of an FG lot'],
    'erp.fg_accessory_cost_snapshots.product_id':['DERIVED','Cost snapshot of an FG lot'],
    'erp.fg_adjustment_items.product_id':['MOVEMENT','Adjusts an existing lot'],
    'erp.fg_inventory_balances.product_id':['DERIVED','Balance cache keyed by product/location/grade'],
    'erp.fg_lots.product_id':['NEW_STOCK_FACT','produced_at of every lot except GOOD returned by rework'],
    'erp.fg_stock_movements.product_id':['MOVEMENT','Movement of an existing lot'],
    'erp.journal_lines.product_id':['ACCOUNTING','Journal dimension'],
    'erp.laundry_receipt_batch_size_lines.bs_product_id':['SOURCE_DOCUMENT','Laundry receipt input; the BS fact is bs_cases'],
    'erp.laundry_receipt_bs_product_allocations.product_id':['SOURCE_DOCUMENT','Validated as NEW_STOCK; the BS fact is bs_cases'],
    'erp.non_po_hpp_gl_sync_events_v2620f.product_id':['ACCOUNTING','HPP to GL synchronisation event'],
    'erp.opening_balance_items.product_id':['SOURCE_DOCUMENT','Opening document; facts are OPENING lots and LEGACY BS'],
    'erp.po_accessory_bom_commitments.product_id':['MASTER','PO accessory BOM commitment'],
    'erp.product_conversions.from_product_id':['SOURCE_DOCUMENT','Conversion source, validated as EXISTING_STOCK'],
    'erp.product_conversions.to_product_id':['SOURCE_DOCUMENT','Conversion target; the fact is the CONVERSION lot in fg_lots'],
    'erp.product_identity_mutation_context_v1.product_id':['AUTHORIZATION','Private one-use identity edit context'],
    'erp.product_price_versions.product_id':['MASTER','Effective-dated price'],
    'erp.qc_inspection_items.final_product_id':['SOURCE_DOCUMENT','QC input; the facts are fg_lots and bs_cases'],
    'erp.sales_items.product_id':['SALES','Sale of existing stock'],
    'erp.sales_return_items.product_id':['SALES','Return of sold stock'],
    'erp.stock_explainability_snapshots.product_id':['REPORT','Stock explanation snapshot'],
    'erp.stock_policy_versions.product_id':['MASTER','Effective-dated stock policy'],
}
assert sorted(k for k,v in REGISTRY.items() if v[0]=='NEW_STOCK_FACT')==['erp.bs_cases.product_id','erp.fg_lots.product_id']
assert all("'" not in k and "'" not in v[1] for k,v in REGISTRY.items())
REGISTRY_LITERAL=json.dumps({k:{'class':c,'reason':r} for k,(c,r) in sorted(REGISTRY.items())},separators=(',',':'))

NEW_FUNCTIONS={
    ORIGIN_GUARD:"""CREATE OR REPLACE FUNCTION erp.guard_bs_case_manual_origin_immutable_v1()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
begin
  raise exception 'BS_MANUAL_ORIGIN_IMMUTABLE: asal BS manual tidak boleh diubah atau dihapus';
end;
$function$
""",
    HELPER:"""CREATE OR REPLACE FUNCTION erp.latest_new_stock_physical_at_v1(p_product_id uuid)
 RETURNS timestamp with time zone
 LANGUAGE sql
 STABLE
 SET search_path TO ''
AS $function$
select max(f.physical_at) from (
  select l.produced_at as physical_at from erp.fg_lots l
  where l.product_id=p_product_id
    and not exists(select 1 from erp.rework_orders r where r.good_fg_lot_id=l.id)
  union all
  select b.physical_at from erp.bs_cases b
  where b.product_id=p_product_id
    and (b.qc_item_id is not null or b.source_laundry_bs_allocation_id is not null
      or exists(select 1 from erp.bs_case_manual_origins_v1 o where o.bs_case_id=b.id and o.origin_type='OUT_OF_NOWHERE'))
) f
$function$
""",
    COVERAGE:"""CREATE OR REPLACE FUNCTION erp.assert_new_stock_cutoff_coverage_v1()
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO ''
AS $function$
declare
  v_registry jsonb:='"""+REGISTRY_LITERAL+"""';
  v_helper_tables text[]:=array["""+','.join("'"+t+"'" for t in HELPER_TABLES)+"""];
  v_actual text[];
  v_unclassified text[];
  v_stale text[];
  v_facts text[];
  v_helper text[];
begin
  -- Structural catalog read: any FK to erp.products in any schema, plus any
  -- product-named uuid column in erp/public that no FK protects.
  select array_agg(distinct ref order by ref) into v_actual from (
    select format('%s.%s.%s',n.nspname,c.relname,a.attname) ref
    from pg_constraint fk join pg_class c on c.oid=fk.conrelid
    join pg_namespace n on n.oid=c.relnamespace
    join pg_attribute a on a.attrelid=c.oid and a.attnum=any(fk.conkey)
    where fk.contype='f' and fk.confrelid='erp.products'::regclass and fk.conrelid<>'erp.products'::regclass
    union
    select format('%s.%s.%s',n.nspname,c.relname,a.attname)
    from pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace
    where n.nspname in('erp','public') and c.relkind in('r','p') and c.oid<>'erp.products'::regclass
      and a.attnum>0 and not a.attisdropped and a.atttypid='uuid'::regtype
      and (a.attname='product_id' or a.attname like '%\\_product\\_id')
  ) r;
  select array_agg(k order by k) into v_unclassified from unnest(v_actual) k where not v_registry ? k;
  if v_unclassified is not null then
    raise exception 'NEW_STOCK_CUTOFF_REFERENCE_UNCLASSIFIED: %',array_to_string(v_unclassified,', ');
  end if;
  select array_agg(k order by k) into v_stale from jsonb_object_keys(v_registry) k where k<>all(v_actual);
  if v_stale is not null then
    raise exception 'NEW_STOCK_CUTOFF_REGISTRY_STALE: %',array_to_string(v_stale,', ');
  end if;
  select array_agg(distinct split_part(key,'.',2) order by split_part(key,'.',2)) into v_facts
  from jsonb_each(v_registry) where value->>'class'='NEW_STOCK_FACT';
  select array_agg(distinct m[1] order by m[1]) into v_helper
  from pg_proc p cross join lateral regexp_matches(lower(p.prosrc),'erp\\.([a-z0-9_]+)','g') m
  where p.oid='erp.latest_new_stock_physical_at_v1(uuid)'::regprocedure;
  if v_helper is null or not (v_helper @> v_helper_tables and v_helper <@ v_helper_tables and v_helper @> v_facts) then
    raise exception 'NEW_STOCK_CUTOFF_HELPER_SCOPE_DRIFT: %',v_helper;
  end if;
  if lower((select p.prosrc from pg_proc p where p.oid='erp.edit_product_identity_effective(uuid,text,uuid,uuid,text,uuid,text,timestamp with time zone,text)'::regprocedure))
     !~ 'erp\\.latest_new_stock_physical_at_v1\\s*\\(' then
    raise exception 'NEW_STOCK_CUTOFF_CONSUMER_DRIFT';
  end if;
  return jsonb_build_object('references',coalesce(array_length(v_actual,1),0),'new_stock_fact_tables',v_facts,'registry',v_registry);
end;
$function$
""",
}

SCHEMA="""create table erp.bs_case_manual_origins_v1 (
 bs_case_id uuid primary key references erp.bs_cases(id),
 origin_type text not null check (origin_type in ('LEGACY','OUT_OF_NOWHERE')),
 recorded_at timestamptz not null default statement_timestamp()
);
alter table erp.bs_case_manual_origins_v1 enable row level security;
revoke all on erp.bs_case_manual_origins_v1 from public,anon,authenticated,service_role;
"""

TRIGGERS="""create trigger trg_bs_case_manual_origin_immutable before update or delete on erp.bs_case_manual_origins_v1
 for each row execute function erp.guard_bs_case_manual_origin_immutable_v1();
create trigger trg_bs_case_manual_origin_no_truncate before truncate on erp.bs_case_manual_origins_v1
 for each statement execute function erp.guard_bs_case_manual_origin_immutable_v1();
"""
