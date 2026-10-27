"""Focused transport fixtures; Native source capture is explicitly not HTTP credit."""
from contextlib import contextmanager
from copy import deepcopy
from time import monotonic
import uuid
import cp7_ow12b_choice_preparation_cases as B

parent, plan, reader = B.parent, B.plan, B.reader
STATE = CHECKER = None
PREP = {verb: 'erp_cp7_' + verb + '_frozen_choice_preparation_v1'
        for verb in ('request', 'get', 'step')}
READ, SAVE = reader.RPC, parent.RPC
IDS = dict(http=[
    'CURRENT_CHOICE_AUTH_COLD_REOPEN_PREPARE_SAVE_REPLAY',
    'CURRENT_CHOICE_AUTH_CHANGED_SOURCE_REFUSES_SAVE',
    'CURRENT_CHOICE_AUTH_FOREIGN_EPOCH_ANON_REVOKED'], races=[
    'CURRENT_CHOICE_RACE_ENQUEUE_SAME_WORK',
    'CURRENT_CHOICE_RACE_STEP_SAME_PAYLOAD',
    'CURRENT_CHOICE_RACE_REVOKED_AFTER_WORK'])


@contextmanager
def installed(state, checker):
    global STATE, CHECKER
    old = STATE, CHECKER
    STATE, CHECKER = state, checker
    try:
        yield dict(Native_fixture_not_HTTP_capture=True,
                   original_B_routes_unchanged=True, preparation_public_RPCs=3,
                   actual_Auth_cases=3, actual_two_backend_cases=3,
                   browser_claim=False, factory_claim=False, production_go=False)
    finally:
        STATE, CHECKER = old


def fixture(cur, today, actor, observed):
    CHECKER(cur)
    # Same posted Native setup as B.prepare, with the real signed-in actor
    # supplied before capture. Never rewrite a captured job's actor or claims.
    x = plan.fixture(cur, today)
    imported = reader.reader.volume.import_batch(cur, today, 11, reader.reader.volume.Phases())
    historical = reader.reader.historical.seed(cur, imported)
    target = imported[0]['target']
    source = next(p['target'] for p in historical
                  if p['target'].split(':')[1] == target.split(':')[1])
    parent.consumer.profile(cur, imported[0]['root'])
    f = parent.fresh(cur, today, dict(x=x, target=target, source=source,
        imported=imported, subject=actor), observed)
    reader.purge(cur, f)
    return f


def prep_args(f, epoch=None):
    return dict(p_source_request=f['key'], p_access=epoch or f['pages']['access_epoch'])


def read_args(f, epoch=None):
    return dict(p_request=f['key'], p_target=f['target'], p_offset=0, p_limit=50,
                p_access=epoch or f['pages']['access_epoch'])


def save_args(f, revision='0', key=None, epoch=None):
    p = parent.payload(f, revision)
    if epoch is not None:
        p['access_epoch'] = epoch
    return dict(p_payload=p, p_request=key or str(uuid.uuid4()))


def calls(f, save=None, epoch=None):
    return [(name, prep_args(f, epoch)) for name in PREP.values()] + [
        (READ, read_args(f, epoch)), (SAVE, save or save_args(f, epoch=epoch))]


def http_call(user, name, args, observed):
    started = monotonic()
    answer = user.rpc(name, args)
    ms = round((monotonic() - started) * 1000, 3)
    observed.setdefault('HTTP_calls', []).append(dict(method=name, millis=ms,
        status=answer['status'], code=(answer['body'] or {}).get('code')))
    assert ms < 8000, ('ORDINARY_CHOICE_HTTP_OVER8S', name, ms)
    return answer


def status(answer, f, expected=None):
    assert answer['status'] == 200, answer
    value = answer['body']
    assert value['contract_version'] == 'cp7.frozen-choice-preparation.v1'
    assert value['source_request'] == f['key'] and value['run_id'] == f['done']['run_id']
    assert value['reference'] == f['pages']['reference'] and value['stage'] == 'FROZEN_INPUTS'
    assert value['unit_count'] == 1 and value['units_done'] == (1 if value['state'] == 'READY' else 0)
    assert value['choice_saved'] is False and value['production_go'] is False
    if expected is not None:
        assert value['state'] == expected, value
    return value


def refused(answer, code, message=None):
    assert answer['status'] != 200 and answer['body']['code'] == code, answer
    if message is not None:
        assert answer['body']['message'] == message, answer
    # Error replies must not include a successful protected snapshot/payload.
    assert not set(answer['body']) & {'reference', 'payload', 'result', 'source_request'}


def snapshot(cur):
    plan.b.api.admin(cur)
    counts = cur.execute('select (select count(*) from cp7_product_analog_choice.choices),'
                         '(select count(*) from cp7_product_analog_choice.commands)').fetchone()
    return dict(metadata=B.choice.metadata(cur), counts=counts, money=plan.monetary_state(cur))


def unchanged(cur, before):
    assert snapshot(cur) == before, 'CHOICE_TRANSPORT_UNEXPECTED_BUSINESS_EFFECT'


def one_work(cur, f):
    plan.b.api.admin(cur)
    assert cur.execute('select count(*) from cp7_frozen_choice_preparation.work '
        'where actor=%s and source_request=%s', (f['subject'], f['key'])).fetchone() == (1,)
    return B.work(cur, f)


def candidate(cur, f):
    # Entire old compiler result, not selected fields or a new lookalike oracle.
    return reader.call(cur, f, f['target'], {})


def observations(observed):
    return deepcopy(observed)
