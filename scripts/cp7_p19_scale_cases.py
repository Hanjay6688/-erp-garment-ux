"""P19 full-application Native scale ladder: 100/300/1000/5000 current targets.

Measurement, not acceptance. Products and opening finished goods come from the
BB opening-balance importer; sales from the ordinary draft/post writers;
profiles, commercial SKUs, production policies and the work calendar from
their public commands. Nothing is inserted into a business table directly.
Every quantity, price, profile and policy is synthetic and labelled; none is
a factory default. No limit is raised and no source is sampled or cut: a size
refused by a cap or stopped at the existing 8 s limit records that refusal as
its measured result. Seeding is timed apart from application latency. The
explicit stand-in kernel benchmarks (cp7_p19_*_benchmark.mjs) stay separate.
"""
from datetime import timedelta
from decimal import Decimal
from math import ceil
from pathlib import Path
from time import monotonic
import hashlib
import json
import re
import uuid

import psycopg

import cp6_bb_probe as bbp
import cp6_bf_probe as bf
import cp7_analysis_cases as analysis
import cp7_p19_native_load_cases as load
import cp7_p19_transport_cases as transport

baseline = analysis.previous.baseline
history = baseline.history
supply = analysis.previous.supply
policies = analysis.previous.policies
b = analysis.b

IDS = dict(
    native=['P19S_NATIVE_SCALE_LADDER'],
    browser=['P19S_BROWSER_DESKTOP_100', 'P19S_BROWSER_DESKTOP_300', 'P19S_BROWSER_DESKTOP_1000', 'P19S_BROWSER_DESKTOP_5000'],
)
REQUIRED = {key: len(value) for key, value in IDS.items()}
EXPECTED = sum(REQUIRED.values())
CONTRACT = 'cp7.p19.full-application-scale.v1'
EVIDENCE_KIND = 'FULL_APPLICATION_NATIVE'
SIZES = (100, 300, 1000, 5000)
HISTORY_DAYS = (1, 30, 100)
GRID_BOUNDARY = dict(size=1000, days=101)
STATEMENT_TIMEOUT = '8s'
BODY_BYTES = 8000000
SEGMENT_CHARACTERS = 2000000
CLIENT_DOCUMENT_BYTES = 64000000
# Public writer/reader page bounds. Every row is written; paging is not sampling.
PROFILE_READ_PAGE, POLICY_READ_PAGE, POLICY_WRITE_PAGE, SKU_GROUP_PAGE = 200, 200, 100, 30
CAPS = {
    'STATEMENT_TIMEOUT_8S': dict(value='8s', codes=['57014', 'CP7_ANALYSIS_JOB_STOPPED'],
        where='existing authenticated statement limit (PostgREST role setting); SQL path sets the same 8s per public call',
        predicted_by_size_model=True),
    'HISTORY_SOURCE_PRODUCTS_1000': dict(value=1000, codes=['CP7_PLANNING_CAPTURE_INCOMPLETE'],
        where='scripts/cp7-src/planning/history-source.sql (more than 1000 current products: status INCOMPLETE); planning/history.sql history_build refuses',
        predicted_by_size_model=True),
    'HISTORY_GRID_100000': dict(value=100000, codes=['CP7_PLANNING_HISTORY_GRID_LIMIT', 'CP7_DEMAND_GRID_LIMIT'],
        where='planning/history.sql and demand/history.sql: products x history days', predicted_by_size_model=True),
    'DEMAND_ARRAYS': dict(value='targets 1000, events 50000, availability 100000', codes=['CP7_F04_ARRAY_LIMIT'],
        where='demand/history.sql cp7_demand.items', predicted_by_size_model=False),
    'BASELINE_ALLOCATION_100000': dict(value='positions x targets 100000, each list 1000', codes=['CP7_BASELINE_ALLOCATION_LIMIT'],
        where='baseline/allocation.sql', predicted_by_size_model=False),
    'NETTING_WORK_100000': dict(value='positions 1000, positions x baseline rows 100000', codes=['CP7_NETTING_WORK_LIMIT'],
        where='planning/netting.sql: more than 1000 WIP positions or positions x baseline rows above 100000',
        predicted_by_size_model=False),
    'NETTING_MATCH_5000': dict(value=5000, codes=['CP7_NETTING_MATCH_SOURCE_LIMIT'],
        where='planning/netting.sql matching_products', predicted_by_size_model=False),
    'SUPPLY_SCOPE_1000': dict(value='1000 scope ids per kind, 20000 facts', codes=['CP7_SUPPLY_GLOBAL_SCOPE_LIMIT', 'CP7_SUPPLY_FACT_LIMIT'],
        where='planning/supply-source.sql', predicted_by_size_model=False),
    'SEGMENT_2000000_CODE_POINTS': dict(value=2000000, codes=[],
        where='planning/analysis-jobs.sql segment cut; a cut, never a refusal', predicted_by_size_model=False),
    'BODY_8000000_BYTES': dict(value=8000000, codes=[],
        where="per segment; above it the panel switches from the single body to the same run's segments",
        predicted_by_size_model=False),
    'CLIENT_DOCUMENT_64000000_BYTES': dict(value=64000000, codes=[],
        where='src/nativeAnalysisTransport.ts ANALYSIS_DOCUMENT_UTF8_BYTES; the client refuses the whole document',
        predicted_by_size_model=False),
}
SYNTHETIC = dict(
    label='P19_SCALE_SYNTHETIC_NOT_FACTORY_DEFAULT', sizes_per_model=10, products_per_import_batch=250, cutover_days=10,
    opening_fg_pcs='50', opening_unit_cost='6.00', color_name='Blue',
    sale_rounds=[dict(days_before_today=3, qty_pcs=3), dict(days_before_today=2, qty_pcs=2)],
    sale_unit_price='20', sale_lines_per_note=100,
    profile=dict(mean_mode='SELECTED_MANUAL', daily_pcs='1', minimum_available_days='20', lead_days='3', review_days='7', buffer_days='0'),
    profile_reason='P19 scale synthetic selected profile; not a factory default', policy_state='ACTIVE',
    policy_reason='P19 scale synthetic ACTIVE review; not a factory default',
    sale_reason='P19 scale synthetic sale history through the ordinary Native sale writer',
    workload_calendar_margin_minutes=60,
    wip_fixture='one accepted cp7_analysis_cases.setup fixture: BB opening WIP 8 pcs, reviewed 9/10 yield, 45 work minutes',
    cutting_groups_seeded=0,
)
assert SYNTHETIC['workload_calendar_margin_minutes'] == load.CALENDAR_MARGIN_MINUTES
CP7_CODE = re.compile(r'CP7_[A-Z0-9_]+')
COMPUTE_PHASES = ('capture', 'request', 'run', 'job')


