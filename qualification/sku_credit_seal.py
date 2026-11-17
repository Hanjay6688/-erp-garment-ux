"""Extend the frozen credit trigger seal through the reviewed SKU chain."""

from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import ast
import json
import re


SOURCE = 'scripts/cp7_customer_credit'
REVIEW = Path(__file__).with_name('SKU_CREDIT_TRIGGER_DELTA.json')
REVIEW_SHA = '2bb262c395f85e81a34d7b644b7bb34be0b034d1836035079675456157f28262'
PINS = {
    'consumer/composition.py': '224a3435afc299b57ee9f8a2170131d0913224aa30c04338c2898a1f046dfe21',
    'consumer/02_operation_facts.sql': '832c79e3d46aeb12d8ddacd20b368864836f2675811ea369ff4c7e14177efee7',
    'integration/owning_bundle.py': '11de7b5d6af83999e3ca17b23662308b07e222f516e33133671a0fc978dffd1a',
    'integration/source_triggers/SOURCE_PINS.json': 'dbb177c5fc067d3173b23c6654dd8c0bc62610c3e8d9ce1b42876c6a7712d292',
    'integration/source_triggers/build_source_pins.py': 'dc39bacd8fd5beb2d40bb3acac8ced0ff4f29a34e1731981e52a0eb416bdf026',
    'integration/source_triggers/capture.sql': '0ec6af17788d09a3f30ffc2adffa2f6a8e46dae8d1879664669f91995fe91f38',
    'integration/source_triggers/trigger_guard.py': '7de2a8cc7761487d77e03bb77f4333f7a52ed61b9fa5ccc33ea3f52965661ab9',
}
ORIGINAL = 'OW04_CONSUMER_BOUNDED'
FINAL = 'CP7_SKU_CURRENT_MANDOR_MOVING_MONEY_AUTOMATIC'
SIGNATURE = 'cp7_credit.assert_source_native_trigger_census_v1()'
SEAL = re.compile(r"(?<=\n if actual_sha256 is distinct from ')[0-9a-f]{64}(?='then\n)")


def require(value, error):
    if not value:
        raise ValueError(error)


def exact(path, expected):
    require(path.is_file() and not any(parent.is_symlink() for parent in (path, *path.parents)),
            'SKU_CREDIT_EXACT_REGULAR_SOURCE_REQUIRED')
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == expected, 'SKU_CREDIT_EXACT_SOURCE_BYTES_REQUIRED')
    return raw


@contextmanager
def utc(cur):
    previous, = cur.execute("select current_setting('TimeZone')").fetchone()
    cur.execute("set local timezone='UTC'")
    try:
        yield
    finally:
        if cur.connection.info.transaction_status.name != 'INERROR':
            cur.execute("select set_config('TimeZone',%s,true)", (previous,))


def pinned_functions(path, raw, names, namespace):
    # The retained Consumer loader also imports its unrelated payment writer.
    # This adapter only needs its frozen manifest builder and capture helpers.
    nodes = [node for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef) and node.name in names]
    require({node.name for node in nodes} == names and len(nodes) == len(names),
            'SKU_CREDIT_EXACT_REUSED_FUNCTIONS_REQUIRED')
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
    return SimpleNamespace(**{name: namespace[name] for name in names})


