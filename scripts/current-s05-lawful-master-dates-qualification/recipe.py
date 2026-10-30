"""Lawful fixture-only recipe dependency; never an ERP writer replacement.

The retained fixture already creates one administrative empty legacy BOM.
Configure that UNUSED master through the exact Native editor before GOOD.
An explicit later recipe change uses the original complete BF command at the
actual current statement time. No physical/calendar date is moved.
"""
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import ast
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EDITOR = 'erp.save_accessory_bom_edit(uuid,jsonb,timestamp with time zone,text)'
EDITOR_BODY_SHA256 = '6c8c701395ab74874e7cb2f3e78f9912f7380a5a3199cba069b1aec6db09cd85'
OLD = "    at = prod.at(f['day'], 0)\n"
NEW = '    at = __S05_REAL_CURRENT_AT__\n'
OLD_EXISTING = "        at = prod.at(f['day'], 17)  # after the committed GOOD source\n"
NEW_EXISTING = '        at = __S05_REAL_CURRENT_AT__  # after the committed GOOD source\n'


def successor_source(raw):
    text = raw.decode()
    function = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == 'recipe')
    original = ''.join(text.splitlines(keepends=True)[function.lineno - 1:function.end_lineno])
    if original.count(OLD) != 1 or original.count(OLD_EXISTING) != 1:
        raise ValueError('S05_RECIPE_EXACT_TWO_TIME_ANCHORS_REQUIRED')
    result = original.replace(OLD, NEW, 1).replace(OLD_EXISTING, NEW_EXISTING, 1)
    if result.replace(NEW, OLD, 1).replace(NEW_EXISTING, OLD_EXISTING, 1) != original:
        raise ValueError('S05_RECIPE_NONREVERSIBLE_DERIVATION')
    return result, dict(original_sha256=sha256(original.encode()).hexdigest(),
                       derived_sha256=sha256(result.encode()).hexdigest(), counted_time_substitutions=2,
                       all_membership_basis_settings_and_Native_command_code_retained=True)


def items(f, qty, rate, empty, method):
    if empty:
        return []
    return [dict(category_id=f['accessory']['category'], qty_per_good_fg_base=qty,
                 hpp_method=method, hpp_standard_rate=rate if method == 'BOM_STANDARD' else None,
                 hpp_uom_code=f['accessory']['pcs'], reimbursement_rate=rate,
                 reimbursement_uom_code=f['accessory']['pcs'])]


