"""Observe the first Global installer before a profile can be admitted."""

from argparse import ArgumentParser
from contextlib import contextmanager, nullcontext
from datetime import date
from gzip import decompress
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from types import FunctionType

from realtime_comparator import prepare as prepare_catalogue_check
from snapshot_prerequisites import ROUTES
from sku_inputs import HEAD, TREE


INPUTS = Path(__file__).resolve().parent / 'global-preseal'
BASE_COMBINED = '2cc9c8f178e443450989dbabe5e8ec53bd7542da'
COMBINED = '3a338b69cc13d44f7c881c62ecf77f5a762a7df7'
COMBINED_SRC = 'ada4544ebf22d9352461beb4b234f9a2f3e0ee29'
ENTRY = 'scripts/current-global-first-snapshot-preparation/install_routes.py'
FENCE = 'scripts/current-sku-managed-recovery-native27-qualification/source_context.py'
COMPARATOR = 'scripts/current-global-sku-automatic-preparation/parent_catalogue.py'
COMPARATOR_SHA = '44d6c946a6a3b9364ff4bd71e434fd8d0bf0d07787649d207a88bed021400ba3'
ROOT_PIN = dict(bytes=23897, sha256='ef5bbb964536502c25d4cf99774447006f4f015833818fae5c14e3cf8be5932a')
CATALOGUE_PIN = dict(bytes=16051957, sha256='ecf858d67f43c0967cfe6f38c51338dea64331ef6c0d1264786a8967f856e2a4')
PLAN = dict(bytes=15667, sha256='71f15d39d45696c40d683f1cd27a03ac4c53a8da960a060839b24bd81996a319')
DERIVED = dict(bytes=25009, sha256='28fac1b4177b2b3520c9b258bb458c760c204a75ab17ae231fb086fde94bcccc')
PATCH_SHA = '25930a5519c806ec439dda4c06fe5cab869896d6b78dbb461a47cd0c6b369489'
OID_SUCCESSOR_SHA = 'a8539d68a5385f900c325dd485b13438ac2522505bf5ec0305a06fa787e36914'
RELATIONS_SHA = '8a08df4cb3a8c0f29731ec644be0748b4200e24998b5a36138ca0140098ac841'
OBSERVATIONS_SHA = '79f87b618e0a9ef62f8fc9aefdf9be754542a4d3682d1f9b6356a9c193ded679'
GATES = ('PARENT_HEAD', 'PARENT_TREE', 'PARENT_ROOT_RECEIPT', 'PARENT_RUN', 'PARENT_JOB',
         'PARENT_ROOT_CONTRACT', 'INPUT_PROFILE_PIN', 'RUNTIME_ENTRY')
HISTORICAL = (
    ('fea75841e26645f1892d880905231625b47e3065', '13c9608a14cf5d137feb84c8bac99954c0c7af50'),
    ('ae480ca43d750a6abe41681fc6f90e6ad81a9135', '84b82de57207948d3e747432d387ce038de55204'),
    ('9b1b0fcc9fbf477634619f07d4628d5be3a1b634', '14de92a9d9c321cad0a513de28c164b4ba12de77'),
)
IMPORTS = {'cp7_global_nonpo_envelope', 'cp7_mandor_shop', 'cp7_accessory_nonpayable',
           'note_overlay', 'operator_ui', 'po_routes', 'preseal_routes', 'preuse_data',
           'snapshot_ownership', 'snapshot_stage', 'timezone_overlay'}
INVERSE_FLAGS = dict(full25_and_Native_raw_authority_restored=True,
                     timezone_and_nota_original_full19_restored=True,
                     snapshot_full25_inverse_restored=True,
                     all_preuse_rows_and_sequences_restored=True,
                     used_rows_removed=False, cascade_or_DROP_OWNED_used=False)


class ScopeRefused(ValueError):
    """An incomplete relation observation with the exact unused inverse restored."""

    def __init__(self, report):
        super().__init__('GLOBAL_PRESEAL_LIVE_RELATION_SCOPE_REFUSED')
        self.report = report