def prepare(entry):
    from psycopg.pq import TransactionStatus

    source = entry.ROOT / SOURCE
    pins = {relative: exact(source / relative, digest) for relative, digest in PINS.items()}
    reviewed = json.loads(exact(REVIEW, REVIEW_SHA))
    require(reviewed['sku_original_run'] == 43347020525
            and reviewed['full25_sha256'] == 'ecf858d67f43c0967cfe6f38c51338dea64331ef6c0d1264786a8967f856e2a4'
            and reviewed['guard_reseal_executed'] is False and reviewed['production_go'] is False,
            'SKU_CREDIT_EXACT_A625_CATALOGUE_REVIEW_REQUIRED')
    guard = entry.load('global_sku_exact_credit_census_guard', source / 'integration/source_triggers/trigger_guard.py')
    builder = entry.load('global_sku_exact_credit_fk_builder', source / 'integration/source_triggers/build_source_pins.py')
    manifest_builder = pinned_functions(source / 'consumer/composition.py', pins['consumer/composition.py'],
                                        {'consumer_trigger_manifest'},
                                        dict(REPO=entry.ROOT, deepcopy=deepcopy, triggers=guard, trigger_builder=builder))
    owning = pinned_functions(source / 'integration/owning_bundle.py', pins['integration/owning_bundle.py'],
                              {'_postgres_reader', '_source_trigger_capture'},
                              dict(contextmanager=contextmanager, TransactionStatus=TransactionStatus))
    manifest = manifest_builder.consumer_trigger_manifest()
    require(len(manifest['tables']) == 6 and len(manifest['ordinary_triggers']) == 25
            and len(manifest['phases'][ORIGINAL]['functions']) == 18
            and len(manifest['phases'][ORIGINAL]['foreign_keys']) == 126,
            'SKU_CREDIT_EXACT_CONSUMER_BASELINE_REQUIRED')
    return Seal(SimpleNamespace(triggers=guard, owning=owning), manifest, reviewed)


def state(cur):
    return cur.execute('''select to_jsonb(p)-'prosrc',n.nspowner,n.nspacl::text,pg_get_functiondef(p.oid)
        from pg_proc p join pg_namespace n on n.oid=p.pronamespace where p.oid=%s::regprocedure''',
                       (SIGNATURE,)).fetchone()


def only_literal_changed(before, after):
    require(before is not None and after is not None and before[:-1] == after[:-1]
            and len(SEAL.findall(before[-1])) == len(SEAL.findall(after[-1])) == 1
            and SEAL.sub('0' * 64, before[-1]) == SEAL.sub('0' * 64, after[-1]),
            'SKU_CREDIT_SEAL_OID_ACL_OR_DEFINITION_CHANGED')