class LawfulRecipe:
    def __init__(self, business, raw, observations):
        self.business = business
        self.successor_code, self.derivation = successor_source(raw)
        self.observations = observations
        self.prepared = {}

    def __call__(self, cur, f, qty='0.5', rate='2', empty=False, method='BOM_STANDARD'):
        self.business.b.api.admin(cur)
        actual = cur.execute("select encode(sha256(convert_to(p.prosrc,'UTF8')),'hex') from pg_proc p where p.oid=%s::regprocedure", (EDITOR,)).fetchone()
        if actual != (EDITOR_BODY_SHA256,):
            raise ValueError('S05_EXACT_NATIVE_LEGACY_EDITOR_BODY_REQUIRED')
        if f['product'] in self.prepared:
            return self.successor(cur, f, qty, rate, empty, method)
        rows = cur.execute('select v.id::text,v.product_id::text,v.effective_from,v.effective_to,v.is_active,erp.accessory_bom_last_committed_at(v.id) from erp.accessory_bom_versions v where v.product_id=%s order by v.effective_from,v.id', (f['product'],)).fetchall()
        if len(rows) != 1:
            raise ValueError('S05_ONE_RETAINED_EMPTY_LEGACY_MASTER_REQUIRED')
        bom, product, start, end, active, last = rows[0]
        if product != f['product'] or end is not None or active is not True or last is not None:
            raise ValueError('S05_FIXTURE_LEGACY_MASTER_ALREADY_USED_OR_INACTIVE')
        if start > self.business.prod.at(f['day'], 0):
            raise ValueError('S05_LEGACY_MASTER_MUST_ALREADY_COVER_PHYSICAL_FIXTURE_DAY')
        root = cur.execute('select identity_root_id::text from erp.products where id=%s', (product,)).fetchone()
        if root != (product,):
            raise ValueError('S05_EXACT_OWNED_PRODUCT_ROOT_REQUIRED')
        counts = cur.execute('select (select count(*)from erp.accessory_bom_items where bom_version_id=%s),(select count(*)from erp.po_accessory_bom_commitments where bom_version_id=%s),(select count(*)from erp.fg_accessory_cost_snapshots where bom_version_id=%s),(select count(*)from erp.bf_sku_members_v1 where product_root=%s)', (bom, bom, bom, product)).fetchone()
        if counts != (0, 0, 0, 0):
            raise ValueError('S05_EMPTY_UNCOMMITTED_UNSHARED_LEGACY_MASTER_REQUIRED')
        expected = items(f, qty, rate, empty, method)
        self.business.prod.owner(cur)
        made = cur.execute('select erp.save_accessory_bom_edit(%s,%s::jsonb,null,%s)::text',
                           (bom, json.dumps(expected), 'S05 fixture: configure unused administrative legacy master before actual GOOD')).fetchone()[0]
        self.business.b.api.admin(cur)
        if made != bom:
            raise ValueError('S05_INITIAL_EDITOR_MUST_EDIT_UNUSED_MASTER_IN_PLACE')
        after = cur.execute('select v.id::text,v.product_id::text,v.effective_from,v.effective_to,v.is_active,erp.accessory_bom_last_committed_at(v.id) from erp.accessory_bom_versions v where v.product_id=%s order by v.effective_from,v.id', (product,)).fetchall()
        if after != rows:
            raise ValueError('S05_NATIVE_EDITOR_CHANGED_LEGACY_MASTER_WINDOW_OR_COMMITMENT')
        actual_items = cur.execute('select category_id::text,qty_per_good_fg_base,hpp_method,hpp_standard_rate,hpp_uom_code,reimbursement_rate,reimbursement_uom_code from erp.accessory_bom_items where bom_version_id=%s order by category_id,id', (bom,)).fetchall()
        wanted = [] if empty else [(f['accessory']['category'], Decimal(qty), method,
                                    Decimal(rate) if method == 'BOM_STANDARD' else None,
                                    f['accessory']['pcs'], Decimal(rate), f['accessory']['pcs'])]
        if actual_items != wanted:
            raise ValueError('S05_NATIVE_LEGACY_EDITOR_ITEMS_NOT_EXACT')
        event = dict(kind='ACTUAL_NATIVE_EDIT_OF_UNUSED_ADMINISTRATIVE_LEGACY_MASTER',
                     product_id=product, bom_version_id=bom, effective_from=str(start),
                     effective_window_unchanged=True, prior_items_commitments_snapshots_memberships=list(counts),
                     Native_editor_signature=EDITOR, Native_editor_body_sha256=EDITOR_BODY_SHA256,
                     items=deepcopy(expected), physical_fixture_day=str(f['day']),
                     historical_BF_creation_claim=False, no_clock_or_physical_date_override=True)
        self.observations.append(event)
        self.prepared[product] = bom
        return dict(kind=event['kind'], bom_version_id=bom)

    def successor(self, cur, f, qty, rate, empty, method):
        bom = self.prepared[f['product']]
        last = cur.execute('select erp.accessory_bom_last_committed_at(%s)', (bom,)).fetchone()[0]
        at = cur.execute('select statement_timestamp()').fetchone()[0]
        if last is None or not last < at:
            raise ValueError('S05_SUCCESSOR_REQUIRES_ACTUAL_PRIOR_GOOD_COMMITMENT')
        namespace = dict(self.business.__dict__, __S05_REAL_CURRENT_AT__=at)
        exec(compile(self.successor_code, str(ROOT/'scripts/cp7_accessory_standard_report/cases.py'), 'exec'), namespace)
        result = namespace['recipe'](cur, f, qty=qty, rate=rate, empty=empty, method=method)
        self.observations.append(dict(kind='ACTUAL_NATIVE_BF_SUCCESSOR_AFTER_GOOD', product_id=f['product'],
                                      old_bom_version_id=bom, prior_financial_commitment=str(last),
                                      effective_from=str(at), actual_statement_time=True,
                                      derivation=self.derivation, result=deepcopy(result),
                                      physical_fixture_day=str(f['day']), no_clock_or_physical_date_override=True))
        return result