def ms(started):
    return round((monotonic() - started) * 1000, 3)


def digest(text):
    return hashlib.sha256(text.encode('UTF8')).hexdigest()


def witness(name, value, compact=False):
    # One complete file per stage; it survives a later assertion failure.
    root = Path(__file__).resolve().parents[1] / 'cp6-proof/t3'
    root.mkdir(parents=True, exist_ok=True)
    path = 'P19_SCALE_' + name + '.json'
    (root / path).write_text(json.dumps(dict(
        contract=CONTRACT, evidence_kind=EVIDENCE_KIND, stage_witness_only=True, Native_case_credit=0,
        kernel_evidence_reused=False, synthetic_inputs_label=SYNTHETIC['label'], limits_raised=False,
        owner_latency_acceptance=False, independent_acceptance=False, production_go=False, observed=value),
        ensure_ascii=False, indent=None if compact else 2, default=str) + '\n')
    return path


def refusal(error):
    message = (error.diag.message_primary or str(error)).strip()
    found = CP7_CODE.match(message)
    return dict(sqlstate=error.sqlstate, code=found.group(0) if found else error.sqlstate, message=message[:2000])


def public(cur, op):
    """One public call in its own subtransaction under the existing 8 s limit; never retried."""
    started = monotonic()
    try:
        with cur.connection.transaction():
            prior = cur.execute('show statement_timeout').fetchone()[0]
            cur.execute("set local statement_timeout='8s'")
            value = op()
            cur.execute("select set_config('statement_timeout',%s,true)", (prior,))
        return dict(outcome='RETURNED', ms=ms(started), value=value)
    except psycopg.Error as error:
        elapsed = ms(started)
        b.api.admin(cur)
        return dict(outcome='REFUSED', ms=elapsed, **refusal(error))


def phase(name, call, **extra):
    row = dict(name=name, outcome=call['outcome'], ms=call['ms'], **extra)
    row.update({key: call[key] for key in ('sqlstate', 'code', 'message') if key in call})
    return row


def timed(log, name, op):
    started = monotonic()
    value = op()
    row = log.setdefault(name, dict(calls=0, ms=0.0))
    row['calls'] += 1
    row['ms'] = round(row['ms'] + (monotonic() - started) * 1000, 3)
    return value


def current_targets(cur):
    # Same current-product predicate as cp7_planning.history_source; admin read.
    b.api.admin(cur)
    return [row[0] for row in cur.execute("""select coalesce(p.identity_root_id,p.id)::text||':'||p.size_id::text
        from erp.products p where p.effective_from<=clock_timestamp()
        and(p.effective_to is null or p.effective_to>clock_timestamp()) order by 1""").fetchall()]


