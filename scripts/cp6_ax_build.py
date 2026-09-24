#!/usr/bin/env python3
"""Build the AX T1 family install: finished goods entering without a production source (owner §15.1-FG, §19.2).

Label T1_FAMILY (owner decision A+B): a development install for targeted family tests on the disposable chain
AN -> AU -> AV -> AW. Not a release package: no capsule, no rollback file, no closed admission. Evidence produced with
it must never be cited as release evidence.

The new table has no product column on purpose: the AV coverage registry classifies every product reference, and the
product of a receipt is the product of its lot.
Repair wage (owner, 24 Sep 2026: "Utang, dibayar via payroll"): a found BS repaired to GOOD may carry a repair wage per
pcs. The lot value is the base value plus the wage (Rp52.000 + Rp2.000 = Rp54.000/pcs); the wage is a debt to the
contractor (Cr CONTRACTOR_PAYABLE) at the receipt and reaches the contractor's payroll like ordinary piece work
(payroll_work_items source FG_REPAIR), paid by the ordinary payroll payment. This needs four base payroll objects to know
the new source; each is taken from its current text (the catalog bootstrap or the AC migration) and changed only by the
exact substitution below, checked here: the eligible-lines view gets one UNION ALL branch with the same column types as
the REWORK branch, the source_type CHECK accepts FG_REPAIR, the work-item source validator and the merge RPC get one
branch each.

Usage: python3 scripts/cp6_ax_build.py            # writes supabase/dev/cp6_ax_t1_family.sql
       python3 scripts/cp6_ax_build.py --check
"""
from pathlib import Path
import gzip,hashlib,re,sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'supabase/dev/cp6_ax_t1_family.sql'
SOURCE=ROOT/'scripts/cp6_ax_functions.sql'
VERSION='v2.6.20ax'
TABLE='fg_unsourced_receipts_v1'
WAGES='fg_unsourced_repair_wages_v1'
BOOTSTRAP=ROOT/'supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz'
AC=next((ROOT/'supabase/migrations').glob('*_erp_v2_6_20ac_*.sql'))
PRIVATE=['erp.guard_fg_unsourced_receipt_immutable_v1()','erp.guard_bs_resolution_fg_unsourced_v1()',
         'erp.guard_fg_unsourced_repair_wage_immutable_v1()',
         'erp.fg_unsourced_valuation_v1(uuid,timestamp with time zone)',
         'erp.post_fg_unsourced_receipt_v1(jsonb,uuid)','erp.reverse_fg_unsourced_receipt_v1(uuid,text,uuid)']
PUBLIC=['public.erp_preview_fg_unsourced_value_v1(uuid,timestamp with time zone)','public.erp_post_fg_unsourced_receipt_v1(jsonb,uuid)',
        'public.erp_reverse_fg_unsourced_receipt_v1(uuid,text,uuid)']

SCHEMA=f"""create table erp.{TABLE} (
  id uuid primary key default gen_random_uuid(),
  source_kind text not null check (source_kind in('FOUND_AT_OPNAME','GOOD_FROM_UNSOURCED_BS','REDYE_MIXED')),
  lot_id uuid not null unique references erp.fg_lots(id),
  bs_case_id uuid references erp.bs_cases(id),
  bs_resolution_id uuid,
  location_id uuid not null references erp.locations(id),
  quality_grade text not null,
  qty_pcs integer not null check (qty_pcs>0),
  physical_at timestamptz not null,
  unit_value numeric(18,2) not null check (unit_value>=0 and unit_value<>'NaN'::numeric),
  total_value numeric(20,2) not null check (total_value>=0 and total_value<>'NaN'::numeric),
  valuation jsonb not null check (valuation ? 'tier'),
  reason text not null check (length(btrim(reason))>0),
  status text not null default 'POSTED' check (status in('POSTED','REVERSED')),
  journal_entry_id uuid references erp.journal_entries(id),
  movement_id uuid not null,
  created_by uuid,
  created_at timestamptz not null default statement_timestamp(),
  reversed_by uuid,
  reversed_at timestamptz,
  reversal_reason text,
  check ((source_kind='GOOD_FROM_UNSOURCED_BS')=(bs_case_id is not null)),
  check ((status='REVERSED')=(reversed_at is not null))
);
alter table erp.{TABLE} enable row level security;
revoke all on erp.{TABLE} from public,anon,authenticated,service_role;
create index idx_{TABLE}_bs_case on erp.{TABLE}(bs_case_id) where bs_case_id is not null;
create table erp.{WAGES} (
  id uuid primary key default gen_random_uuid(),
  receipt_id uuid not null unique references erp.{TABLE}(id),
  contractor_id uuid not null references erp.contractors(id),
  work_component_id uuid not null references erp.work_components(id),
  qty_pcs integer not null check (qty_pcs>0),
  rate_per_pcs numeric(18,2) not null check (rate_per_pcs>0 and rate_per_pcs<>'NaN'::numeric),
  amount numeric(20,2) not null check (amount>0 and amount<>'NaN'::numeric),
  physical_at timestamptz not null,
  rate_reason text not null check (length(btrim(rate_reason))>0),
  status text not null default 'POSTED' check (status in('POSTED','REVERSED')),
  created_at timestamptz not null default statement_timestamp(),
  reversed_at timestamptz,
  check (amount=round(qty_pcs::numeric*rate_per_pcs,2)),
  check ((status='REVERSED')=(reversed_at is not null))
);
alter table erp.{WAGES} enable row level security;
revoke all on erp.{WAGES} from public,anon,authenticated,service_role;
create index idx_{WAGES}_contractor on erp.{WAGES}(contractor_id) where status='POSTED';
"""

