"""Writer-only source checkpoint. Never invoked by a qualification runtime."""
from pathlib import Path
from hashlib import sha256
import ast
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = '568e57d5bdd1452ed7d62392879f6d5b738dfadd'
NS = 'scripts/current-credit-d1-product-cap-qualification'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def bind():
    names = ['scripts/cp7_credit_correction_de/' + f for f in (
        'review.sql','facts.sql','owning.sql','proof.sql','posting.sql','materialize.sql','closure.sql','native_delta.py','composition.py')]
    old = {p: sha256(git('show', BASE + ':' + p)).hexdigest() for p in names}
    for p in names:
        if not p.endswith('/owning.sql'):
            assert sha256((ROOT / p).read_bytes()).hexdigest() == old[p], p
    assert sha256((HERE / 'retained/owning.before.sql').read_bytes()).hexdigest() == old['scripts/cp7_credit_correction_de/owning.sql']
    frozen = git('ls-tree','-r','--name-only',BASE,'scripts/current-credit-de-native-qualification').decode().splitlines()
    frozen += [p for p in git('ls-tree','-r','--name-only',BASE,'.github/workflows').decode().splitlines() if 'credit-de-native' in p]
    frozen_pins = {}
    for p in frozen:
        original = git('show', BASE + ':' + p)
        assert (ROOT / p).read_bytes() == original, p
        frozen_pins[p] = sha256(original).hexdigest()
    callbacks = 'scripts/cp7_credit_correction_de/cases.py'
    original = git('show', BASE + ':' + callbacks)
    assert (ROOT / callbacks).read_bytes() == original
    nodes = ast.parse(original).body
    ids = next(ast.literal_eval(n.value) for n in nodes if isinstance(n,ast.Assign)
               and any(isinstance(t,ast.Name)and t.id=='IDS' for t in n.targets))
    parent = dict(local_base_head=BASE, base_tree='6f931e639bd8996378ff65b8a7be2a1ed8590b45',
        business_leaves=old, frozen_qualifier_files=frozen_pins,
        frozen_callback_sha256=sha256(original).hexdigest(), original_Native13_ids=list(ids))
    (HERE / 'PARENT.json').write_text(json.dumps(parent,indent=2)+'\n')
    paths = set(names + [callbacks, 'scripts/cp7_credit_correction_de/local_compile_fixture.py', 'scripts/cp7_credit_correction_de/local_cap_check.mjs'])
    paths.update(str(p.relative_to(ROOT)) for p in (ROOT / 'scripts/cp7_customer_credit/consumer').glob('*.sql'))
    paths.update('scripts/cp7_customer_credit/'+p for p in (
        'kernel/kernel.sql','ordinal-wrapper/wrapper.sql','ledger/01_immutable_facts.proposal.sql',
        'coordinator/01_coordinator_facts.sql','coordinator/05_factual_profile.sql','reconciliation/03_source_requests.sql'))
    paths.update(frozen)
    paths.update(str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p.name!='SOURCE.json'
                 and '__pycache__' not in p.parts and p.suffix!='.pyc')
    files = {}
    for path in sorted(paths):
        raw=(ROOT/path).read_bytes();files[path]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
    value=dict(status='PREPARED_QUOTE_PRODUCT_CAP_LOCAL_SQL_ONLY', base_tree=parent['base_tree'],
        files=files, product_changes=['cp7_credit_correction_de.quote_v1(jsonb)'],
        other_owning_bodies_unchanged=13,other_business_leaves_unchanged=8,
        all_original_Native13_callback_assertions_unchanged=True,
        Native_financial_execution=False, actual_Native_cases=0,production_go=False,independent_acceptance=False)
    (HERE/'SOURCE.json').write_text(json.dumps(value,indent=2)+'\n')
    return dict(status=value['status'],files=len(files),frozen_qualifier_files=len(frozen))


if __name__=='__main__':
    assert sys.argv[1:]==['--writer-freeze'], 'D1_PRODUCT_CAP_BINDER_IS_NOT_RUNTIME'
    print(json.dumps(bind()))