def expected_caps(total, days):
    """Caps the declared counts meet. The existing 8 s limit may stop any point."""
    products = CAPS['HISTORY_SOURCE_PRODUCTS_1000']['value']
    caps = ['STATEMENT_TIMEOUT_8S']
    if total > products:
        caps.append('HISTORY_SOURCE_PRODUCTS_1000')
    if min(total, products + 1) * days > CAPS['HISTORY_GRID_100000']['value']:
        caps.append('HISTORY_GRID_100000')
    return caps


def cap_of(code):
    return next((name for name, cap in CAPS.items() if code in cap['codes']), None)


def source_cap(cur):
    """Which history-source bound the current Native data meets (admin read, not app latency).

    CP7_PLANNING_CAPTURE_INCOMPLETE is shared by every source-completeness
    condition, so every collection's row count is kept to show which one."""
    b.api.admin(cur)
    started = monotonic()
    status, rows = cur.execute("""select s->>'status',(select jsonb_object_agg(key,jsonb_array_length(value))
        from jsonb_each(s->'facts'))from(select cp7_planning.history_source()s)x""").fetchone()
    return dict(history_source_status=status, history_source_products_read=rows['products'], collection_rows=rows,
                other_collections_within_50000=all(n <= 50000 for k, n in rows.items() if k != 'products'),
                read_ms=ms(started), cap_products=CAPS['HISTORY_SOURCE_PRODUCTS_1000']['value'])


def supply_scope(cur):
    """PL-8: historical cutting groups drive the quadratic WIP normalisation. Count, never remove."""
    b.api.admin(cur)
    started = monotonic()
    try:
        with cur.connection.transaction():
            scope = cur.execute("select cp7_supply_native.wip_source_at(clock_timestamp())->'scope'").fetchone()[0]
        return dict(outcome='READ', read_ms=ms(started), **{k: len(v) for k, v in scope.items()})
    except psycopg.Error as error:
        b.api.admin(cur)
        return dict(outcome='REFUSED', read_ms=ms(started), **refusal(error))


def coverage(labels, recommended, warnings, status, expected):
    unreviewed = {w.split(':', 1)[1] for w in warnings if w.startswith('PRODUCTION_POLICY_UNREVIEWED:')}
    keys, wanted = set(labels), set(expected)
    out = dict(expected_targets=len(expected), source_targets=len(labels), recommended_targets=len(recommended),
               unreviewed_named_targets=len(unreviewed), analysis_status=status,
               source_equals_current_targets=keys == wanted and len(labels) == len(keys),
               recommendations_unique_and_known=len(recommended) == len(set(recommended)) and set(recommended) <= wanted,
               every_target_recommended_or_named=status == 'BLOCKED' or wanted <= set(recommended) | unreviewed)
    out['complete'] = all(out[k] for k in ('source_equals_current_targets', 'recommendations_unique_and_known',
                                           'every_target_recommended_or_named'))
    return out


def original(cur, run):
    """Digests of the stored immutable Original (admin read after the measured call)."""
    b.api.admin(cur)
    row = cur.execute("""with x as(select r.*,cp7_analysis_jobs.original(r)::text o from cp7_analysis_native.runs r where r.id=%s)
        select octet_length(o),length(o),encode(pg_catalog.sha256(convert_to(o,'UTF8')),'hex'),
        octet_length(result::text),encode(pg_catalog.sha256(convert_to(result::text,'UTF8')),'hex'),
        octet_length(facts::text),encode(pg_catalog.sha256(convert_to(facts::text,'UTF8')),'hex'),
        jsonb_array_length(facts->'facts'->'products'),jsonb_array_length(result->'recommendations')from x""", (run,)).fetchone()
    assert row, ('P19S_ORIGINAL_NOT_STORED', run)
    out = dict(zip(('original_utf8_bytes', 'original_characters', 'original_sha256', 'analysis_sql_text_utf8_bytes',
                    'analysis_sha256', 'facts_sql_text_utf8_bytes', 'facts_sha256', 'source_products', 'recommendations'), row))
    out.update(run_id=str(run), segment_count=ceil(out['original_characters'] / SEGMENT_CHARACTERS),
               single_body_bound_exceeded=out['analysis_sql_text_utf8_bytes'] > BODY_BYTES,
               client_document_bound_exceeded=out['original_utf8_bytes'] > CLIENT_DOCUMENT_BYTES)
    return out