TRIGGERS=f"""create trigger trg_guard_{TABLE}_immutable before update or delete on erp.{TABLE}
  for each row execute function erp.guard_fg_unsourced_receipt_immutable_v1();
create trigger trg_guard_{TABLE}_truncate before truncate on erp.{TABLE}
  for each statement execute function erp.guard_fg_unsourced_receipt_immutable_v1();
create trigger trg_guard_bs_resolution_fg_unsourced_v1 before update or delete on erp.bs_resolutions
  for each row execute function erp.guard_bs_resolution_fg_unsourced_v1();
create trigger trg_guard_{WAGES}_immutable before update or delete on erp.{WAGES}
  for each row execute function erp.guard_fg_unsourced_repair_wage_immutable_v1();
create trigger trg_guard_{WAGES}_truncate before truncate on erp.{WAGES}
  for each statement execute function erp.guard_fg_unsourced_repair_wage_immutable_v1();
"""

# ---------------------------------------------------------------- base payroll objects that learn the FG_REPAIR source
VIEW_HEAD='create or replace view "erp"."v_payroll_eligible_work_lines" with (security_invoker=true) as\n'
REPAIR_BRANCH=f"""
UNION ALL
 SELECT 'FG_REPAIR'::text AS source_type,
    w.id AS source_id,
    w.contractor_id,
    NULL::uuid AS po_id,
    NULL::uuid AS cutting_group_id,
    r.bs_case_id,
    w.work_component_id,
    w.physical_at AS eligible_at,
    w.qty_pcs AS source_qty,
    w.qty_pcs AS eligible_qty,
    COALESCE(a.allocated_qty, 0) AS allocated_qty,
    GREATEST(w.qty_pcs - COALESCE(a.allocated_qty, 0), 0) AS remaining_qty,
    0 AS held_qty,
    w.rate_per_pcs AS rate_snapshot,
    round(GREATEST(w.qty_pcs - COALESCE(a.allocated_qty, 0), 0)::numeric * w.rate_per_pcs, 2) AS remaining_amount,
    'FG_UNSOURCED_REPAIR_POSTED'::text AS eligibility_reason
   FROM erp.{WAGES} w
     JOIN erp.{TABLE} r ON r.id = w.receipt_id
     LEFT JOIN LATERAL ( SELECT sum(pwi.qty_payable)::integer AS allocated_qty
           FROM erp.payroll_work_items pwi
             JOIN erp.payroll_settlements ps ON ps.id = pwi.payroll_id
          WHERE pwi.source_type::text = 'FG_REPAIR'::text AND pwi.source_id = w.id AND ps.status::text <> 'REVERSED'::text) a ON true
  WHERE w.status = 'POSTED'::text AND r.status = 'POSTED'::text AND GREATEST(w.qty_pcs - COALESCE(a.allocated_qty, 0), 0) > 0"""
CHECK_OLD="alter table only \"erp\".\"payroll_work_items\" add constraint \"payroll_work_items_source_type_check\" CHECK (source_type::text = ANY (ARRAY['PRODUCTION'::character varying::text, 'REWORK'::character varying::text]));"
CHECK_NEW=("alter table erp.payroll_work_items drop constraint payroll_work_items_source_type_check;\n"
           "alter table erp.payroll_work_items add constraint payroll_work_items_source_type_check CHECK (source_type::text = ANY (ARRAY['PRODUCTION'::text, 'REWORK'::text, 'FG_REPAIR'::text]));")
VALIDATE_OLD="""  else
    raise exception 'Payroll source_type must be PRODUCTION or REWORK';
  end if;"""