def require(value, error):
    if not value:
        raise ValueError(error)


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def exact(path, digest):
    require(path.is_file() and not any(parent.is_symlink() for parent in (path, *path.parents)),
            'GLOBAL_PRESEAL_REGULAR_SOURCE_REQUIRED')
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == digest, 'GLOBAL_PRESEAL_SOURCE_DIGEST_CHANGED:' + path.name)
    return raw


def load(name, path):
    spec = spec_from_file_location(name, path)
    result = module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def git(root, *args, input=None):
    return subprocess.check_output(('git', '-C', str(root), *args), input=input, stderr=subprocess.PIPE,
                                   env=dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_NO_REPLACE_OBJECTS='1')).decode().strip()


def verify_candidate(candidate):
    require((git(candidate, 'rev-parse', 'HEAD'), git(candidate, 'rev-parse', 'HEAD^{tree}')) == (HEAD, TREE)
            and git(candidate, 'write-tree') == COMBINED and git(candidate, 'write-tree', '--prefix=src/') == COMBINED_SRC
            and not git(candidate, 'diff', '--name-only') and not git(candidate, 'ls-files', '--others', '--exclude-standard'),
            'GLOBAL_PRESEAL_EXACT_COMBINED_SOURCE_REQUIRED')


def materialize(auditor, candidate, patch):
    """Apply both exact private deltas in a distinct worktree."""
    require(candidate != auditor and not candidate.exists() and git(auditor, 'rev-parse', 'HEAD') == HEAD
            and not git(auditor, 'status', '--porcelain', '--untracked-files=no'),
            'GLOBAL_PRESEAL_EXACT_SEPARATE_A625_CHECKOUT_REQUIRED')
    base = decompress(exact(patch, PATCH_SHA))
    successor = exact(INPUTS / 'global-oid-successor.patch', OID_SUCCESSOR_SHA)
    git(auditor, 'worktree', 'add', '--detach', '--no-checkout', str(candidate), HEAD)
    git(candidate, 'sparse-checkout', 'set', 'scripts', 'src')
    git(candidate, 'reset', '--hard', HEAD)
    git(candidate, 'apply', '--index', '--check', '-', input=base)
    git(candidate, 'apply', '--index', '-', input=base)
    require(git(candidate, 'write-tree') == BASE_COMBINED, 'GLOBAL_PRESEAL_EXACT_COMBINED_BASE_REQUIRED')
    git(candidate, 'apply', '--index', '--check', '-', input=successor)
    git(candidate, 'apply', '--index', '-', input=successor)
    verify_candidate(candidate)


@contextmanager
def candidate_imports(candidate):
    """Resolve the provider and its bare imports in its own exact checkout."""
    def selected(name):
        return name.split('.', 1)[0] in IMPORTS

    previous = {name: sys.modules.pop(name) for name in tuple(sys.modules) if selected(name)}
    search = sys.path[:]
    sys.path[0:0] = [str((candidate / ENTRY).parent), str(candidate / 'scripts')]
    try:
        yield
    finally:
        for name in tuple(sys.modules):
            if selected(name):
                del sys.modules[name]
        sys.modules.update(previous)
        sys.path[:] = search


def closed(provider):
    require(all(getattr(provider.admission, gate) is None for gate in GATES),
            'GLOBAL_PRESEAL_ALL_EIGHT_ADMISSION_GATES_MUST_REMAIN_CLOSED')