def stored_coverage(cur, run, expected):
    b.api.admin(cur)
    labels, recommended, warnings, status = cur.execute("""select
        (select coalesce(jsonb_agg((x->>'root_id')||':'||(x->>'size_id')),'[]')from jsonb_array_elements(r.facts->'facts'->'products')x),
        (select coalesce(jsonb_agg(x->'target'->>'key'),'[]')from jsonb_array_elements(r.result->'recommendations')x),
        r.result->'generation_warnings',r.result->>'status' from cp7_analysis_native.runs r where r.id=%s""", (run,)).fetchone()
    return coverage(labels, recommended, warnings, status, expected)


def evidence(cur, envelope, expected):
    started = monotonic()
    try:
        analysis.checked(envelope)
        valid, error = True, None
    except Exception as failure:  # the frozen validator's own refusal is the evidence
        valid, error = False, str(failure)[:2000]
    x = envelope['analysis']
    cover = coverage([label['target_key'] for label in envelope['product_labels']],
                     [r['target']['key'] for r in x['recommendations']], x['generation_warnings'], x['status'], expected)
    return dict(run_id=envelope['run_id'], frozen_contract_valid=valid, frozen_contract_error=error,
                frozen_validator_ms_not_app_latency=ms(started), coverage=cover, coverage_complete=cover['complete'],
                original=original(cur, envelope['run_id']), original_recorded=True, source_state=envelope.get('source_state'))


def verdict(point):
    """The probe fails only on app misbehaviour; an honest cap or 8 s refusal is the measured result."""
    expected = point['expected_caps']
    structural = [c for c in expected if c != 'STATEMENT_TIMEOUT_8S']
    stopped = next((p for p in point['phases'] if p['outcome'] in ('REFUSED', 'JOB_FAILED')), None)
    if stopped is None:
        if point.get('job_not_terminal') or not point.get('original_recorded'):
            return dict(kind='EVIDENCE_MISSING', acceptable=False, counterexample=False)
        if structural:
            return dict(kind='BEYOND_CAP_NOT_REFUSED', caps=structural, acceptable=False, counterexample=True)
        failed = [k for k in ('coverage_complete', 'frozen_contract_valid', 'transport_exact') if point.get(k) is False]
        if failed:
            return dict(kind='RESULT_DEFECT', failed=failed, acceptable=False, counterexample=True)
        return dict(kind='COMPLETE_RESULT', acceptable=True, counterexample=False)
    cap = cap_of(stopped.get('code'))
    base = dict(phase=stopped['name'], code=stopped.get('code'), sqlstate=stopped.get('sqlstate'), cap=cap,
                time_to_refusal_ms=point.get('elapsed_to_stop_ms'))
    if point.get('result_saved_after_refusal'):
        return dict(base, kind='REFUSAL_SAVED_A_RESULT', acceptable=False, counterexample=True)
    if cap in expected:
        return dict(base, kind='HONEST_CAP_REFUSAL', structural_caps_also_apply=[c for c in structural if c != cap],
                    acceptable=True, counterexample=False)
    if cap is not None:
        return dict(base, kind='DECLARED_CAP_NOT_PREDICTED', acceptable=False, counterexample=False)
    return dict(base, kind='REFUSAL_OUTSIDE_DECLARED_CAPS', acceptable=False, counterexample=True)


def new_point(today, size, days, path, expected, **extra):
    key, q = uuid.uuid4(), history.query(today, days)
    products = CAPS['HISTORY_SOURCE_PRODUCTS_1000']['value']
    return key, q, dict(size=size, history_days=days, path=path, request_id=str(key), query=q,
                        expected_caps=expected_caps(len(expected), days),
                        grid_cells=min(len(expected), products + 1) * days, statement_timeout=STATEMENT_TIMEOUT,
                        phases=[], **extra)


def ordinary(cur, today, size, days, expected, boundary=False):
    key, q, point = new_point(today, size, days, 'ORDINARY_CAPTURE', expected,
                              public_rpc='erp_cp7_capture_analysis_v1', grid_boundary_witness=boundary)
    captured = public(cur, lambda: analysis.capture(cur, today, key, q=q))
    point['phases'].append(phase('capture', captured))
    point['request_to_result_ms'] = captured['ms']
    if captured['outcome'] == 'RETURNED':
        envelope = captured['value']
        point.update(evidence(cur, envelope, expected))
        point['original_witness'] = witness('ORIGINAL_%d_%d_ORDINARY' % (size, days),
                                            dict(point=dict(point), complete_original=envelope), True)
    else:
        point['elapsed_to_stop_ms'] = captured['ms']
        point['result_saved_after_refusal'] = transport.counts(cur, key)[0] != 0
    point['verdict'] = verdict(point)
    return point


