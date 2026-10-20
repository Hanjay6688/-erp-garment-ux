"""Strict OW04 Native assembler; no connections, writes, commits, or installation.

The caller supplies an approval made ONLY after the isolated F05 predecessor's
raw probe.verify and p09.functions checks. capture_verified repeats the two
owning legacy verifiers BEFORE capturing. Approval is never derived here from
an unverified candidate. Returned SQL belongs in the caller's one transaction.

Legacy composition is deliberately disclosed: after independent exact live
target/metadata + immutable-baseline verification, ONLY the original legacy
helper-definition equality reads receive the approved predecessor definition.
All other legacy reads run unchanged against the actual database. This is not
raw legacy PASS and is not used by any Native/source collector. No monkeypatch.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError('OW04_TRANSFORM_UNAVAILABLE')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


admission = _load('ow04_assembler_admission', HERE.parent / 'admission/03_native_admission_transform.py')
ledger = _load('ow04_assembler_ledger', HERE.parent / 'ledger/03_native_copy_transform.py')
NATIVE = tuple(s[0] for s in admission.SPECS)
NOTE_NATIVE = (
    'erp.reverse_fg_movement(uuid,text)',
    'erp._cp3_r4_reverse_journal_internal(uuid,text)',
    'erp.reverse_journal(uuid,text)', 'erp.reverse_sale(uuid,text)',
    'erp.reverse_sales_return(uuid,text)', 'erp.reverse_sales_payment(uuid,text)',
)
RETURN_NATIVE = NOTE_NATIVE[:3] + ('erp.reverse_sales_return(uuid,text)',)
PRIVATE = tuple(s.replace('erp.', 'cp7_note.', 1) for s in NOTE_NATIVE) + tuple(
    s.replace('erp.', 'cp7_sales_return_correction.', 1) for s in RETURN_NATIVE)
POSTER = ledger.POST_JOURNAL_IDENTITY
REVERSE = ledger.REVERSE_JOURNAL_IDENTITY
BOUND = 'cp7_credit._post_journal_bound(text,uuid,date,text,jsonb)'
REQUIRED = NATIVE + PRIVATE + (POSTER, REVERSE)
TARGETS = NATIVE + PRIVATE + (BOUND, REVERSE)
LEGACY_FILES = ('scripts/cp7_note_correction_verify.py',
                'scripts/cp7_sales_return_correction_bundle.py')
FKEYS = {'identity', 'definition', 'body', 'owner', 'acl', 'security_definer', 'volatility', 'config'}
AKEYS = (FKEYS - {'definition', 'body'}) | {'definition_sha256', 'body_sha256'}
HEX = re.compile(r'[0-9a-f]{64}\Z')


def digest(value):
    return sha256(value.encode('utf-8')).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _closed(value, keys, error):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(error)


def _hash(value):
    if type(value) is not str or not HEX.fullmatch(value):
        raise ValueError('OW04_INVALID_SHA256')


def _metadata(row, approval=False):
    _closed(row, AKEYS if approval else FKEYS, 'OW04_FUNCTION_CAPTURE_FIELDS')
    if type(row['identity']) is not str:
        raise ValueError('OW04_FUNCTION_IDENTITY_TYPE')
    if row['owner'] != 'postgres' or type(row['security_definer']) is not bool:
        raise ValueError('OW04_FUNCTION_OWNER_OR_SECURITY')
    if row['volatility'] not in ('i', 's', 'v'):
        raise ValueError('OW04_FUNCTION_VOLATILITY')
    for key in ('acl', 'config'):
        val = row[key]
        if val is not None and (type(val) is not list or any(type(x) is not str for x in val)):
            raise ValueError('OW04_FUNCTION_METADATA_TYPE')
    if row['acl'] is not None and (row['acl'] != sorted(row['acl']) or len(set(row['acl'])) != len(row['acl'])):
        raise ValueError('OW04_FUNCTION_ACL_NOT_CANONICAL')
    if approval:
        _hash(row['definition_sha256']); _hash(row['body_sha256'])
    elif (type(row['definition']) is not str or type(row['body']) is not str
          or not row['body'] or row['definition'].count(row['body']) != 1):
        raise ValueError('OW04_CAPTURE_BODY_NOT_UNIQUE')


def _index(rows, identities, approved=False):
    if type(rows) is not list:
        raise ValueError('OW04_EXACT_FUNCTION_LIST_REQUIRED')
    found = {}
    for row in rows:
        _metadata(row, approved)
        identity = row['identity']
        if identity in found:
            raise ValueError('OW04_DUPLICATE_FUNCTION: ' + identity)
        found[identity] = row
    if set(found) != set(identities):
        raise ValueError('OW04_MISSING_OR_EXTRA_FUNCTION')
    return found


def _facts(value):
    _closed(value, ('cp7_note', 'cp7_sales_return_correction'), 'OW04_HELPER_BASELINE_SCHEMAS')
    for schema, required in (('cp7_note', NOTE_NATIVE), ('cp7_sales_return_correction', RETURN_NATIVE)):
        rows = value[schema]
        if type(rows) is not list:
            raise ValueError('OW04_HELPER_BASELINE_ROWS')
        found = {}
        for row in rows:
            _closed(row, ('native_signature', 'native_definition_sha256'), 'OW04_HELPER_BASELINE_FIELDS')
            key = row['native_signature']; _hash(row['native_definition_sha256'])
            if key in found:
                raise ValueError('OW04_DUPLICATE_HELPER_BASELINE')
            found[key] = row['native_definition_sha256']
        if set(found) != set(required):
            raise ValueError('OW04_HELPER_BASELINE_SET_CHANGED')
    return value


def _approval(manifest):
    _closed(manifest, ('contract_version', 'baseline_verification', 'functions', 'helper_sources',
                       'legacy_verifier_sources', 'absent_targets'), 'OW04_APPROVAL_FIELDS')
    if manifest['contract_version'] != 'ow04.native-approved.v1':
        raise ValueError('OW04_APPROVAL_VERSION')
    b = manifest['baseline_verification']
    _closed(b, ('phase', 'verifiers', 'receipt_sha256'), 'OW04_BASELINE_VERIFICATION_REQUIRED')
    if b['phase'] != 'VERIFIED_PREDECESSOR' or b['verifiers'] != ['probe.verify', 'p09.functions']:
        raise ValueError('OW04_UNVERIFIED_PREDECESSOR')
    _hash(b['receipt_sha256'])
    _closed(manifest['legacy_verifier_sources'], LEGACY_FILES, 'OW04_LEGACY_SOURCE_PINS_REQUIRED')
    for value in manifest['legacy_verifier_sources'].values(): _hash(value)
    if manifest['absent_targets'] != [BOUND]:
        raise ValueError('OW04_NEW_TARGET_ABSENCE_REQUIRED')
    _facts(manifest['helper_sources'])
    return _index(manifest['functions'], REQUIRED, True)


def _fingerprint(row):
    result = {key: deepcopy(row[key]) for key in FKEYS - {'definition', 'body'}}
    result.update(definition_sha256=digest(row['definition']), body_sha256=digest(row['body']))
    return result


def _validate(captures, manifest):
    approved = _approval(manifest)
    _closed(captures, ('contract_version', 'baseline_receipt', 'functions', 'helper_sources', 'absent_targets'),
            'OW04_CAPTURE_ENVELOPE')
    if captures['contract_version'] != 'ow04.native-captures.v1':
        raise ValueError('OW04_CAPTURE_VERSION')
    expected_receipt = {'phase': 'BEFORE_CAPTURE',
        'external_receipt_sha256': manifest['baseline_verification']['receipt_sha256'],
        'legacy_verifier_sources': manifest['legacy_verifier_sources']}
    if captures['baseline_receipt'] != expected_receipt:
        raise ValueError('OW04_BEFORE_CAPTURE_VERIFICATION_REQUIRED')
    actual = _index(captures['functions'], REQUIRED)
    if _facts(captures['helper_sources']) != manifest['helper_sources']:
        raise ValueError('OW04_IMMUTABLE_HELPER_BASELINE_CHANGED')
    if captures['absent_targets'] != [BOUND]:
        raise ValueError('OW04_BOUND_POSTER_ALREADY_EXISTS')
    for identity, row in actual.items():
        if _fingerprint(row) != approved[identity]:
            raise ValueError('OW04_PREDECESSOR_OR_METADATA_CHANGED: ' + identity)
    # The recorded private copier predecessor is immutable. Its original Native
    # digest must match captured Native where that Native is in this census.
    for rows in captures['helper_sources'].values():
        for fact in rows:
            if fact['native_signature'] in actual and fact['native_definition_sha256'] != digest(actual[fact['native_signature']]['definition']):
                raise ValueError('OW04_HELPER_BASELINE_NOT_CAPTURED_NATIVE')
    return actual


def _private_body(identity, body):
    schema, name = identity.split('.', 1)
    name = name.split('(', 1)[0]
    context = 'perform ' + schema + '.require_context();'
    if body.count(context) != 1:
        raise ValueError('OW04_PRIVATE_CONTEXT_NOT_EXACT')
    transforms = {'reverse_sale': admission.reverse_sale,
                  'reverse_sales_return': admission.reverse_return,
                  'reverse_sales_payment': admission.reverse_payment,
                  'reverse_journal': ledger.reverse_body}
    if name in transforms:
        changed = transforms[name](body)
    elif name == '_cp3_r4_reverse_journal_internal':
        # Protect the actual internal child too. Parent/source hooks retain all
        # original authority/FG/date/stock checks. No generic bypass is added.
        anchor = context
        guard = (anchor + '\n if cp7_credit.is_protected_journal(p_journal_entry_id)then'
                 " raise exception 'CP7_CREDIT_JOURNAL_USE_OWNING_SOURCE_WORKFLOW';end if;")
        changed = admission.once(body, anchor, guard)
    elif name == 'reverse_fg_movement':
        # This physical primitive stays exact; its actual semantic parents above
        # enter/complete the bound financial-source guard before any inversion.
        changed = body
    else:
        raise ValueError('OW04_UNKNOWN_PRIVATE_INVERSE')
    if changed.count(context) != 1:
        raise ValueError('OW04_PRIVATE_CONTEXT_CHANGED')
    return changed


def derive_plan(captures, trusted_approved_manifest):
    """Pure exact old/new plan. Does not approve its inputs or execute SQL."""
    actual = _validate(captures, trusted_approved_manifest)
    entries = []
    transforms = {spec[0]: spec[3] for spec in admission.SPECS}
    for identity in REQUIRED:
        old = actual[identity]
        target = BOUND if identity == POSTER else identity
        if identity in transforms:
            changed = transforms[identity](old['body'])
        elif identity in PRIVATE:
            changed = _private_body(identity, old['body'])
        elif identity == POSTER:
            changed = ledger.post_body(old['body'])
        elif identity == REVERSE:
            changed = ledger.reverse_body(old['body'])
        else:
            raise ValueError('OW04_UNDECLARED_TRANSFORM')
        new_definition = admission.once(old['definition'], old['body'], changed)
        if identity == POSTER:
            new_definition = admission.once(new_definition, 'FUNCTION erp.post_journal(',
                                             'FUNCTION cp7_credit._post_journal_bound(')
        new = deepcopy(old)
        new.update(identity=target, definition=new_definition, body=changed)
        if target == BOUND:
            new['acl'] = ['postgres=X/postgres']
        entries.append({'source_identity': identity, 'target_identity': target,
            'action': 'CREATE' if identity == POSTER else ('UNCHANGED' if new == old else 'REPLACE'),
            'old': deepcopy(old), 'new': new, 'old_sha256': digest(old['definition']),
            'new_sha256': digest(new_definition)})
    return {'contract_version': 'ow04.native-plan.v1',
            'approval_sha256': digest(canonical(trusted_approved_manifest)),
            'captures': deepcopy(captures), 'entries': entries,
            'immutable_helper_sources': deepcopy(captures['helper_sources']),
            'native_execution_proven': False}


def _checked_plan(plan, manifest):
    if type(plan) is not dict or 'captures' not in plan:
        raise ValueError('OW04_PLAN_REQUIRED')
    expected = derive_plan(plan['captures'], manifest)
    if plan != expected:
        raise ValueError('OW04_PLAN_MODIFIED_AFTER_DERIVATION')
    return plan


CAPTURE_QUERY = """select pg_get_functiondef(p.oid),p.prosrc,pg_get_userbyid(p.proowner),
 case when p.proacl is null then null else array(select a::text from unnest(p.proacl)a order by a::text collate "C")end,
 p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p where p.oid=to_regprocedure(%s)"""


def _capture(cur, identity):
    row = cur.execute(CAPTURE_QUERY, (identity,)).fetchone()
    if row is None:
        raise ValueError('OW04_LIVE_FUNCTION_MISSING: ' + identity)
    return dict(identity=identity, definition=row[0], body=row[1], owner=row[2],
                acl=None if row[3] is None else list(row[3]), security_definer=row[4],
                volatility=row[5], config=None if row[6] is None else list(row[6]))


def _helper_rows(cur):
    return {schema: [dict(native_signature=s, native_definition_sha256=h) for s, h in
        cur.execute('select native_signature,native_definition_sha256 from ' + schema + '.helper_sources order by native_signature collate "C"').fetchall()]
        for schema in ('cp7_note', 'cp7_sales_return_correction')}


def _legacy_modules(repo, manifest):
    _approval(manifest)
    paths = [Path(repo) / name for name in LEGACY_FILES]
    for name, path in zip(LEGACY_FILES, paths):
        if digest(path.read_text()) != manifest['legacy_verifier_sources'][name]:
            raise ValueError('OW04_LEGACY_VERIFIER_SOURCE_CHANGED: ' + name)
    def literal(path, variable):
        tree = ast.parse(path.read_text())
        nodes = [n.value for n in tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == variable for t in n.targets)]
        if len(nodes) != 1: raise ValueError('OW04_PRIVATE_INVENTORY_SOURCE_CHANGED')
        return tuple(ast.literal_eval(nodes[0]))
    if literal(paths[0], 'SIGNATURES') != NOTE_NATIVE or literal(paths[1], 'HELPERS') != tuple(s.split('.')[1].split('(')[0] for s in RETURN_NATIVE):
        raise ValueError('OW04_PRIVATE_INVENTORY_SOURCE_CHANGED')
    scripts = str(Path(repo).resolve() / 'scripts')
    old = list(sys.path)
    try:
        sys.path.insert(0, scripts)
        modules = tuple(_load('ow04_exact_legacy_' + str(i), p) for i, p in enumerate(paths))
        if Path(modules[0].bundle.ROOT).resolve() != Path(repo).resolve() or Path(modules[1].ROOT).resolve() != Path(repo).resolve():
            raise ValueError('OW04_LEGACY_DEPENDENCY_CHECKOUT_CHANGED')
        return modules
    finally:
        sys.path[:] = old


def capture_verified(cur, trusted_approved_manifest, repo):
    """Read-only; raw owning legacy checks precede every candidate capture."""
    _approval(trusted_approved_manifest)
    for module in _legacy_modules(repo, trusted_approved_manifest): module.verify(cur)
    absent = cur.execute('select to_regprocedure(%s)is null', (BOUND,)).fetchone()
    if absent != (True,): raise ValueError('OW04_BOUND_POSTER_ALREADY_EXISTS')
    captures = {'contract_version': 'ow04.native-captures.v1',
        'baseline_receipt': {'phase': 'BEFORE_CAPTURE',
            'external_receipt_sha256': trusted_approved_manifest['baseline_verification']['receipt_sha256'],
            'legacy_verifier_sources': deepcopy(trusted_approved_manifest['legacy_verifier_sources'])},
        'functions': [_capture(cur, s) for s in REQUIRED], 'helper_sources': _helper_rows(cur), 'absent_targets': [BOUND]}
    _validate(captures, trusted_approved_manifest)
    return captures


def verify_installed(cur, plan, trusted_approved_manifest):
    """Read-only exact definitions + pg_proc metadata; immutable facts unchanged."""
    plan = _checked_plan(plan, trusted_approved_manifest)
    for entry in plan['entries']:
        if _capture(cur, entry['target_identity']) != entry['new']:
            raise ValueError('OW04_INSTALLED_TARGET_CHANGED: ' + entry['target_identity'])
    # Creating the private poster never alters the accepted Native poster.
    original = next(e['old'] for e in plan['entries'] if e['source_identity'] == POSTER)
    if _capture(cur, POSTER) != original:
        raise ValueError('OW04_ORIGINAL_NATIVE_POSTER_CHANGED')
    if _helper_rows(cur) != plan['immutable_helper_sources']:
        raise ValueError('OW04_IMMUTABLE_HELPER_BASELINE_CHANGED')
    return {'contract_version': 'ow04.native-install-verification.v1',
            'plan_sha256': digest(canonical(plan)), 'functions_verified': 19,
            'original_poster_unchanged': True, 'immutable_helper_sources_unchanged': True}


DEFINITION_READ = 'select pg_get_functiondef(%s::regprocedure)'
LEGACY_IDENTITIES = frozenset(NOTE_NATIVE + PRIVATE)


class _ProjectedResult:
    def __init__(self, value): self.value = value
    def fetchone(self): return (self.value,)
    def fetchall(self): return [(self.value,)]


class _LegacyDefinitionView:
    """One exact parameterized SELECT only; everything else is actual SQL."""
    def __init__(self, cur, plan, manifest, proof):
        plan = _checked_plan(plan, manifest)
        plan_sha = digest(canonical(plan))
        if proof != {'contract_version': 'ow04.native-install-verification.v1',
                     'plan_sha256': plan_sha, 'functions_verified': 19,
                     'original_poster_unchanged': True, 'immutable_helper_sources_unchanged': True}:
            raise ValueError('OW04_LEGACY_VIEW_REQUIRES_EXACT_LIVE_PROOF')
        self.cur, self.reads = cur, []
        self.predecessor = {e['source_identity']: e['old']['definition'] for e in plan['entries']
                            if e['source_identity'] in LEGACY_IDENTITIES}
    def _project_definition(self, sql, params):
        if (sql != DEFINITION_READ or type(params) is not tuple or len(params) != 1
                or type(params[0]) is not str or params[0] not in LEGACY_IDENTITIES
                or params[0] not in self.predecessor):
            raise ValueError('OW04_LEGACY_PROJECTION_QUERY_OR_PARAMS_REFUSED')
        identity = params[0]
        self.reads.append(identity)
        return _ProjectedResult(self.predecessor[identity])
    def execute(self, sql, params=None):
        is_read = type(sql) is str and 'pg_get_functiondef' in sql.lower()
        managed_names = tuple(identity.split('(')[0] for identity in self.predecessor)
        managed_param = type(params) in (tuple, list) and any(type(p) is str and
            any(p == name or p.startswith(name + '(') for name in managed_names) for p in params)
        managed_literal = is_read and any(name in sql for name in managed_names)
        if is_read and (managed_param or managed_literal):
            return self._project_definition(sql, params)
        return self.cur.execute(sql, params) if params is not None else self.cur.execute(sql)


def verify_legacy_composed(cur, plan, trusted_approved_manifest, repo):
    plan = _checked_plan(plan, trusted_approved_manifest)
    proof = verify_installed(cur, plan, trusted_approved_manifest)
    first_failures, results, projected = [], [], []
    for i, module in enumerate(_legacy_modules(repo, trusted_approved_manifest)):
        try:
            module.verify(cur)
        except AssertionError as error:
            args = error.args
            valid = (len(args) == 1 and type(args[0]) is tuple and len(args[0]) == 2 and
                ((i == 0 and args[0][0] == 'NOTE_NATIVE_DEFINITION_CHANGED' and args[0][1] in (REVERSE, 'erp.reverse_sale(uuid,text)', 'erp.reverse_sales_return(uuid,text)', 'erp.reverse_sales_payment(uuid,text)'))
                 or (i == 1 and args[0][0] in (REVERSE, 'erp.reverse_sales_return(uuid,text)') and args[0][1] == 'Native original changed')
                 or (i == 1 and args[0][0] in (
                     'cp7_sales_return_correction._cp3_r4_reverse_journal_internal(uuid,text)',
                     'cp7_sales_return_correction.reverse_journal(uuid,text)',
                     'cp7_sales_return_correction.reverse_sales_return(uuid,text)')
                     and args[0][1] == 'Undeclared private Native delta')))
            if not valid: raise
            first_failures.append({'verifier': LEGACY_FILES[i], 'direct_legacy_assertion': repr(args)})
        else:
            raise ValueError('OW04_DIRECT_LEGACY_DELTA_WAS_NOT_OBSERVED')
        view = _LegacyDefinitionView(cur, plan, trusted_approved_manifest, proof)
        results.append(module.verify(view)); projected.append(view.reads)
    return {'classification': 'COMPOSED_LEGACY_VERIFICATION_NOT_RAW_LEGACY_PASS',
        'live_proof': proof, 'direct_legacy_first_failures': first_failures,
        'projected_definition_reads': projected, 'legacy_results': results,
        'immutable_baselines_rewritten': False}


def _q(value):
    # Explicit E-string retains JSON backslashes independently of the install
    # session's standard_conforming_strings setting.
    return "E'" + value.replace('\\', '\\\\').replace("'", "''") + "'"


def _guard_sql(rows, facts, absent=()):
    payload = canonical({'functions': rows, 'helper_sources': facts, 'absent_targets': list(absent)})
    return """do $ow04_exact_guard$