def preseal_functions(loader, provider, source):
    """Use the pinned installer statements through the final authority read."""
    require(pin(source.encode()) == DERIVED, 'GLOBAL_PRESEAL_EXACT_DERIVED_PROVIDER_REQUIRED')
    forward_name = '\ndef install(cur,parent_receipt_raw,input_profile_raw):\n'
    forward_start = '    _money_input_relations(inputs)\n'
    forward_end = '        wrapper=dict(contract='
    inverse_start = '        _timezone_require_preuse(cur,state)\n'
    require(all(source.count(mark) == 1 for mark in (forward_name, forward_start, forward_end, inverse_start)),
            'GLOBAL_PRESEAL_EXACT_DDL_BOUNDARIES_REQUIRED')
    retained = source.split(forward_name, 1)[1].split(forward_start, 1)[1].split(forward_end, 1)[0]
    # The diagnostic starts at the retained pre-DDL validations. It ends before
    # profile construction, INSERT, application barrier, and business work.
    forward = ('def run_preseal(cur, parent_receipt_raw, inputs, parent):\n'
               '    source=sources()\n' + forward_start + retained +
               '        return dict(before=before, after=after, fp=fp, catalogs=catalogs, relations=relations,\n'
               '            parent_catalogue_proof=parent_catalogue_proof,\n'
               '            authority_sha=authority_sha, timezone_identity=timezone_identity, note_identity=note_identity,\n'
               '            snapshot_before_pin=_snapshot_catalogue_pin(snapshot_before), snapshot_identity=snapshot_identity,\n'
               '            originals={n:r[0] for n,r in originals.items()}, definitions=definitions, native_identity=identity,\n'
               '            plan=plan)\n')
    inverse = ('def undo_preseal(cur, state):\n'
               '    from psycopg import sql\n'
               '    with atomic(cur),metadata_context(cur):\n'
               '        trusted_installer(cur)\n' + inverse_start + source.split(inverse_start, 1)[1])
    namespace = dict(vars(provider))
    exec(compile(forward + '\n' + inverse, str(loader.__file__) + '::closed_preseal', 'exec'), namespace)
    return namespace['run_preseal'], namespace['undo_preseal']


def observation_tools():
    """Use the reviewed six observations with the proposed, unsealed relations."""
    from global_scope import SECTIONS, errors, read_queries, ROLES, DECIMAL, PGCRYPTO

    raw = exact(INPUTS / 'closure_observations.sql', OBSERVATIONS_SHA)
    sql = '\n'.join(line for line in raw.decode().splitlines() if not line.lstrip().startswith('--'))
    queries = dict(zip(SECTIONS, (query.strip() for query in sql.split(';') if query.strip()), strict=True))
    routines = sorted(set(ROUTES) | {DECIMAL} | set(PGCRYPTO))

    def observe(cur, names):
        result = read_queries(cur, queries, dict(relations=names, roles=list(ROLES), routines=routines))
        return result, errors(result, names)

    return observe


