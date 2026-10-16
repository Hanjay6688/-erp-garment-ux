"""Assemble immutable log observations; never change a raw result into PASS."""
import collections
import datetime
import gzip
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tarfile

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[1]
E = pathlib.Path(sys.argv[1])
CANDIDATE = '2e9d6a468c110684c278d585418eb404250d1150'


def put(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse(path):
    rows = []
    for no, line in enumerate(path.read_text().splitlines(), 1):
        body = re.sub(r'^\d{4}-\S+Z ', '', line)
        body = re.sub(r'\x1b\[[0-9;]*m', '', body)
        if not body.startswith('{'):
            continue
        try:
            data = json.loads(body)
        except ValueError:
            continue
        if isinstance(data, dict):
            rows.append(dict(log=path.name, line=no, raw=data))
    return rows


observed = [row for p in sorted((E / 'logs').glob('own-*.log')) for row in parse(p)]
cases = [r for r in observed if isinstance(r['raw'].get('case'), str) and isinstance(r['raw'].get('status'), str)]
assert len({(r['log'], r['raw'].get('group'), r['raw']['case']) for r in cases}) == len(cases)
put('CASE_ATTEMPTS.json', cases)
put('RUNTIME_SUMMARIES.json', [r for r in observed if r not in cases])
groups = collections.defaultdict(collections.Counter)
for r in cases:
    groups[(r['log'], r['raw'].get('group'))][r['raw']['status']] += 1
put('CASE_COUNTS.json', [dict(log=k[0], group=k[1], counts=dict(v)) for k, v in groups.items()])

manifest = json.loads((OUT / 'EXECUTION_MANIFEST.json').read_text())
expected = [s for ids in manifest['cp17_required_case_ids'].values() for s in ids]
cp17 = [r for r in cases if r['log'].startswith('own-38928849640')]
assert len(expected) == 145
assert {r['raw']['case'] for r in cp17} == set(expected) | {'CP6_AUDITOR_PUBLIC_STATE_STABLE_ORDER'}
assert all(r['raw']['status'] == 'PASS' for r in cp17)
own = json.loads((OUT / 'OWN_ORACLES.json').read_text())
canonical = []
for key in own['native_ids'] + own['dom_ids']:
    attempts = [r for r in cases if r['raw']['case'] == key]
    assert attempts
    if key == 'ASTRA_R2_REOPEN_AFTER_REVERSED_FG_ADJUSTMENT':
        assert [r['raw']['status'] for r in attempts] == ['INCOMPLETE', 'COUNTEREXAMPLE']
    else:
        assert len(attempts) == 1
    canonical.append(dict(case=key, status=attempts[-1]['raw']['status'], attempts=attempts,
                          counting='One unique case; original status retained in attempts'))
matrix = [r for r in cases if r['raw']['case'].startswith('ASTRA_R2_MATRIX_')]
assert len(matrix) == 288 and all(r['raw']['status'] == 'PASS' for r in matrix)
assert sum(r['raw'].get('rendered') is False for r in matrix) == 34
put('INDEPENDENT_CASES.json', dict(native_and_dom=canonical, matrix=matrix,
    counts=dict(unique_cases=303, PASS=300, COUNTEREXAMPLE=3,
                original_INCOMPLETE_retained=1, raw_attempts=304),
    caveat='288 entry assertions include 34 hidden-nav checks, not 288 full business journeys.'))

register = []
for p in sorted(E.glob('run-[0-9]*.json')):
    data = json.loads(p.read_text())
    assert data['run']['status'] == 'completed'
    assert all(j['status'] == 'completed' for j in data['jobs'])
    data['product_checkout'] = CANDIDATE
    data['origin'] = 'INDEPENDENT_NATIVE_RERUN'
    data['oracle_origin'] = 'WRITER_PREDECLARED' if data['run']['id'] in [38928849615,38928849640,38928849710] else 'ASTRA_PREDECLARED'
    register.append(data)
assert len(register) == 7 and sum(len(r['jobs']) for r in register) == 11
put('RUN_REGISTER.json', register)

writer_runs = json.loads((E / 'writer-runs-api.json').read_text())
put('WRITER_RUN_RECEIPT.json', writer_runs)
failed = json.loads((E / 'writer-failure-jobs.json').read_text())
failure_review = []
for run in failed:
    jobs = []
    for job in run['jobs']:
        path = E / 'logs' / f"writer-{run['run']['id']}-{job['id']}.log"
        lines = path.read_text().splitlines()
        error_index = next((i for i,s in enumerate(lines) if '##[error]' in s), None)
        context = lines[max(0,error_index-7):error_index+1] if error_index is not None else []
        raw = parse(path)
        raw_cases = [r for r in raw if r['raw'].get('case') and r['raw'].get('status')]
        counts = collections.Counter(r['raw']['status'] for r in raw_cases)
        classification = ('OBSOLETE_SCENARIO_CONTEXT_AND_RETIRED_SELECTORS' if run['run']['id']==38906744394
            else 'EXPIRED_AE_ARTIFACT' if run['run']['id']==38894846530 and job['conclusion']=='failure'
            else 'HISTORICAL_SOURCE_SCOPE_GUARD' if job['conclusion']=='failure' else 'PREDECESSOR_OR_CONTROL_JOB')
        jobs.append(dict(job=job, classification=classification, first_error_context=context,
                         raw_case_counts=dict(counts), raw_cases=raw_cases,
                         log=path.name, sha256=digest(path), bytes=path.stat().st_size))
    failure_review.append(dict(run=run['run'], jobs=jobs,
        disposition='Keep failure; do not call predecessor/control PASS a current-candidate acceptance.'))
put('WRITER_FAILURE_REVIEW.json', failure_review)

disposition = []
for r in cases:
    if not r['log'].startswith('own-38928849710') or r['raw']['status'] in ('PASS','CONTROL_PASS','MATCH'):
        continue
    c = r['raw']
    if c.get('group') == 'AR_SEQUENTIAL':
        reason = 'Superseded by ERP-DEC02/M:5023 B: BC_FREE_REQUIRES_POLICY is correct; AR_SUPERSEDING:ACCESSORY_CONNECTED_ZERO_REFUSED_BC_FREE_POLICY PASS. Original INCOMPLETE retained.'
        status = 'SUPERSEDED_BY_OWNER_RULE'
    elif c.get('group') == 'BUSINESS':
        reason = 'Frozen date-policy marker retained. C0 D01.1-5 ratified e83d56e6 supplies the separate date oracles; T2_C0_ORACLE 25/25 PASS. Not relabelled as frozen PASS.'
        status = 'HISTORICAL_DATE_POLICY_MARKER'
    else:
        reason = 'Original date oracle retained. Separate C0 group contains 8 AS +12 calendar +4 AO +1 adjustment, all PASS under ratified e83d56e6. Amount/identity assertions and original results preserved.'
        status = 'SUPERSEDED_BY_OWNER_RULE'
    disposition.append(dict(observation=r, disposition=status, reason=reason))
put('T2_DISPOSITION.json', dict(result='DISPOSITION_REQUIRED_RAW_RETAINED', rows=disposition,
    c0_source='scripts/cp6_c0_oracles_auditor.py',
    c0_sha256=digest(ROOT/'scripts/cp6_c0_oracles_auditor.py'),
    warning='Independent execution of previously qualified oracles, not newly authored Astra cases.'))

put('CP1_CP2_HASH_RECHECK.json', json.loads((E/'CP1_CP2_HASH_RECHECK.json').read_text()))
crosswalk = ROOT/'docs/evidence/c6-all-crosswalk/C6_75_ALL22_CROSSWALK.json'
cross = json.loads(crosswalk.read_text())
assert len(cross['rows']) == 97 and len({r['id'] for r in cross['rows']}) == 97
put('C6_ALL_INDEX_REVIEW.json', dict(path=str(crosswalk.relative_to(ROOT)), sha256=digest(crosswalk),
    indexed_candidate=cross['candidate'], counts=cross['counts'], rows_unique=97,
    status='REUSED_HISTORICAL_INDEX_NOT_97_NEW_ACCEPTANCES',
    current_scope='Index/disposition availability confirmed; not a fresh case for every requirement.'))

identity = json.loads((OUT/'IDENTITY.json').read_text())
control = json.loads((E/'head.json').read_text())['commit']
git = lambda *args: subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
after = {p:git('rev-parse',f'{control}:{p}') for p in identity['product_trees'] if p!='.github'}
assert all(after[k]==identity['product_trees'][k] for k in after)
assert not git('diff','--name-only',CANDIDATE,'--','src','scripts','tests','supabase','package.json','package-lock.json','vite.config.ts')
changes = git('diff','--name-only',CANDIDATE,control).splitlines()
assert all(p.startswith('audit/astra_cp17_r2/') or p.startswith('.github/workflows/audit-astra-r2-') for p in changes)
put('FINAL_IDENTITY_CHECK.json', dict(candidate=CANDIDATE,candidate_tree=git('rev-parse',f'{CANDIDATE}^{{tree}}'),
    audit_control_head=control, product_trees_before=identity['product_trees'], product_trees_after=after,
    all_product_trees_equal=True, original_github_files_unchanged=True, audit_only_paths=changes,
    migrations_immutable=not git('diff','--name-only','dfab13bf62398a69a02bf6221c06d29075e5e40b',CANDIDATE,'--','supabase')))

logs = sorted((E/'logs').glob('*.log'))
put('RAW_LOG_INDEX.json', [dict(file=p.name,bytes=p.stat().st_size,sha256=digest(p)) for p in logs])
with tarfile.open(OUT/'RAW_LOGS.tar.xz','w:xz') as tar:
    for p in logs:
        info = tar.gettarinfo(str(p),arcname=p.name)
        info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
        with p.open('rb') as f:tar.addfile(info,f)
for name in ['RUNTIME_SUMMARIES.json', 'INDEPENDENT_CASES.json', 'WRITER_FAILURE_REVIEW.json', 'CASE_ATTEMPTS.json']:
    raw = OUT/name
    (OUT/(name+'.gz')).write_bytes(gzip.compress(raw.read_bytes(), mtime=0))
    raw.unlink()
print(json.dumps(dict(raw_logs=len(logs),unique_astra_cases=303,raw_astra_attempts=304,
    cp17=145,cp17_extra=1,own_runs=7,own_jobs=11,product_equal=True,
    raw_archive_bytes=(OUT/'RAW_LOGS.tar.xz').stat().st_size)))
