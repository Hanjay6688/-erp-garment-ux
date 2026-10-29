"""Exact private family15 fixture successor. Never edits product/original tests."""
from pathlib import Path
from hashlib import sha256
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
ORIGINAL='tests/cp7/families/sku-pair-conversion.test.ts'
ORIGINAL_SHA='c9e11478ecdd1669de2aec8df42c660807b566a29913da8278a0fe6cbfba4240'
DERIVED='scripts/current-sku-all-member-native23-qualification/client_fixture_followup/sku-pair-conversion.derived.test.ts'
PREFIX='scripts/current-sku-all-member-native23-qualification/client_fixture_followup'
NATIVE_DOWNSTREAM='Hasil conversion/rebrand masih dipakai transaksi downstream aktif. Reverse transaksi downstream terlebih dahulu.'

POST_FOOTPRINT="""      -- Explicit model of BE POST's immutable source and Native allocation/GL footprint.
      insert into erp.be_conversion_sources_v1(conversion_id,source_lot_id,origin_kind,rework_id,source_revision,created_by)
      values(p_id,source_id,'FG',null,v->>'source_revision',erp.current_app_user_id());
      insert into erp.product_conversion_allocations(conversion_id,source_lot_id,destination_lot_id,qty_pcs,original_hpp_per_pcs,conversion_cost_allocated)
      values(p_id,source_id,dest,qty,unit_cost,0);
      update erp.fg_stock_movements m set source_type='PRODUCT_CONVERSION'where m.source_id=p_id and m.movement_type in('REBRAND_IN','REBRAND_OUT');
      insert into erp.journal_entries(id,journal_number,transaction_date,economic_date,source_type,source_id,description,status,created_by)
      values(p_id,'MODEL-'||p_id::text,((v->>'physical_at')::timestamptz at time zone'Asia/Jakarta')::date,
       ((v->>'physical_at')::timestamptz at time zone'Asia/Jakarta')::date,'PRODUCT_CONVERSION',p_id,'Declared selected-lot posting model','POSTED',erp.current_app_user_id());
"""

REPLACEMENTS=(
 ("from './f04/runtime.mjs'", "from '../../../tests/cp7/families/f04/runtime.mjs'"),
 ("  // The original required-key validator rejects JSON null, unlike the former\n",
  "  await db.execute(readFileSync('"+PREFIX+"/fixture_dependencies.sql','utf8'))\n"
  "  await db.execute(readFileSync('"+PREFIX+"/native_downstream.sql','utf8')+';')\n"
  "  // The original required-key validator rejects JSON null, unlike the former\n"),
 ("      insert into erp.test_journals values(p_id,round(qty*unit_cost,2),round(qty*unit_cost,2));",
  POST_FOOTPRINT+"      insert into erp.test_journals values(p_id,round(qty*unit_cost,2),round(qty*unit_cost,2));"),
 ("      if exists(select 1 from erp.test_downstream where lot_id=h.destination_lot_id)then raise exception 'DOWNSTREAM_ACTIVE';end if;",
  "      if exists(select 1 from erp.product_conversion_allocations a where a.conversion_id=h.id\n"
  "       and erp.fg_lot_has_active_downstream(a.destination_lot_id,'REBRAND_IN','PRODUCT_CONVERSION',h.id))then\n"
  "       raise exception '"+NATIVE_DOWNSTREAM+"';end if;"),
 ("  await db.execute(`insert into erp.test_downstream values('${second}')`)",
  "  await db.execute(`insert into erp.fg_stock_movements(id,lot_id,product_id,location_id,quality_grade,movement_type,qty_signed,physical_at,source_type,source_id)\n"
  "    values('${u(180)}','${second}','${target}','${warehouse}','GRADE_A','SALE',-1,'2026-10-21','SALE','${u(181)}')`)"),
 (".rejects.toThrow('DOWNSTREAM_ACTIVE')", ".rejects.toThrow('"+NATIVE_DOWNSTREAM+"')"),
 ("  await db.execute('delete from erp.test_downstream')", "  await db.execute(`delete from erp.fg_stock_movements where id='${u(180)}'`)"),
)


def derive(raw):
    if sha256(raw).hexdigest()!=ORIGINAL_SHA:raise ValueError('SKU_CLIENT_EXACT_ORIGINAL15_REQUIRED')
    text=raw.decode()
    for before,after in REPLACEMENTS:
        if text.count(before)!=1:raise ValueError('SKU_CLIENT_ONE_EXACT_FIXTURE_ANCHOR_REQUIRED:'+before)
        text=text.replace(before,after,1)
    reverse=text
    for before,after in reversed(REPLACEMENTS):
        if reverse.count(after)!=1:raise ValueError('SKU_CLIENT_ONE_EXACT_REVERSE_ANCHOR_REQUIRED')
        reverse=reverse.replace(after,before,1)
    if reverse.encode()!=raw:raise ValueError('SKU_CLIENT_REVERSIBLE_PRIVATE_DERIVATION_REQUIRED')
    old_ids=re.findall(r"^test\('([^']+)'",raw.decode(),re.M)
    new_ids=re.findall(r"^test\('([^']+)'",text,re.M)
    if old_ids!=new_ids or len(old_ids)!=15 or len(set(old_ids))!=15:raise ValueError('SKU_CLIENT_EXACT15_IDS_REQUIRED')
    old_bodies=re.split(r"(?=^test\(')",raw.decode(),flags=re.M)[1:]
    new_bodies=re.split(r"(?=^test\(')",text,flags=re.M)[1:]
    changed=[i for i,(old,new)in enumerate(zip(old_bodies,new_bodies))if old!=new]
    if changed!=[8]:raise ValueError('SKU_CLIENT_OTHER14_TEST_BODIES_CHANGED')
    old_assertions=re.findall(r'^.*\bexpect\(.*$',raw.decode(),re.M)
    new_assertions=re.findall(r'^.*\bexpect\(.*$',text,re.M)
    expected=[line.replace(".rejects.toThrow('DOWNSTREAM_ACTIVE')",".rejects.toThrow('"+NATIVE_DOWNSTREAM+"')")for line in old_assertions]
    if new_assertions!=expected:raise ValueError('SKU_CLIENT_FINANCIAL_QTY_VALUE_CONSERVATION_ASSERTIONS_CHANGED')
    return text.encode(),dict(original_sha256=ORIGINAL_SHA,derived_sha256=sha256(text.encode()).hexdigest(),
        counted_substitutions=len(REPLACEMENTS),same15_test_IDs=old_ids,original_assertion_lines=len(old_assertions),
        unchanged_other14_test_bodies=True,
        all_original_assertions_preserved=True,only_changed_expected_error='Native downstream exact message replaces old model-only marker',
        production_SQL_changed=False,Native_executions=0)