@contextmanager
def prepare(candidate, catalogue, fingerprint, output, *, relation_names=None, installed_parent=None):
    """Review the exact inputs and provide one diagnostic on the live SKU cursor."""
    verify_candidate(candidate)
    for commit, tree in HISTORICAL:
        require(git(candidate, 'rev-parse', commit + '^{tree}') == tree,
                'GLOBAL_PRESEAL_HISTORICAL_SOURCE_REQUIRED:' + commit[:8])
    raw = exact(INPUTS / 'SKU_A625_VERIFIED_ROOT.json', ROOT_PIN['sha256'])
    root = json.loads(raw)
    require(pin(raw) == ROOT_PIN and pin(catalogue) == CATALOGUE_PIN
            and root['head'] == HEAD and root['tree'] == TREE and (root['run_id'], root['job_id']) == (43347020525, 131628716944)
            and root['global_parent_catalogue']['fingerprint'] == fingerprint,
            'GLOBAL_PRESEAL_EXACT_RETAINED_SKU_ROOT_AND_CATALOGUE_REQUIRED')
    reviewed = json.loads(exact(INPUTS / 'relation_candidates.json', RELATIONS_SHA))
    names = reviewed['relations']
    require(reviewed['parent_root'] == ROOT_PIN and reviewed['complete_input_review'] is False
            and len(names) == 438 and names == sorted(set(names)), 'GLOBAL_PRESEAL_EXACT_STATIC_RELATION_REVIEW_REQUIRED')
    if relation_names is not None:
        require(installed_parent is not None and type(relation_names) is list
                and relation_names == sorted(set(relation_names)) and set(names) < set(relation_names),
                'GLOBAL_PRESEAL_EXACT_ADDITIVE_RELATION_REVIEW_REQUIRED')
        names = relation_names
    else:
        require(installed_parent is None, 'GLOBAL_PRESEAL_DATED_PARENT_SCOPE_REQUIRED')
    read_scope = observation_tools()
    parent = {key: root[key] for key in ('head', 'tree', 'run_id', 'job_id')}
    parent['root_receipt_pin'] = ROOT_PIN
    with candidate_imports(candidate):
        fence = load('cp7_global_preseal_source_fence', candidate / FENCE)
        with fence.fenced_source_read():
            loader = load('cp7_global_preseal_closed_loader', candidate / ENTRY)
            recorded = []

            def record_compile(source, filename, mode, *args, **kwargs):
                if filename.endswith('::prepared_first_global_snapshots'):
                    recorded.append(source)
                return compile(source, filename, mode, *args, **kwargs)

            provider, proof = FunctionType(loader.load_prepared.__code__,
                dict(loader.load_prepared.__globals__, compile=record_compile))()
            closed(provider)
            require(proof['gates'] == list(GATES) and proof['runtime_admission'] is False
                    and provider.sources()['plan'] == PLAN, 'GLOBAL_PRESEAL_EXACT_CLOSED_PLAN_REQUIRED')
            source, = recorded
            exact(candidate / COMPARATOR, COMPARATOR_SHA)
            comparator = load('cp7_global_preseal_parent_comparator', candidate / COMPARATOR)
            compare = prepare_catalogue_check(comparator, catalogue, CATALOGUE_PIN, archived_startup_day=date(2026, 11, 13))
            inputs = dict(installation_plan=PLAN, relations=names, complete_input_review=False,
                          parent_catalogue_fingerprint=fingerprint,
                          parent_catalogue_equivalence=comparator.reviewed_fields(catalogue, CATALOGUE_PIN),
                          **loader.review_parent(raw, catalogue, verified_root_pin=ROOT_PIN,
                                                 catalogue_groups=loader.snapshot.CATALOGUE_GROUPS))
            provider._money_input_relations(inputs)
            forward, inverse = preseal_functions(loader, provider, source)
        print('GLOBAL_PARENT_GLOBAL_PRESEAL_SOURCE_VERIFIED tree=' + COMBINED + ' gates_open=0', flush=True)

        observed = False

        def observe(cur):
            nonlocal observed
            require(not observed, 'GLOBAL_PRESEAL_ONE_OBSERVATION_REQUIRED')
            connection = cur.connection
            info = connection.info
            require(not connection.autocommit and info.transaction_status.name == 'INTRANS'
                    and (info.host, info.port, info.dbname, info.user)
                    == ('127.0.0.1', 54322, 'cp6_rollback', 'cp6_maintenance_admission')
                    and cur.execute('show server_version_num').fetchone() == ('170006',),
                    'GLOBAL_PRESEAL_EXACT_DISPOSABLE_OWNING_TRANSACTION_REQUIRED')
            closed(provider)
            observed = True
            before = provider.capture(cur)
            scope = nullcontext(compare) if installed_parent is None else installed_parent(cur, provider, compare, inputs)
            refused = None
            with cur.connection.transaction(force_rollback=True):
                with scope as bound:
                    forward.__globals__['_automatic_parent_catalogue'] = bound
                    try:
                        result = run_observation(cur, provider, forward, inverse, raw, inputs, parent, read_scope, output)
                    except ScopeRefused as error:
                        # Allow an additive parent to prove its own unused inverse
                        # before raising the reviewed scope refusal to the caller.
                        refused = error
                require(provider.capture(cur) == before, 'GLOBAL_PRESEAL_PARENT_NOT_RESTORED_BEFORE_SAVEPOINT_ROLLBACK')
            if installed_parent is not None:
                print('GLOBAL_PARENT_DATED_LAUNDRY_PREUSE_INVERSE_VERIFIED', flush=True)
            if refused is not None:
                raise refused
            return result

        yield observe