declare expected jsonb:=%s::jsonb;r jsonb;p pg_proc;actual_acl jsonb;actual_facts jsonb;s text;
begin
 for r in select value from jsonb_array_elements(expected->'functions')loop
  select *into strict p from pg_proc where oid=to_regprocedure(r->>'identity');
  select case when p.proacl is null then null else coalesce(jsonb_agg(a::text order by a::text collate "C"),'[]'::jsonb)end
   into actual_acl from unnest(p.proacl)a;
  if pg_get_functiondef(p.oid)is distinct from r->>'definition'or p.prosrc is distinct from r->>'body'
   or pg_get_userbyid(p.proowner)is distinct from r->>'owner'or actual_acl is distinct from nullif(r->'acl','null'::jsonb)
   or to_jsonb(p.prosecdef)is distinct from r->'security_definer'or p.provolatile::text is distinct from r->>'volatility'
   or to_jsonb(p.proconfig)is distinct from nullif(r->'config','null'::jsonb)then
   raise exception 'OW04_EXACT_FUNCTION_OR_METADATA_CHANGED: %%',r->>'identity';end if;
 end loop;
 foreach s in array array['cp7_note','cp7_sales_return_correction']loop
  execute format('select coalesce(jsonb_agg(jsonb_build_object(''native_signature'',native_signature,''native_definition_sha256'',native_definition_sha256)order by native_signature collate "C"),''[]'')from %%I.helper_sources',s)into actual_facts;
  if actual_facts is distinct from expected->'helper_sources'->s then raise exception 'OW04_IMMUTABLE_HELPER_BASELINE_CHANGED';end if;
 end loop;
 for s in select jsonb_array_elements_text(expected->'absent_targets')loop
  if to_regprocedure(s)is not null then raise exception 'OW04_NEW_TARGET_ALREADY_EXISTS: %%',s;end if;
 end loop;
