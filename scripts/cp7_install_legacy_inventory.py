"""OW14b installation inventory: exact Native references and one official rule.

Administrative cursor only; no connection, commit, migration or owner policy.
The optional preview runs the existing material engine inside a savepoint and
rolls back its cache writes. Zero remains zero and missing references stay null.
"""
from hashlib import sha256
from pathlib import Path
import json

CONTRACT='cp7.legacy-fabric-installation-inventory.v1'
SQL="""
select jsonb_build_object(
 'material_id',m.id,'sku',m.material_sku,'name',m.material_name,
 'material_type',m.material_type,'unit_code',m.unit_code,'is_active',m.is_active,
 'row_version',m.row_version,'profile_present',fp.material_id is not null,
 'minimum_stock_qty',fp.minimum_stock_qty::text,
 'native_material',to_jsonb(m),'native_profile',to_jsonb(fp))
from erp.materials m left join erp.fabric_master_profiles fp on fp.material_id=m.id
where m.material_type='FABRIC' order by m.id
"""


def digest(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def source_hash():return sha256(Path(__file__).read_bytes()).hexdigest()


def capture(cur):
    # The installation transaction owns these SHARE locks until completion.
    # No minimum, identity, unit or master metadata may change during admission.
    cur.execute('lock table erp.materials,erp.fabric_master_profiles in share mode')
    orphan=cur.execute("select fp.material_id::text from erp.fabric_master_profiles fp "
        "left join erp.materials m on m.id=fp.material_id "
        "where m.id is null or m.material_type<>'FABRIC' order by fp.material_id").fetchall()
    if orphan:raise ValueError('OW14B_FABRIC_PROFILE_IDENTITY_MISMATCH')
    rows=[r[0]for r in cur.execute(SQL).fetchall()]
    ids=[r['material_id']for r in rows]
    if len(ids)!=len(set(ids)):raise ValueError('OW14B_DUPLICATE_MATERIAL_IDENTITY')
    if any(not isinstance(r['unit_code'],str)or not r['unit_code'].strip()for r in rows):
        raise ValueError('OW14B_MATERIAL_UNIT_REQUIRED')
    return dict(contract=CONTRACT,source_sha256=source_hash(),rows=rows,
        rows_sha256=digest(rows),count=len(rows),native_values_changed=False,
        selection_made=False,production_go=False)


def assert_preserved(cur,before):
    if before.get('contract')!=CONTRACT or before.get('source_sha256')!=source_hash() \
            or before.get('rows_sha256')!=digest(before.get('rows')):
        raise ValueError('OW14B_TRUSTED_INVENTORY_REQUIRED')
    after=capture(cur)
    if after['rows']!=before['rows']:raise ValueError('OW14B_NATIVE_REFERENCE_CHANGED_DURING_INSTALL')
    return after


def preview_active_rules(cur,before):
    """Read actual official engine results, with no persistent cache changes."""
    assert_preserved(cur,before)
    prior=cur.execute("select coalesce(jsonb_agg(to_jsonb(e)order by e.material_id),'[]') "
                      'from cp7_stock_formula.material_evaluations e').fetchone()[0]
    cur.execute('savepoint ow14b_install_rule_preview')
    try:
        cur.execute('set local role cp7_capture')
        at=cur.execute('select clock_timestamp()').fetchone()[0]
        cur.execute('select cp7_stock_formula.compute_materials(%s)',(at,))
        cur.execute('reset role')
        rules=[r[0]for r in cur.execute("select to_jsonb(e)||jsonb_build_object("
            "'legacy_minimum_qty',e.legacy_minimum_qty::text,'point',e.point::text,"
            "'manual_point',e.manual_point::text)from cp7_stock_formula.material_evaluations e "
            "where e.material_type='FABRIC' order by e.material_id").fetchall()]
        active={r['material_id']:r for r in before['rows']if r['is_active']}
        if {r['material_id']for r in rules}!=set(active):raise ValueError('OW14B_ACTIVE_INVENTORY_COVERAGE_CHANGED')
        for row in rules:
            native=active[row['material_id']]
            if (row['sku'],row['unit_code'],row['legacy_minimum_qty'])!=(native['sku'],native['unit_code'],native['minimum_stock_qty']):
                raise ValueError('OW14B_ACTIVE_IDENTITY_UNIT_REFERENCE_MISMATCH')
        result=dict(contract='cp7.legacy-fabric-official-rule-preview.v1',read_at=at.isoformat(),
            inventory_sha256=before['rows_sha256'],rows=rules,rows_sha256=digest(rules),
            engine='cp7_stock_formula.compute_materials(timestamptz)',formula_reimplemented=False,
            read_only_preview=True,native_values_changed=False,selection_made=False,production_go=False)
    finally:
        cur.execute('rollback to savepoint ow14b_install_rule_preview')
        cur.execute('release savepoint ow14b_install_rule_preview')
    assert_preserved(cur,before)
    after=cur.execute("select coalesce(jsonb_agg(to_jsonb(e)order by e.material_id),'[]') "
                      'from cp7_stock_formula.material_evaluations e').fetchone()[0]
    if after!=prior:raise ValueError('OW14B_PREVIEW_CACHE_NOT_RESTORED')
    return result