def report_issue(phase, error):
    if not phase:
        phase = 'START'
    code = getattr(error, 'sqlstate', None)
    # Public SQL may carry values in DETAIL. Print only the known diagnostic
    # code and structured catalogue identifiers reported by PostgreSQL.
    message = next(iter(str(error).splitlines()), '')
    label = re.match(r'^(?:GLOBAL_|SNAPSHOT_|CP7_GLOBAL_)[A-Z0-9_]{5,100}', message)
    relation = re.fullmatch(r'(?:GLOBAL_REVIEWED_PHYSICAL_RELATION_REQUIRED|GLOBAL_NATIVE_WORK_COLUMN_PROFILE_CHANGED):'
                            r'([a-z0-9_.:]{3,130})', message)
    identities = [getattr(getattr(error, 'diag', None), key, None)
                  for key in ('schema_name', 'table_name', 'constraint_name', 'column_name')]
    names = [name for name in identities if name and re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}', name)]
    if relation:
        names.append(relation[1])
    print('GLOBAL_PARENT_GLOBAL_PRESEAL_REFUSED phase=' + phase, type(error).__name__,
          code or '', label[0] if label else '', *names, flush=True)
    return dict(phase=phase, error_type=type(error).__name__, sqlstate=code,
                label=label[0] if label else None, catalogue_names=names)


def public_summary(report):
    """Return the job receipt without raw observations or fixture values."""
    exact_fields = ('status', 'phase', 'combined_tree', 'sku_root', 'installation_plan',
                    'catalogue_fence_relations', 'sealed_profile_rows', 'outside_origin_RI_count',
                    'scope_refused_before_inverse', 'preseal_savepoint_restored',
                    'owning_transaction_still_open', 'complete_input_review', 'runtime_admission',
                    'actual_global_cases', 'production_go')
    value = {name: report[name] for name in exact_fields if name in report}
    if 'full25' in report:
        value['full25'] = {key: report['full25'][key] for key in ('groups', 'sha256')}
    dated = report.get('verified_parent_catalogue', {}).get('dated_laundry')
    if dated is not None:
        value['dated_laundry'] = dict(replaced=len(dated['exact_replaced_functions']),
                                      private_helpers=len(dated['exact_private_helpers']),
                                      same_connection_raw_authority_verified=dated['same_connection_raw_authority_verified'])
    if 'observed' in report:
        value['observed_relations'] = len(report['observed']['relations'])
        value['missing_relation_OID_count'] = len(report['missing_relation_OIDs'])
    if 'issues' in report:
        value['scope_issue_count'] = len(report['issues'])
        value['scope_issue_labels'] = sorted({issue.partition(':')[0] for issue in report['issues']})[:16]
    if 'inverse' in report:
        value['inverse'] = {key: report['inverse'][key] for key in INVERSE_FLAGS if key in report['inverse']}
    if 'failure' in report:
        value['failure'] = {key: report['failure'][key] for key in ('phase', 'error_type', 'sqlstate', 'label')}
    for name in ('replaced', 'private_additions', 'tables'):
        if name in report:
            value[name + '_count'] = len(report[name])
    return value


