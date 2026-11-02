"""Three prepared Native FREE date cases; no connection or runtime on import.

The accepted actual complete-DE parent and this closed physical source are
required before ERP imports. An owning disposable caller must still provide
the original strict runner, full restoration and every outer package gate.
"""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import ast, importlib, importlib.util, inspect, json, os, subprocess, uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IDS = (
    'FREE_DATE_NATIVE_WIB_INCLUSIVE_LOOKUP_AND_NORMAL_PUBLIC_QUOTE',
    'FREE_DATE_NATIVE_FINAL_DAY_POST_STOCK_GL_AND_EXACT_REPLAY',
    'FREE_DATE_NATIVE_POSTED_HISTORY_AFTER_ELIGIBILITY_ENDS',
)
WIB = ZoneInfo('Asia/Jakarta')
ZONES = ('UTC', 'Asia/Jakarta', 'America/New_York', 'Pacific/Kiritimati')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_controls():
    """Read immutable fixture/runner bytes without importing their ERP graph."""
    value = json.loads((HERE / 'FREE_NATIVE3_SOURCE.json').read_bytes())
    if (value['case_ids'] != list(IDS) or len(set(IDS)) != 3
            or value['actual_Native_cases'] != 0
            or value['fixture_or_runner_changes'] != 0):
        raise ValueError('FREE_DATE_NATIVE_EXACT_THREE_PREPARED_CASES_REQUIRED')
    for name, pin in value['unchanged_sources'].items():
        path = ROOT / name
        raw = path.read_bytes()
        original = subprocess.check_output(
            ['/usr/bin/git', '-C', str(ROOT), 'show', value['head'] + ':' + name],
            env=dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0'))
        if (path.is_symlink() or len(raw) != pin['bytes']
                or sha256(raw).hexdigest() != pin['sha256'] or raw != original):
            raise ValueError('FREE_DATE_NATIVE_UNCHANGED_FIXTURE_OR_RUNNER_REQUIRED:' + name)
        compile(raw, str(path), 'exec')
    own = ast.parse(Path(__file__).read_bytes())
    declared = [ast.literal_eval(n.value) for n in own.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'IDS' for t in n.targets)]
    if declared != [IDS]:
        raise ValueError('FREE_DATE_NATIVE_EXACT_DECLARED_IDS_REQUIRED')
    return dict(status='PREPARED_NATIVE_FREE3_SOURCE_NOT_EXECUTED', case_ids=list(IDS),
                unchanged_fixture_and_runner_files=len(value['unchanged_sources']),
                fixture_or_runner_changes=0, actual_Native_cases=0,
                actual_SQL_executed=0, production_go=False, independent_acceptance=False)


def timeline(today):
    """All posting timestamps precede the actual supplied WIB business day."""
    end = today - timedelta(days=1)
    start = end - timedelta(days=2)
    first = datetime.combine(start, time.min, WIB)
    following = datetime.combine(end + timedelta(days=1), time.min, WIB)
    points = ((first - timedelta(microseconds=1), False), (first, True),
              (datetime.combine(end, time.min, WIB), True),
              (following - timedelta(microseconds=1), True), (following, False))
    return start, end, tuple((at.isoformat(), eligible) for at, eligible in points)


def setup(cur, today, bc):
    bc.api.admin(cur)
    actor = cur.execute("""select u.is_active,r.role_code,r.is_active
        from erp.app_users u join erp.app_roles r on r.id=u.role_id
        where u.auth_user_id=%s""", (bc.api.base.OPERATOR_AUTH,)).fetchall()
    if actor != [(True, 'OWNER', True)]:
        raise ValueError('FREE_DATE_NATIVE_ORIGINAL_ACTIVE_OWNER_REQUIRED_WITHOUT_PROMOTION')
    start, end, points = timeline(today)
    fx = bc.fixture(cur, today, zones=False)
    bc.policy(cur, 'ERP_DEC02', dict(special_free_category_ids=[fx['category']]))
    bc.api.admin(cur)
    prior = cur.execute('select count(*) from erp.contractor_hpp_policy_versions '
                        'where contractor_id=%s', (fx['mandor'],)).fetchone()[0]
    if prior != 0:
        raise ValueError('FREE_DATE_NATIVE_NEW_CONTRACTOR_POLICY_FIXTURE_REQUIRED')
    cur.execute("""insert into erp.contractor_hpp_policy_versions
        (contractor_id,effective_from,effective_to,contractor_role_snapshot,
         attendance_required_snapshot,is_special,reason)
        values(%s,%s,%s,'MANDOR',false,true,'Native FREE WIB date fixture')""",
        (fx['mandor'], start, end))
    version = str(cur.execute("select erp.bc_policy_version_v1('ERP_DEC02')").fetchone()[0])
    expected = dict(category_id=fx['category'], policy_version=version)
    return fx, start, end, points, expected