VALIDATE_NEW=f"""  elsif new.source_type='FG_REPAIR' then
    -- AX repair wage of a found BS repaired to GOOD (owner 24 Sep 2026): a contractor debt paid through payroll. The row
    -- is locked FOR SHARE so an AX reversal (FOR UPDATE) and a payroll line on the same wage serialize.
    select w.qty_pcs,w.work_component_id,null::uuid,w.contractor_id
    into v_source_qty,v_source_component,v_source_po,v_source_contractor
    from erp.{WAGES} w
    where w.id=new.source_id and w.status='POSTED'
    for share;
  else
    raise exception 'Payroll source_type must be PRODUCTION, REWORK or FG_REPAIR';
  end if;"""
MERGE_OLD="""    elsif upper(v_line->>'source_type')='REWORK' then
      perform 1 from erp.rework_component_lines
      where id=(v_line->>'source_id')::uuid for update;
    else"""
MERGE_NEW=f"""    elsif upper(v_line->>'source_type')='REWORK' then
      perform 1 from erp.rework_component_lines
      where id=(v_line->>'source_id')::uuid for update;
    elsif upper(v_line->>'source_type')='FG_REPAIR' then
      perform 1 from erp.{WAGES}
      where id=(v_line->>'source_id')::uuid for update;
    else"""


def base_payroll():
    """The four base objects, each from its current source text with exactly one checked substitution."""
    boot=gzip.decompress(BOOTSTRAP.read_bytes()).decode()
    start=boot.index(VIEW_HEAD);end=boot.index(';;\n',start)
    view=boot[start:end]
    assert view.count('UNION ALL')==1 and "'REWORK'::text AS source_type" in view
    assert boot.count(CHECK_OLD)==1
    vstart=boot.index('CREATE OR REPLACE FUNCTION erp.validate_payroll_work_item_source()');vend=boot.index('$function$;',vstart)+len('$function$;')
    validate=boot[vstart:vend]
    assert validate.count(VALIDATE_OLD)==1
    ac=AC.read_text()
    mstart=ac.index('CREATE OR REPLACE FUNCTION erp.merge_eligible_work_into_payroll_v2(');mend=ac.index('$function$;',mstart)+len('$function$;')
    merge=ac[mstart:mend]
    assert merge.count(MERGE_OLD)==1 and ac.count('CREATE OR REPLACE FUNCTION erp.merge_eligible_work_into_payroll_v2(')==1
    return [CHECK_NEW,view+REPAIR_BRANCH+';',validate.replace(VALIDATE_OLD,VALIDATE_NEW),merge.replace(MERGE_OLD,MERGE_NEW)]



def functions():
    text=SOURCE.read_text()
    parts=re.split(r'(?=^CREATE OR REPLACE FUNCTION )',text,flags=re.M)
    out=[p.rstrip()+'\n' for p in parts if p.startswith('CREATE OR REPLACE FUNCTION ')]
    assert len(out)==len(PRIVATE)+len(PUBLIC),len(out)
    return out


def build():
    parts=['-- CP6 AX finished goods without a production source: T1_FAMILY development install (NOT a release package).',
           '-- Generated by scripts/cp6_ax_build.py from scripts/cp6_ax_functions.sql; do not edit by hand.',
           'begin;',"set local lock_timeout='10s';set local statement_timeout='240s';set local search_path='';",
           'do $t1_guard$','begin',
           " if (select count(*) from erp.schema_migrations where version in('v2.6.20av','v2.6.20aw'))<>2 then raise exception 'AX_T1_REQUIRES_AV_AND_AW'; end if;",
           f" if exists(select 1 from erp.schema_migrations where version='{VERSION}') or to_regclass('erp.{TABLE}') is not null then raise exception 'AX_T1_ALREADY_INSTALLED'; end if;",
           'end $t1_guard$;',SCHEMA.strip()]
    parts+=[f.rstrip()+';' for f in functions()]
    parts+=base_payroll()
    parts.append(TRIGGERS.strip())
    for key in PRIVATE:parts.append(f'revoke all on function {key} from public,anon,authenticated,service_role;')
    for key in PUBLIC:parts+=[f'revoke all on function {key} from public,anon;',f'grant execute on function {key} to authenticated,service_role;']
    parts+=["do $coverage$ begin perform erp.assert_new_stock_cutoff_coverage_v1(); end $coverage$;",
            f"insert into erp.schema_migrations(version,description) values('{VERSION}',"
            "'T1_FAMILY development install of AX (finished goods without a production source); not a release package');",'commit;','']
    return '\n'.join(parts)


if __name__=='__main__':
    text=build()
    if '--check' in sys.argv:
        assert OUT.read_text()==text,'supabase/dev/cp6_ax_t1_family.sql is stale; rerun scripts/cp6_ax_build.py'
        print('fresh',hashlib.sha256(text.encode()).hexdigest())
    else:
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(text)
        print(OUT.relative_to(ROOT),len(text),hashlib.sha256(text.encode()).hexdigest())
