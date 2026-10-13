"""Render audit evidence tables without changing any original result."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
RAW = HERE.parents[2] / 'audit-artifacts'
SHA = 'd0b9e9c2e41a9f0f3a138346887434fd7d3c14f0'
TREE = '4bd5e1acf55f0b441d9c8f67949ee5b070eb9c41'
r = json.loads((HERE / 'evidence/RECONCILIATION.json').read_text())
idx = {a['id']: a for a in json.loads((HERE / 'evidence/ARTIFACT_INDEX.json').read_text())}
known_runs = {str(x['id']): x for x in json.loads((HERE / 'RUN_INDEX.json').read_text())['runs']}
own = {k.split('/', 1)[1]: v for k, v in r['canonical_case_observations'].items() if k.startswith('ASTRA_CONTRACT/')}
expected = set(json.loads((HERE / 'INDEPENDENT_MANIFEST.json').read_text())['registered_ids'])
expected.update(json.loads((HERE / 'NEW_CASE_MANIFEST.json').read_text())['case_ids'][:8])
expected.add(json.loads((HERE / 'K7_EQUIVALENCE_MANIFEST.json').read_text())['case_id'])
tablet_manifest = HERE / 'TABLET_MANIFEST.json'
if tablet_manifest.exists(): expected.add(json.loads(tablet_manifest.read_text())['case_id'])
assert set(own) <= expected, {'unexpected': sorted(set(own)-expected)}
assert len(expected) == (77 if tablet_manifest.exists() else 76)
missing_own = sorted(expected-set(own))

identity = []
saved = []
(HERE / 'evidence/archives').mkdir(exist_ok=True)
for a in r['archives']:
    directory = RAW / str(a['artifact_id'])
    execution = json.loads((directory / 'ASTRA_EXECUTION_ORIGIN.json').read_text())
    receipt_path = directory / 'ASTRA_SOURCE_RECEIPT.json'
    source = json.loads(receipt_path.read_text())
    assert source['candidate_sha'] == execution['product_sha'] == SHA
    assert source['candidate_tree'] == TREE
    assert execution['run_id'] == str(a['run_id'])
    assert execution['audit_workflow_sha'] == known_runs[str(a['run_id'])]['control_commit']
    identity.append(dict(artifact=a['artifact_id'], run=a['run_id'], product_sha=SHA,
        workflow_sha=execution['audit_workflow_sha'], raw_oracle_origin=execution['oracle_origin'],
        assigned_origin='ASTRA_CONTRACT' if '-own-' in a['artifact_name'] else 'WRITER_ORACLE_RERUN_BY_ASTRA',
        source_receipt_sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest()))
    z = directory.with_suffix('.zip')
    digest = hashlib.sha256(z.read_bytes()).hexdigest()
    assert digest == idx[a['artifact_id']]['digest'].removeprefix('sha256:')
    target = HERE / 'evidence/archives' / z.name
    if not target.exists(): shutil.copyfile(z, target)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
    saved.append(dict(id=a['artifact_id'], path=str(target.relative_to(HERE)), bytes=target.stat().st_size, sha256=digest))
(HERE / 'evidence/EXECUTION_IDENTITY_CHECK.json').write_text(json.dumps(dict(verified_archives=len(identity), all_same_candidate=True, rows=identity),indent=2)+'\n')
(HERE / 'evidence/SAVED_ARCHIVES.json').write_text(json.dumps(saved,indent=2)+'\n')

lines = ['# Hasil kasus mandiri Astra', '', 'Kandidat `d0b9e9c2`. Satu baris = satu ID kanonik, bukan setiap pengulangan atau assertion. Arsip asli diverifikasi dengan digest GitHub; pemetaan run ada di `evidence/ARTIFACT_INDEX.json`.', '', '| ID | Status mentah | Disposisi | Artifact ID |', '|---|---|---|---|']
unique_status = Counter()
for key, obs in sorted(own.items()):
    states = sorted({x['status'] for x in obs})
    unique_status[' / '.join(states)] += 1
    disposition = 'PASS' if states == ['PASS'] else 'Batas detektor lama pada salinan yang sengaja dilemahkan; hasil mentah dipertahankan'
    lines.append('| ' + ' | '.join([key, ' / '.join(states), disposition, ', '.join(str(x) for x in sorted({v['artifact_id'] for v in obs}))]) + ' |')
lines += ['', f'{len(own)} ID mandiri: {dict(unique_status)}. Kontrol alat tanggal ASF09–12 dilaporkan terpisah: 2 PASS dan 2 COUNTEREXAMPLE yang menjadi satu temuan ASF-F01.', '', 'FULL_FLOW terlewat oleh filter runner awal dan dijalankan pertama kali pada run 38161351529; oracle tidak berubah. UI awal berhenti sebelum kasus pertama karena inventaris auditor belum disalin; run pemulihan 38160527120 menjalankan tiga kasus dengan inventaris asli. Kedua kekurangan alat auditor tidak dibebankan kepada writer.', '']
lines += [f'Kasus terdaftar yang belum mempunyai hasil: {missing_own}. Tidak dihitung PASS.', '']
(HERE / 'OWN_RESULTS.md').write_text('\n'.join(lines))

lines = ['# Regresi dengan oracle writer yang dijalankan Astra', '', 'Kandidat `d0b9e9c2`; runner audit sendiri. Ini bukti `INDEPENDENT_NATIVE_RERUN`, dengan `oracle_origin=WRITER_UNCHANGED`. Jumlah di bawah berasal dari baris hasil asli, bukan nama job. Smoke dan fase gladi tidak ditambahkan ke hitungan kasus produk.', '', '| Suite | Kasus produk PASS/teramati | Smoke PASS/teramati | Status mentah | Artifact ID |', '|---|---:|---:|---|---|']
counts = Counter()
rehearsals = []
for a in r['archives']:
    if '-own-' in a['artifact_name']: continue
    for s in a['reports']:
        states = Counter(status for g in s['groups'].values() if not g['smoke'] for status in g['case_ids'].values())
        smoke = Counter(status for g in s['groups'].values() if g['smoke'] for status in g['case_ids'].values())
        assert s['case_budget_match'], (a['artifact_id'], s['file'], 'budget')
        assert not s['errors'], (a['artifact_id'], s['errors'])
        assert s['declared_group_keys_match'] is not False
        assert s['cp6_restored'] is not False and s['advisor_gate'] is not False
        for group in s['groups'].values():
            assert group['planned_ids_match'] and group['counts_match'], (a['artifact_id'], group)
            assert group['declared_ids_match'] is not False
            assert group['group_budget_match'] is not False
        counts.update(states)
        counts['smoke_executions'] += sum(smoke.values())
        counts['smoke_pass'] += smoke['PASS']
        counts['reports'] += 1
        lines.append(f"| {s['file']} | {states['PASS']}/{sum(states.values())} | {smoke['PASS']}/{sum(smoke.values())} | {s['reported_status']} | {a['artifact_id']} |")
    for s in a.get('rehearsals', []):
        rehearsals.append(dict(artifact_id=a['artifact_id'], file=s['file'], status=s['status'], steps=[x['step'] for x in s['steps']], cp6_restored=s['cp6_restored'], advisor_gate=s['advisor_gate']))
        lines.append(f"| {s['file']} | — | — | {s['status']}; {len(s['steps'])} fase | {a['artifact_id']} |")
lines += ['', 'P21 dasar: enam fase. P21 penuh: sembilan fase, termasuk transaksi COMMITTED, penolakan rollback sesudah dipakai, backup terpakai → restore 559 tabel, lalu restore pra-pasang. Tidak mengklaim rollback sesudah dipakai tanpa kehilangan transaksi. `pg_restore` keluar 1 karena 19 kesalahan pg_cron yang dilaporkan satu per satu pada database tujuan terpisah; tidak ada error tak terjelaskan. Catalog dibandingkan secara semantik untuk perbedaan serialisasi/ACL yang dicatat.', '', 'P19: 48 pengukuran UI dalam empat kasus browser. Lulus fungsi/batas bukan berarti semua waktu ≤3 detik. Rincian waktu, penolakan yang jujur, buka DONE, dan pindah halaman ada di `evidence/SCALE_BROWSER_SUMMARY.json`.', '']
(HERE / 'REGRESSION_RESULTS.md').write_text('\n'.join(lines))
summary = dict(candidate=SHA, product_cases_own_unique=len(own), own_status_counts=dict(unique_status), own_executions=sum(len(v) for v in own.values()), writer_regression=dict(counts), rehearsals=rehearsals, own_manifest_complete=not missing_own, own_cases_pending=missing_own, own_cases_expected=len(expected), pending_regression_reports=42-counts['reports'], production_go=False)
summary['writer_product_unique_ids'] = sum(k.startswith('WRITER_ORACLE_RERUN_BY_ASTRA/') and any(not row['smoke'] for row in rows) for k, rows in r['canonical_case_observations'].items())
summary['writer_smoke_unique_ids'] = sum(k.startswith('WRITER_ORACLE_RERUN_BY_ASTRA/') and any(row['smoke'] for row in rows) for k, rows in r['canonical_case_observations'].items())
summary['date_rollover_flags_in_case_reports'] = sum(len(report['first_attempt_and_date_flags']) for artifact in r['archives'] for report in artifact['reports'])
summary['note'] = 'Unique IDs are not unique independent oracles. The same product case may recur in separate composition suites. Smoke and rehearsal phases are separate.'
(HERE / 'evidence/RESULT_SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