def background(cur, today, size, days, expected):
    """Request -> run -> get, then manifest -> every segment -> serve; each call under 8 s."""
    key, q, point = new_point(today, size, days, 'BACKGROUND_JOB_SEGMENTS', expected, public_rpcs=list(transport.FUNCTIONS))
    elapsed = [0.0]

    def step(name, op, **extra):
        call = public(cur, op)
        elapsed[0] = round(elapsed[0] + call['ms'], 3)
        point['phases'].append(phase(name, call, **extra))
        if call['outcome'] != 'RETURNED' and 'elapsed_to_stop_ms' not in point:
            point['elapsed_to_stop_ms'] = elapsed[0]
        return call
    requested = step('request', lambda: transport.request(cur, today, key, q=q))
    if requested['outcome'] == 'RETURNED':
        point['requested_state'] = requested['value']['state']
        ran = step('run', lambda: transport.run(cur, key))
        if ran['outcome'] == 'RETURNED':
            job = point['job'] = ran['value']
            point['request_to_terminal_ms'] = elapsed[0]
            got = step('get', lambda: transport.status(cur, key))
            point['get_equals_run'] = got.get('value') == job
            if job['state'] == 'FAILED':
                point['phases'].append(dict(name='job', outcome='JOB_FAILED', ms=0.0, **job['failure']))
                point.setdefault('elapsed_to_stop_ms', point['request_to_terminal_ms'])
            elif job['state'] == 'DONE':
                transfer(cur, point, job['run_id'], step, expected)
            else:
                point['job_not_terminal'] = True
    stop = next((p['name'] for p in point['phases'] if p['outcome'] != 'RETURNED'), None)
    if stop in COMPUTE_PHASES:
        point['result_saved_after_refusal'] = transport.counts(cur, key)[0] != 0
    point['verdict'] = verdict(point)
    if point.get('complete_original') is not None:
        document = point.pop('complete_original')
        point['original_witness'] = witness('ORIGINAL_%d_%d_BACKGROUND' % (size, days),
                                            dict(point=dict(point), complete_original=document), True)
    return point


def transfer(cur, point, run, step, expected):
    manifest = step('manifest', lambda: transport.rpc(cur, 'erp_cp7_read_analysis_manifest_v1', (run,)))
    if manifest['outcome'] != 'RETURNED':
        return
    m = point['manifest'] = manifest['value']
    d = m['document']
    parts, exact = [], d['segment_characters'] == SEGMENT_CHARACTERS
    for index in range(d['segment_count']):
        read = step('segment', lambda: transport.rpc(cur, 'erp_cp7_read_analysis_segment_v1', (run, index, m['access_epoch'])),
                    index=index)
        if read['outcome'] != 'RETURNED':
            return
        s = read['value']
        raw = s['body'].encode('UTF8')
        ok = (s['index'], s['document_sha256'], s['document_utf8_bytes']) == (index, d['sha256'], d['utf8_bytes']) \
            and len(raw) == s['utf8_bytes'] <= BODY_BYTES and hashlib.sha256(raw).hexdigest() == s['sha256']
        point['phases'][-1].update(utf8_bytes=s['utf8_bytes'], segment_exact=ok)
        exact = exact and ok
        parts.append(s['body'])
    whole = ''.join(parts)
    raw = whole.encode('UTF8')
    exact = exact and len(raw) == d['utf8_bytes'] and len(whole) == d['characters'] and hashlib.sha256(raw).hexdigest() == d['sha256']
    assembled = {**json.loads(whole), 'source_state': m['source_state']}
    point['manifest_and_segments_ms'] = round(sum(p['ms'] for p in point['phases'] if p['name'] in ('manifest', 'segment')), 3)
    served = step('serve', lambda: analysis.read(cur, run))
    if served['outcome'] == 'RETURNED':
        point['assembled_equals_serve'] = assembled == served['value']
        exact = exact and point['assembled_equals_serve']
    point['transport_exact'] = exact
    point.update(evidence(cur, assembled, expected))
    point['complete_original'] = assembled


def diagnostics(cur, today, days):
    """PL-8 attribution: each step alone through its own public RPC under the same 8 s."""
    out = {}
    q = history.query(today, days)
    for name, op in (('demand_history', lambda: history.capture(cur, today, uuid.uuid4(), q=q)),
                     ('supply', lambda: supply.capture_query(cur, q, uuid.uuid4()))):
        call = public(cur, op)
        row = phase(name, call)
        if call['outcome'] == 'RETURNED' and name == 'supply':
            positions = call['value']['wip'].get('positions') or []
            row.update(wip_status=call['value']['wip'].get('status'), wip_positions=len(positions),
                       zero_quantity_wip_positions=sum(1 for p in positions if str(p.get('remaining_pcs')) == '0'))
        out[name] = row
    history_ok = out['demand_history']['outcome'] == 'RETURNED'
    supply_stop = out['supply']['outcome'] == 'REFUSED' and (
        history_ok or cap_of(out['supply'].get('code')) in ('SUPPLY_SCOPE_1000', 'NETTING_WORK_100000'))
    out['supply_step_stops_this_point'] = supply_stop
    out['attribution'] = ('DEMAND_HISTORY' if not history_ok else 'SUPPLY_BASELINE_WIP' if supply_stop
                          else 'LATER_STAGES_OR_NONE')
    out['not_app_latency'] = True
    return out