def basis(cur, fx, at, bc, *, material=None, contractor=None):
    bc.api.admin(cur)
    return cur.execute('select erp.bc_free_basis_v1(%s::uuid,%s::uuid,%s::timestamptz)',
                       (material or fx['material'], contractor or fx['mandor'], at)).fetchone()[0]


def quote(cur, fx, at, bc):
    value = bc.note_read(cur, dict(contractor_id=fx['mandor'], location_id=fx['main'],
                                  physical_at=at, material_query=fx['code'].lower()))
    rows = [row for row in value['materials'] if row['id'] == fx['material']]
    if len(rows) != 1:
        raise ValueError('FREE_DATE_NATIVE_NORMAL_PUBLIC_QUOTE_MATERIAL_REQUIRED')
    return rows[0]['free']


def lookup_case(cur, today, bc):
    fx, start, end, points, expected = setup(cur, today, bc)
    bc.api.admin(cur)
    zone = cur.execute('show TimeZone').fetchone()[0]
    rows = []
    try:
        for name in ZONES:
            cur.execute("select set_config('TimeZone',%s,true)", (name,))
            for at, eligible in points:
                actual = basis(cur, fx, at, bc)
                if actual != (expected if eligible else None):
                    raise ValueError('FREE_DATE_NATIVE_WIB_INCLUSIVE_BOUNDARY_FAILED')
                rows.append(dict(session_timezone=name, at=at, expected_eligible=eligible,
                                 actual=actual))
            # The ordinary form accepts seconds, while the lower lookup also
            # tests the last microsecond. Both are before the real current day.
            at = end.isoformat() + 'T23:59:59+07:00'
            if quote(cur, fx, at, bc) != expected:
                raise ValueError('FREE_DATE_NATIVE_NORMAL_PUBLIC_FINAL_DAY_QUOTE_FAILED')
            bc.api.admin(cur)
        absent = str(uuid.uuid4())
        if (basis(cur, fx, points[1][0], bc, material=absent) is not None
                or basis(cur, fx, points[1][0], bc, contractor=absent) is not None
                or basis(cur, fx, None, bc) is not None):
            raise ValueError('FREE_DATE_NATIVE_ABSENT_ID_OR_NULL_MUST_REMAIN_INELIGIBLE')
    finally:
        bc.api.admin(cur)
        cur.execute("select set_config('TimeZone',%s,true)", (zone,))
    return dict(status='PASS', policy_from=start.isoformat(), policy_to=end.isoformat(),
                actual_lookup_observations=rows, actual_public_final_day_quotes=len(ZONES),
                null_and_absent_ids_ineligible=True, product_clock_changed=False,
                GOOD_eligibility_policy_decided=False)


def posted_snapshot(cur, issue, bc):
    bc.api.admin(cur)
    return cur.execute("""select jsonb_build_object(
        'header',(select to_jsonb(h) from erp.contractor_material_issues h where h.id=%s),
        'items',(select jsonb_agg(to_jsonb(i) order by i.id)
                 from erp.contractor_material_issue_items i where i.issue_id=%s),
        'free_provenance',(select jsonb_agg(to_jsonb(f) order by f.material_id)
                 from erp.bc_free_issue_lines_v1 f where f.issue_id=%s))""",
        (issue, issue, issue)).fetchone()[0]