end $ow04_exact_guard$;
""" % _q(payload)


def render_install_sql(plan, trusted_approved_manifest):
    """Emit guarded DDL; caller alone executes it, atomically, without commits."""
    plan = _checked_plan(plan, trusted_approved_manifest)
    out = [_guard_sql([e['old'] for e in plan['entries']], plan['immutable_helper_sources'], [BOUND])]
    for entry in plan['entries']:
        if entry['action'] != 'UNCHANGED': out.append(entry['new']['definition'].rstrip().rstrip(';') + ';\n')
        if entry['action'] == 'CREATE':
            out.append('alter function ' + BOUND + ' owner to postgres;\n')
            # Remove all inherited default ACLs, including roles outside the UI
            # role list; verify exact postgres-only ACL before transaction end.
            out.append("""do $ow04_new_acl$declare r record;begin
 for r in select distinct x.grantee from pg_proc p cross join lateral aclexplode(coalesce(p.proacl,acldefault('f',p.proowner)))x
  where p.oid='%s'::regprocedure and x.grantee<>'postgres'::regrole::oid loop
  execute 'revoke all on function %s from '||case when r.grantee=0 then'PUBLIC'else quote_ident(pg_get_userbyid(r.grantee))end;
 end loop;end $ow04_new_acl$;
grant execute on function %s to postgres;
""" % (BOUND, BOUND, BOUND))
    after = [e['new'] for e in plan['entries']] + [next(e['old'] for e in plan['entries'] if e['source_identity'] == POSTER)]
    out.append(_guard_sql(after, plan['immutable_helper_sources']))
    return '\n'.join(out)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captures', required=True, type=Path)
    parser.add_argument('--approval', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--sql-output', type=Path)
    args = parser.parse_args()
    approval = json.loads(args.approval.read_text())
    plan = derive_plan(json.loads(args.captures.read_text()), approval)
    args.output.write_text(json.dumps(plan, indent=2) + '\n')
    if args.sql_output: args.sql_output.write_text(render_install_sql(plan, approval))
    print(json.dumps({'classification': 'PURE_NATIVE_DERIVATION_NOT_NATIVE_EXECUTION',
                      'entries': len(plan['entries']), 'plan_sha256': digest(canonical(plan))}))