def import_batch(cur, today, count, log):
    """One BB opening-balance batch: masters, opening FG and one customer (no cutting group)."""
    s = SYNTHETIC
    code = 'P19S' + uuid.uuid4().hex[:7]
    sizes = min(count, s['sizes_per_model'])
    pairs = [(m, z) for m in range(ceil(count / s['sizes_per_model'])) for z in range(sizes)][:count]
    model, size_code = (lambda m: '{C}M%03d' % m), (lambda z: '{C}S%02d' % z)
    sku = lambda m, z: '{C}M%03dS%02d' % (m, z)
    total_pcs = count * int(s['opening_fg_pcs'])
    rows = dict(
        MODEL=[dict(model_code=model(m), model_name='P19 skala model %03d' % m) for m in sorted({m for m, _ in pairs})],
        SIZE=[dict(size_code=size_code(z)) for z in range(sizes)],
        BRAND=[dict(brand_code='{C}', brand_name='P19 skala merek')],
        PRODUCT=[dict(sku=sku(m, z), product_name='P19 skala %03d-%02d' % (m, z), model_code=model(m), brand_code='{C}',
                      color_name=s['color_name'], size_code=size_code(z)) for m, z in pairs],
        LOCATION=[dict(location_code='{C}G', location_name='P19 skala gudang FG', location_type='FG_WAREHOUSE')],
        CUSTOMER=[dict(customer_code='{C}C', customer_name='P19 skala pelanggan')],
        OPENING_BALANCE_ITEM=[dict(balance_type='FINISHED_GOODS', product_sku=sku(m, z), brand_code='{C}', model_code=model(m),
                                   color_name=s['color_name'], size_code=size_code(z), location_code='{C}G', qty=s['opening_fg_pcs'],
                                   unit_cost=s['opening_unit_cost'], control_key='FG') for m, z in pairs],
        OPENING_CONTROL=[dict(control_key='FG', balance_type='FINISHED_GOODS', qty=str(total_pcs),
                              amount=str(Decimal(s['opening_unit_cost']) * total_pcs))])
    assert sum(map(len, rows.values())) <= 5000, 'P19S_BB_BATCH_ROWS'
    fx = timed(log, 'bb_opening_import_batch', lambda: bbp.production_post(cur, today, rows, code=code, cutover_days=s['cutover_days']))
    b.api.admin(cur)
    products = cur.execute("""select lower(p.sku),p.id::text,coalesce(p.identity_root_id,p.id)::text,
        coalesce(p.identity_root_id,p.id)::text||':'||p.size_id::text from erp.products p where lower(p.sku) like lower(%s)""",
                           (code + 'M%',)).fetchall()
    customer = cur.execute('select id::text from erp.customers where lower(customer_code)=lower(%s)', (code + 'C',)).fetchone()
    assert len(products) == count and customer and fx['fg'], ('P19S_IMPORT_RESULT', code, len(products))
    model_of = {sku(m, z).replace('{C}', code).lower(): m for m, z in pairs}
    return [dict(code=code, product=pid, root=root, target=target, model=model_of[key], location=fx['fg'], customer=customer[0])
            for key, pid, root, target in products]