def run_observation(cur, provider, forward, inverse, root, inputs, parent, read_scope, output):
    report = dict(status='INCOMPLETE', combined_tree=COMBINED, sku_root=ROOT_PIN, installation_plan=PLAN,
                  complete_input_review=False, runtime_admission=False, actual_global_cases=0, production_go=False)
    with (output / 'GLOBAL_PRESEAL_OBSERVATION.json').open('x') as record:
        try:
            with cur.connection.transaction(force_rollback=True):
                report['phase'] = 'LIVE_PARENT_CENSUS'
                original_data = provider._timezone_snapshot(cur, lock=False)
                report['phase'] = 'GLOBAL_DDL_AND_AUTHORITY'
                state = forward(cur, root, inputs, parent)
                # Protect against unexpected data/sequence changes during forward
                # DDL. The new tables each have the exact digest of an empty set.
                empty = [0, sha256(b'[]').hexdigest()]
                state['preuse_data_and_sequences'] = original_data | dict.fromkeys(state['plan']['tables'], empty)
                provider.verify_objects(cur, state['after'], state['plan'])
                require(provider.native_identity(cur, state['definitions']) == state['native_identity']
                        and provider._timezone_identity(cur) == state['timezone_identity']
                        and provider.native_identity(cur, state['note_identity']) == state['note_identity'],
                        'GLOBAL_PRESEAL_EXISTING_FUNCTION_OID_OR_RAW_ACL_CHANGED')
                old, new = (dict(state[name]['functions']) for name in ('before', 'after'))
                replaced = sorted(name for name in old if old[name] != new.get(name))
                added = sorted(set(new) - set(old))
                require((len(replaced), len(added), len(state['plan']['tables'])) == (22, 19, 3),
                        'GLOBAL_PRESEAL_EXACT_COMBINED_FOOTPRINT_REQUIRED')
                sealed, = cur.execute('select count(*) from cp7_global_nonpo_envelope.profiles').fetchone()
                require(sealed == 0, 'GLOBAL_PRESEAL_EXPECTED_EMPTY_PROFILE_TABLE')
                report.update(full25=state['fp'], catalogue_fence_relations=len(state['catalogs']),
                              verified_parent_catalogue=state['parent_catalogue_proof'],
                              replaced=replaced, private_additions=added, tables=sorted(state['plan']['tables']),
                              native_authority_sha256=state['authority_sha'], sealed_profile_rows=sealed)
                report['phase'] = 'LIVE_RELATION_SCOPE'
                observed, issues = read_scope(cur, inputs['relations'])
                missing = sorted(row['qualified_name'] for row in observed['relations'] if row['relation_oid'] is None)
                outside = observed['outside_origin_RI']
                report.update(observed=observed, issues=issues, missing_relation_OIDs=missing,
                              outside_origin_RI_count=len(outside))
                if issues or outside:
                    print('GLOBAL_PARENT_GLOBAL_PRESEAL_SCOPE_OUTSIDE observed=' + str(len(observed['relations'])),
                          'issues=' + str(len(issues)), 'missing=' + str(len(missing)), 'outside_RI=' + str(len(outside)),
                          *missing[:8], *(f"{row['parent']}->{row['child']}" for row in outside[:8]), flush=True)
                    report['scope_refused_before_inverse'] = True
                report['phase'] = 'ORIGINAL_DDL_INVERSE'
                report['inverse'] = inverse(cur, state)
                require(all(report['inverse'].get(key) is value for key, value in INVERSE_FLAGS.items())
                        and provider.capture(cur) == state['before'], 'GLOBAL_PRESEAL_INVERSE_DID_NOT_RESTORE_LIVE_SKU')
                print('GLOBAL_PARENT_GLOBAL_PRESEAL_INVERSE_VERIFIED groups=25 rows=true sequences=true', flush=True)
            closed(provider)
            require(cur.connection.info.transaction_status.name == 'INTRANS'
                    and provider.capture(cur) == state['before'], 'GLOBAL_PRESEAL_SAVEPOINT_DID_NOT_RESTORE_LIVE_SKU')
            report['preseal_savepoint_restored'] = True
            if issues or outside:
                report['phase'] = 'LIVE_RELATION_SCOPE'
                raise ScopeRefused(report)
            report.update(status='GLOBAL_LIVE_PRESEAL_AND_INVERSE_VERIFIED', phase='RESTORED')
        except Exception as error:
            report.update(status='REFUSED', failure=report_issue(report.get('phase'), error),
                          owning_transaction_still_open=cur.connection.info.transaction_status.name == 'INTRANS')
            raise
        finally:
            json.dump(report, record, indent=2)
            record.write('\n')
            with (output / 'GLOBAL_PRESEAL_PUBLIC.json').open('x') as public:
                json.dump(public_summary(report), public, indent=2)
                public.write('\n')
    print('GLOBAL_PARENT_GLOBAL_PRESEAL_VERIFIED groups=25 existing=22 private=19 tables=3 '
          f'observed_relations={len(inputs["relations"])} sealed_profiles=0 actual_global_cases=0 inverse=true', flush=True)
    return report


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('auditor', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('patch', type=Path)
    args = parser.parse_args()
    materialize(args.auditor.resolve(), args.candidate.resolve(), args.patch.resolve())