class Seal:
    def __init__(self, consumer, manifest, reviewed):
        self.guard = consumer.triggers
        self.owning = consumer.owning
        self.manifest = manifest
        self.reviewed = reviewed
        self.initial = None
        self.initial_guard = None

    def capture(self, cur):
        return self.owning._source_trigger_capture(cur, self.guard)

    def record_baseline(self, cur):
        require(self.initial is None, 'SKU_CREDIT_ONE_PRE_MANDOR_CAPTURE_REQUIRED')
        with utc(cur):
            with self.owning._postgres_reader(cur):
                cur.execute('select ' + SIGNATURE).fetchone()
            observed = self.capture(cur)
            proof = self.guard.validate_source(observed, self.manifest, ORIGINAL)
            require((proof['ordinary_attachments'], proof['ordinary_functions'], proof['internal_attachments'],
                     proof['foreign_keys']) == (25, 18, 264, 126), 'SKU_CREDIT_EXACT_INITIAL_ATTACHMENT_COUNTS_REQUIRED')
            self.initial = observed
            self.initial_guard = state(cur)
        print('GLOBAL_PARENT_CREDIT_PRE_MANDOR_CENSUS_VERIFIED ordinary=25 foreign_keys=126', flush=True)

    def extend_manifest(self, cur, observed):
        result = deepcopy(self.manifest)
        final = deepcopy(result['phases'][ORIGINAL])
        final['functions'] += self.reviewed['functions']
        final['foreign_keys'] += self.reviewed['foreign_keys']
        attachments = deepcopy(self.reviewed['ordinary_triggers'])
        for expected in attachments:
            constraint = expected['constraint']
            if constraint is None:
                continue
            # Only the one exact declared deferred trigger uses a runtime OID.
            rows = [row for row in observed['triggers'] if not row['internal']
                    and (row['relation'], row['name']) == (expected['relation'], expected['name'])]
            require(len(rows) == 1 and rows[0]['constraint'] is not None
                    and {key: value for key, value in rows[0]['constraint'].items() if key != 'oid'} == constraint,
                    'SKU_CREDIT_EXACT_DEFERRED_TRIGGER_CONSTRAINT_REQUIRED')
            identity = cur.execute('''select c.oid::text from pg_constraint c
                    join pg_trigger t on t.tgconstraint=c.oid
                    where c.conrelid=%s::regclass and t.tgrelid=c.conrelid
                      and c.conname=%s and t.tgname=%s and c.contype='t'
                      and c.condeferrable and c.condeferred and c.convalidated''',
                               (expected['relation'], constraint['name'], expected['name'])).fetchone()
            require(identity == (str(rows[0]['constraint']['oid']),), 'SKU_CREDIT_LIVE_DEFERRED_CONSTRAINT_ID_CHANGED')
            constraint['oid'] = rows[0]['constraint']['oid']
        result['ordinary_triggers'] += attachments
        result['phases'][FINAL] = final
        return result

    def verify_transition(self, cur, observed):
        require(self.initial is not None and state(cur) == self.initial_guard,
                'SKU_CREDIT_ORIGINAL_RUNTIME_SEAL_CHANGED_BEFORE_REVIEW')
        for group, key, delta in (('relations', 'relation', 0), ('functions', 'identity', 5),
                                  ('foreign_keys', 'oid', 11), ('triggers', 'trigger_oid', 29)):
            before = {row[key]: row for row in self.initial[group]}
            after = {row[key]: row for row in observed[group]}
            require(len(before) == len(self.initial[group]) and len(after) == len(observed[group])
                    and len(after) == len(before) + delta
                    and all(after.get(identity) == row for identity, row in before.items()),
                    'SKU_CREDIT_PREEXISTING_RAW_OBJECT_CHANGED:' + group)
        manifest = self.extend_manifest(cur, observed)
        proof = self.guard.validate_source(observed, manifest, FINAL)
        require((proof['ordinary_attachments'], proof['ordinary_functions'], proof['internal_attachments'],
                 proof['foreign_keys']) == (32, 23, 286, 137), 'SKU_CREDIT_EXACT_FINAL_ATTACHMENT_COUNTS_REQUIRED')
        for function in self.reviewed['functions']:
            acl, = cur.execute('''select jsonb_agg(jsonb_build_array(pg_get_userbyid(a.grantee),
                    pg_get_userbyid(a.grantor),a.privilege_type,a.is_grantable) order by a.grantee,a.grantor)
                from pg_proc p cross join lateral aclexplode(p.proacl) a
                where p.oid=%s::regprocedure''', (function['identity'],)).fetchone()
            require(acl == function['exact_acl'], 'SKU_CREDIT_EXACT_EXPLICIT_TRIGGER_EXECUTE_ACL_REQUIRED')
        return manifest

    def install_final(self, cur):
        require(not cur.connection.autocommit, 'SKU_CREDIT_OWNING_TRANSACTION_REQUIRED')
        with cur.connection.transaction(), utc(cur):
            observed = self.capture(cur)
            manifest = self.verify_transition(cur, observed)
            with self.owning._postgres_reader(cur):
                digest, = cur.execute('select cp7_credit.pg_jsonb_sha256(%s::jsonb)',
                                      (self.guard.canonical(observed),)).fetchone()
                ddl = self.guard.render_runtime_guard(observed, manifest, FINAL, digest)
                cur.execute(ddl, prepare=False)
                cur.execute('select ' + SIGNATURE).fetchone()
            only_literal_changed(self.initial_guard, state(cur))
            require(self.capture(cur) == observed, 'SKU_CREDIT_RESEAL_CHANGED_RAW_CENSUS')
        print('GLOBAL_PARENT_CREDIT_FINAL_CENSUS_VERIFIED ordinary=32 foreign_keys=137 raw_preserved=true', flush=True)

    def verify_copy(self, cur):
        self.verify_live(cur)
        print('GLOBAL_PARENT_CREDIT_BROWSER_COPY_CENSUS_VERIFIED', flush=True)

    def verify_live(self, cur):
        with self.owning._postgres_reader(cur):
            cur.execute('select ' + SIGNATURE).fetchone()