def sell(cur, today, seeded, log):
    """Posted sale history through the ordinary draft and post writers, at most 100 lines per note."""
    s, lines, by_code = SYNTHETIC, SYNTHETIC['sale_lines_per_note'], {}
    for row in seeded:
        by_code.setdefault(row['code'], []).append(row)
    for sale in s['sale_rounds']:
        at = history.receipt.aa.at(today - timedelta(days=sale['days_before_today']), 10).isoformat()
        for code, rows in by_code.items():
            for start in range(0, len(rows), lines):
                chunk = rows[start:start + lines]
                payload = dict(sale_number='%s-D%d-%03d' % (code, sale['days_before_today'], start // lines),
                               customer_id=chunk[0]['customer'], source_location_id=chunk[0]['location'], sale_date=at,
                               reason=s['sale_reason'], items=[dict(product_id=r['product'], qty_pcs=sale['qty_pcs'],
                               unit_price_snapshot=s['sale_unit_price'], discount_amount='0') for r in chunk])
                draft = timed(log, 'sale_draft_writer',
                              lambda: b.chain.production.rpc(cur, 'erp.save_sale_draft_v2', payload, uuid.uuid4(), None))
                b.api.admin(cur)
                timed(log, 'sale_post_writer', lambda: history.sales.fg.post_sale(cur, draft))


def profile(cur, roots, log):
    s = SYNTHETIC
    for start in range(0, len(roots), PROFILE_READ_PAGE):
        rows = timed(log, 'profile_reader', lambda: baseline.get(cur, roots[start:start + PROFILE_READ_PAGE]))['rows']
        for row in rows:
            timed(log, 'profile_writer', lambda: baseline.save(cur, dict(
                root_id=row['root_id'], product_version_id=row['product_version_id'], expected_revision=row['revision'],
                reason=s['profile_reason'], config=dict(s['profile']))))


def commercial(cur, seeded, log):
    """One commercial SKU per synthetic model, its sizes as members."""
    models = {}
    for row in seeded:
        models.setdefault((row['code'], row['model']), []).append(row['root'])
    keys, skus = list(models), []
    for start in range(0, len(keys), SKU_GROUP_PAGE):
        b.api.admin(cur)
        at = cur.execute('select clock_timestamp()').fetchone()[0]
        groups = [bf.group(cur, models[key], at, settings=dict(price=None, bom=None, work_rates=[], laundry_rates=[]))
                  for key in keys[start:start + SKU_GROUP_PAGE]]
        timed(log, 'commercial_sku_writer', lambda: bf.save(cur, groups, at))
        skus += [g['id'] for g in groups]
    return skus


def activate(cur, skus, log):
    s = SYNTHETIC
    for start in range(0, len(skus), POLICY_READ_PAGE):
        rows = timed(log, 'policy_reader', lambda: policies.get(cur, skus[start:start + POLICY_READ_PAGE]))['rows']
        for first in range(0, len(rows), POLICY_WRITE_PAGE):
            changes = [dict(policies.proposal(row, s['policy_state']), reason=s['policy_reason'])
                       for row in rows[first:first + POLICY_WRITE_PAGE]]
            timed(log, 'policy_writer', lambda: policies.apply(cur, changes))


def calendar(cur, today, log):
    # The review is bound to the current source; above the history cap the
    # supply read refuses and that refusal is recorded, never worked around.
    started = monotonic()
    try:
        with cur.connection.transaction():
            review = load.reviewed_workload_calendar(cur, today)
        outcome = dict(outcome='REVIEWED', **{k: review[k] for k in (
            'reviewed_position_count', 'selected_total_work_minutes', 'reviewed_capacity_minutes', 'margin_minutes')})
    except psycopg.Error as error:
        b.api.admin(cur)
        outcome = dict(outcome='REFUSED', cap=None, **refusal(error))
        outcome['cap'] = cap_of(outcome['code'])
    log['calendar_review'] = dict(calls=1, ms=ms(started))
    return outcome


def ensure(cur, today, size, wip_done):
    """Grow the global current Native target set to `size` through ordinary writers only."""
    started, log = monotonic(), {}
    if not wip_done:
        timed(log, 'wip_fixture_analysis_setup', lambda: analysis.setup(cur, today))
    before = current_targets(cur)
    missing = size - len(before)
    assert missing >= 0, ('P19S_SIZE_NOT_CONSTRUCTIBLE_PREEXISTING_TARGETS', size, len(before))
    seeded, page = [], SYNTHETIC['products_per_import_batch']
    for offset in range(0, missing, page):
        seeded += import_batch(cur, today, min(page, missing - offset), log)
    sell(cur, today, seeded, log)
    profile(cur, [row['root'] for row in seeded], log)
    activate(cur, commercial(cur, seeded, log), log)
    review = calendar(cur, today, log)
    after = current_targets(cur)
    assert len(after) == size and set(before) <= set(after), ('P19S_TARGET_COUNT', size, len(after))
    assert {row['target'] for row in seeded} == set(after) - set(before), 'P19S_SEEDED_TARGETS_DIFFER'
    return dict(size=size, preexisting_targets=len(before), seeded_targets=len(seeded), total_targets=len(after),
                target_keys_sha256=digest('\n'.join(after)), seed_ms=ms(started), writer_phases=log,
                calendar_review=review, supply_scope=supply_scope(cur), synthetic_inputs=SYNTHETIC,
                seed_is_application_latency=False, direct_business_inserts=False)


def observe(cur, actor, requests, run, label):
    """Read-back of one browser click on the disposable copy (admin read, not app latency)."""
    b.api.admin(cur)
    out = dict(actor_runs=cur.execute('select count(*) from cp7_analysis_native.runs where actor=%s', (actor,)).fetchone()[0],
               requests={str(r): dict(zip(('runs', 'documents', 'jobs'), transport.counts(cur, r))) for r in requests},
               jobs=[dict(zip(('request_id', 'state', 'attempts', 'failure_sqlstate', 'failure_code', 'run_id'), row))
                     for row in cur.execute("""select request_id::text,state,attempts,failure_sqlstate,failure_code,run_id::text
                        from cp7_analysis_jobs.jobs where actor=%s order by requested_at""", (actor,)).fetchall()],
               runs=[dict(zip(('run_id', 'request_id'), row)) for row in cur.execute(
                   'select id::text,request_id::text from cp7_analysis_native.runs where actor=%s order by captured_at', (actor,)).fetchall()])
    if run:
        out['original'] = original(cur, run)
        out['coverage'] = stored_coverage(cur, run, current_targets(cur))
        text = cur.execute('select cp7_analysis_jobs.original(r)::text from cp7_analysis_native.runs r where r.id=%s', (run,)).fetchone()[0]
        root = Path(__file__).resolve().parents[1] / 'cp6-proof/t3'
        root.mkdir(parents=True, exist_ok=True)
        name = 'P19_SCALE_BROWSER_ORIGINAL_' + label + '.json'
        (root / name).write_text(text)  # the exact stored Original text, byte for byte
        assert digest((root / name).read_text()) == out['original']['original_sha256']
        out['original_witness'] = name
    return out


def compact(point):
    return {k: v for k, v in point.items() if k not in ('manifest', 'job')} | dict(
        job_state=(point.get('job') or {}).get('state'), segment_count=(point.get('manifest') or {}).get('document', {}).get('segment_count'))


def cases(cur, today):
    def ladder():
        rows, points, wip = [], [], False
        products = CAPS['HISTORY_SOURCE_PRODUCTS_1000']['value']
        for size in SIZES:
            seed = ensure(cur, today, size, wip)
            wip = True
            expected = current_targets(cur)
            cap = source_cap(cur)
            witness('SEED_%d' % size, dict(seed, history_source=cap))
            before = b.boundary.snapshot(cur)
            measured, attribution = [], {}
            for days in HISTORY_DAYS:
                measured += [ordinary(cur, today, size, days, expected), background(cur, today, size, days, expected)]
                attribution[days] = diagnostics(cur, today, days)
            if size == GRID_BOUNDARY['size']:
                measured.append(ordinary(cur, today, size, GRID_BOUNDARY['days'], expected, True))
            unchanged = b.boundary.snapshot(cur) == before
            row = dict(size=size, total_targets=len(expected), seed_ms_not_app_latency=seed['seed_ms'],
                       writer_phases=seed['writer_phases'], calendar_review=seed['calendar_review'],
                       supply_scope=seed['supply_scope'], history_source=cap,
                       source_model_consistent=cap['history_source_products_read'] == min(size, products + 1)
                       and cap['other_collections_within_50000']
                       and (cap['history_source_status'] == 'COMPLETE') == (size <= products),
                       step_attribution=attribution, Native_business_unchanged_by_measurement=unchanged,
                       points=[compact(p) for p in measured])
            witness('SIZE_%d' % size, row)
            rows.append(row)
            points += measured
            assert unchanged, ('P19S_MEASUREMENT_CHANGED_NATIVE_BUSINESS', size)
        verdicts = [p['verdict'] for p in points]
        consistent = all(row['source_model_consistent'] for row in rows)
        status = ('COUNTEREXAMPLE' if any(v['counterexample'] for v in verdicts)
                  else 'PASS' if consistent and all(v['acceptable'] for v in verdicts) else 'INCOMPLETE')
        return dict(status=status, evidence_kind=EVIDENCE_KIND, contract=CONTRACT, sizes=rows,
                    verdict_counts={k: sum(v['kind'] == k for v in verdicts) for k in sorted({v['kind'] for v in verdicts})},
                    source_model_consistent=consistent, statement_timeout=STATEMENT_TIMEOUT, limits_raised=False,
                    data_sampled_or_truncated=False, seed_time_reported_apart=True, kernel_evidence_reused=False,
                    synthetic_inputs=SYNTHETIC, owner_latency_acceptance=False, full_P19_acceptance=False,
                    factory_capacity_or_SLA=False, production_go=False)
    return [(IDS['native'][0], ladder)]


def races(tools, today):
    # Concurrency at scale is not part of this declared budget (see README).
    return []


def http_cases(http, today):
    # Real Auth/PostgREST is measured inside the browser cases (same copy, same seeding).
    return []