def post_one(cur, today, bc):
    fx, start, end, points, expected = setup(cur, today, bc)
    at = end.isoformat() + 'T23:59:59+07:00'
    if basis(cur, fx, at, bc) != expected or quote(cur, fx, at, bc) != expected:
        raise ValueError('FREE_DATE_NATIVE_FINAL_DAY_MUST_BE_ELIGIBLE_BEFORE_POST')
    before = bc.ledger(cur)
    stock = bc.stock(cur, fx['material'], fx['main'])
    key = str(uuid.uuid4())
    payload = dict(number=bc.tag(), contractor_id=fx['mandor'], location_id=fx['main'],
                   po_id=None, physical_at=at, notes='Native FREE last valid WIB day',
                   reason='Native FREE last valid WIB day', items=[dict(
                       material_id=fx['material'], qty='3', mode='FREE',
                       free_policy_version=expected['policy_version'])])
    made = bc.note_call(cur, 'POST', payload, key=key)
    issue = made['id']
    moved = bc.delta(before, bc.ledger(cur))
    if (bc.stock(cur, fx['material'], fx['main']) != stock - 3
            or moved.get('MATERIAL_INVENTORY') != Decimal('-6.00')
            or any(moved.get(k, 0) != 0 for k in
                   ('CONTRACTOR_RECEIVABLE', 'CASH', 'BANK', 'OTHER_INCOME'))
            or sum(moved.values(), Decimal(0)) != 0):
        raise ValueError('FREE_DATE_NATIVE_SINGLE_FREE_POST_STOCK_AND_MONEY_FAILED')
    stored = bc.q(cur, 'select total_receivable,manual_retail_unit_price '
                  'from erp.contractor_material_issue_items where issue_id=%s', issue)
    provenance = bc.q(cur, 'select category_id::text,policy_version '
                      'from erp.bc_free_issue_lines_v1 where issue_id=%s', issue)
    if (stored != [(Decimal(0), Decimal(0))]
            or provenance != [(fx['category'], int(expected['policy_version']))]):
        raise ValueError('FREE_DATE_NATIVE_ZERO_PRICE_AND_ACTUAL_POLICY_PROVENANCE_REQUIRED')
    return dict(fx=fx, issue=issue, made=made, payload=payload, key=key, expected=expected,
                at=at, stock_after=bc.stock(cur, fx['material'], fx['main']),
                ledger_before=before, ledger_after=bc.ledger(cur), snapshot=posted_snapshot(cur, issue, bc),
                stock_before=str(stock), ledger_delta={k:str(v) for k,v in moved.items()})


def replay_case(cur, today, bc):
    item = post_one(cur, today, bc)
    again = bc.note_call(cur, 'POST', item['payload'], key=item['key'])
    after_snapshot = posted_snapshot(cur, item['issue'], bc)
    after_ledger = bc.ledger(cur)
    after_stock = bc.stock(cur, item['fx']['material'], item['fx']['main'])
    if (again != item['made'] or after_snapshot != item['snapshot']
            or after_ledger != item['ledger_after'] or after_stock != item['stock_after']):
        raise ValueError('FREE_DATE_NATIVE_EXACT_POST_REPLAY_MUST_HAVE_ZERO_NEW_EFFECT')
    return dict(status='PASS', issue_id=item['issue'], physical_at=item['at'],
                actual_posted_snapshot=item['snapshot'], ledger_delta=item['ledger_delta'],
                actual_posted_snapshot_after_replay=after_snapshot,
                stock_before=item['stock_before'], stock_after_post=str(item['stock_after']),
                stock_after_replay=str(after_stock),
                account_balances_before={k:str(v) for k,v in item['ledger_before'].items()},
                account_balances_after_post={k:str(v) for k,v in item['ledger_after'].items()},
                account_balances_after_replay={k:str(v) for k,v in after_ledger.items()},
                actual_replay_response=again, replay_stock_GL_and_history_unchanged=True,
                original_normal_post_route=True, source_lines=1, paid_companion_lines=0,
                mandatory_PO_or_FG_match=False, product_clock_changed=False)


def history_case(cur, today, bc):
    item = post_one(cur, today, bc)
    later = today.isoformat() + 'T00:00:00+07:00'
    if basis(cur, item['fx'], later, bc) is not None:
        raise ValueError('FREE_DATE_NATIVE_DAY_AFTER_POLICY_END_MUST_BE_INELIGIBLE')
    view = bc.note_read(cur, dict(id=item['issue'], contractor_id=item['fx']['mandor'],
                                 location_id=item['fx']['main'], physical_at=later,
                                 material_ids=[item['fx']['material']]))
    document = view['document']
    after_snapshot = posted_snapshot(cur, item['issue'], bc)
    after_ledger = bc.ledger(cur)
    after_stock = bc.stock(cur, item['fx']['material'], item['fx']['main'])
    if (document is None or document['id'] != item['issue']
            or len(document['items']) != 1 or document['items'][0]['free'] is not True
            or Decimal(document['items'][0]['amount']) != 0
            or after_snapshot != item['snapshot'] or after_ledger != item['ledger_after']
            or after_stock != item['stock_after']):
        raise ValueError('FREE_DATE_NATIVE_POSTED_FREE_HISTORY_MUST_NOT_BE_REPRICED')
    return dict(status='PASS', issue_id=item['issue'], original_physical_at=item['at'],
                later_quote_at=later, later_eligibility=None, actual_original_snapshot=item['snapshot'],
                actual_posted_snapshot_after_read=after_snapshot,
                account_balances_before_read={k:str(v) for k,v in item['ledger_after'].items()},
                account_balances_after_read={k:str(v) for k,v in after_ledger.items()},
                stock_before_read=str(item['stock_after']),stock_after_read=str(after_stock),
                actual_public_document=document, stock_GL_and_posted_history_unchanged=True,
                posted_row_updates=0, policy_history_rewrites=0,
                GOOD_eligibility_policy_decided=False, product_clock_changed=False)


def runtime_modules():
    """Bind unchanged owning fixture/runner files without canonical cache reuse.

    The complete inherited runtime can import its own historical fixtures.
    Those canonical module-cache entries are not the owning fixture contract.
    Fresh private aliases execute the exact pinned owning files, while their
    ordinary dependency imports and the natural product graph stay unchanged.
    This SAME function runs in the preDB fence and the actual Native caller.
    """
    admission = load('free_date_runtime_actual_parent', HERE / 'admission.py')
    admission.parent_receipt()
    source_controls()
    with admission.import_scope():
        product = importlib.import_module('cp7_current_de_free_date.composition')
        product.runtime()  # Include the real full inherited runtime import path.
        bc = load('free_date_exact_owning_Native_fixture', ROOT / 'scripts/cp6_bc_probe.py')
        runner = load('free_date_exact_owning_strict_runner', ROOT / 'scripts/cp6_auditor_runner.py')
        modules = {}
        for module, name in ((product, 'cp7_current_de_free_date/composition.py'),
                             (bc, 'cp6_bc_probe.py'), (runner, 'cp6_auditor_runner.py')):
            expected = ROOT / 'scripts' / name
            actual = Path(module.__file__).resolve()
            if actual != expected or actual.read_bytes() != expected.read_bytes():
                raise ValueError('FREE_DATE_NATIVE_EXACT_NATURAL_MODULE_ORIGIN_REQUIRED:' + name)
            raw = actual.read_bytes()
            modules[name] = dict(bytes=len(raw), sha256=sha256(raw).hexdigest(), path=str(actual))
        checks = ((bc.fixture, (None, None), dict(zones=False)),
                  (bc.note_read, (None, {}), {}), (bc.note_call, (None, 'POST', {}), dict(key='source-only')),
                  (bc.ledger, (None,), {}), (bc.stock, (None, 'source-only', 'source-only'), {}),
                  (runner.strict_group, ('source-only', None, None), {}),
                  (runner.public_state, (None,), {}))
        for operation, args, kwargs in checks:
            inspect.signature(operation).bind(*args, **kwargs)
        if not callable(bc.api.admin) or not hasattr(bc.api.base, 'OPERATOR_AUTH'):
            raise ValueError('FREE_DATE_NATIVE_REAL_FIXTURE_API_REQUIRED')
        if runner.r1.OUT != ROOT / 'cp6-proof/aw':
            raise ValueError('FREE_DATE_NATIVE_REAL_OWNING_ORIGINAL_OUTPUT_REQUIRED')
        proof = dict(status='EXACT_OWNING_FREE3_FIXTURE_AND_STRICT_RUNNER_BOUND_BEFORE_SQL',
                     actual_working_directory=str(Path.cwd()),
                     modules=modules, callable_API_bindings=len(checks),
                     private_fixture_and_runner_aliases=True, canonical_module_cache_replaced=False,
                     fixture_or_runner_original_files_changed=False,
                     actual_original_output=str(runner.r1.OUT), actual_SQL_executed=0, actual_Native_cases=0)
    return product, bc, runner, proof


def bind(state):
    admission = load('free_date_Native_actual_parent_before_ERP', HERE / 'admission.py')
    receipt = admission.parent_receipt()  # Before source/fixture/runner/ERP imports.
    load('free_date_Native_closed_physical_source', HERE / 'source.py').preflight()
    proof = source_controls()
    with admission.import_scope():
        product, bc, runner, bindings = runtime_modules()
        accepted = product.qualified_parent_sources(receipt, state['predecessor']['sources'])
        if state['qualified_parent_sources'] != accepted or state['sources'] != product.sources():
            raise ValueError('FREE_DATE_NATIVE_ACTUAL_WHOLE_PARENT_AND_DATE_SOURCE_REQUIRED')
    def cases(cur, today):
        return [(IDS[0], lambda: lookup_case(cur, today, bc)),
                (IDS[1], lambda: replay_case(cur, today, bc)),
                (IDS[2], lambda: history_case(cur, today, bc))]
    return SimpleNamespace(product=product, fixture=bc, runner=runner, cases=cases,
                           IDS=IDS, source_control=dict(proof, actual_runtime_bindings=bindings), actual_Native_cases=0)
