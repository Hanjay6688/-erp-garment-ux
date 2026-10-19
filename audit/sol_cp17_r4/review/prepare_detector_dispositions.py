"""Source-only finite catalog. Observed clean zeros never become negative PASS."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import gzip
import json
import re

A = Path(__file__).resolve().parents[1]
REPO = A.parents[1]

def read_source(path):
    data = (REPO / path).read_bytes()
    expanded = gzip.decompress(data) if path.endswith('.gz') else data
    return expanded.decode(), dict(path=path, stored_sha256=sha256(data).hexdigest(),
                                    expanded_utf8_sha256=sha256(expanded).hexdigest(),
                                    line_basis='DECOMPRESSED_UTF8_SQL' if path.endswith('.gz') else 'UTF8_SQL')

def body(text):
    m = re.search(r'\bAS\s+(\$[\w]*\$)', text, re.I)
    if not m:
        return text
    end = text.find(m[1], m.end())
    return text[m.end():end] if end >= 0 else text[m.end():]

def units(sql):
    """Top-level UNION/RETURN QUERY statement bounds; preserve nested CTE SQL."""
    bounds, i, depth = [(0, 0)], 0, 0
    while i < len(sql):
        if sql.startswith('--', i):
            j = sql.find('\n', i); i = len(sql) if j < 0 else j + 1; continue
        if sql.startswith('/*', i):
            j = sql.find('*/', i + 2); i = len(sql) if j < 0 else j + 2; continue
        if sql[i] in "'\"":
            q = sql[i]; i += 1
            while i < len(sql):
                if sql[i] == q:
                    if i + 1 < len(sql) and sql[i + 1] == q: i += 2; continue
                    i += 1; break
                i += 1
            continue
        if sql[i] == '(': depth += 1
        if sql[i] == ')': depth -= 1
        if depth == 0:
            m = re.match(r'(?:union\s+all|return\s+query)\b|;', sql[i:], re.I)
            if m:
                bounds.append((i, i + len(m[0]))); i += len(m[0]); continue
        i += 1
    return bounds + [(len(sql), len(sql))]

def predicate(text, name):
    sql = body(text)
    m = re.search(r"\bselect\s+'" + re.escape(name) + r"'\s*(?:::text)?\s*,", sql, re.I)
    if not m:
        return None
    bs = units(sql)
    start = max(b[1] for b in bs if b[1] <= m.start())
    end = min(b[0] for b in bs if b[0] > m.start())
    out = sql[start:end].strip()
    assert name in out and len(out) > len(name)
    # A top-level UNION member can refer to a WITH binding declared before the
    # first member (for example `from ar`). Preserve that statement preamble,
    # rather than publishing an isolated SELECT with an unresolved CTE.
    query_start = 0
    for left, right in bs:
        if right <= m.start() and sql[left:right].lower().startswith('return'):
            query_start = right
    prefix = sql[query_start:m.start()].lstrip()
    if prefix.lower().startswith('with ') and not out.lower().startswith('with '):
        first = re.search(r"\bselect\s+'[A-Za-z0-9_]+'\s*(?:::text)?\s*,\s*'(?:ERROR|WARN|CRITICAL)'", prefix, re.I)
        if first:
            preamble = prefix[:first.start()].rstrip()
            ctes = set(re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\s+as\s*\(', preamble, re.I))
            references = set(re.findall(r'\b(?:from|join)\s+([A-Za-z_][A-Za-z0-9_]*)\b(?!\.)', out, re.I))
            if ctes & references:
                out = preamble + '\n' + out
    return out

CATALOG = {
 'browser_direct_transfer_write_grant', 'transfer_view_not_security_invoker',
 'browser_direct_gudang_document_write', 'browser_legacy_gudang_post_execute',
 'v266_protected_tables_with_direct_write', 'v266_legacy_fg_rpc_exposed', 'v266_public_rpc_execute',
 'v266_view_without_security_invoker', 'V267_BROWSER_ROLE_DIRECT_INVOICE_WRITE',
 'V268_LIABILITY_VIEW_HELPER_PRIVILEGE', 'V268_BROWSER_DIRECT_LEDGER_OR_INVOICE_WRITE',
}
DERIVED = {'KASBON_STATUS_MISMATCH', 'V2620M_SUPPLIER_PAYMENT_EXACT_STATUS',
           'V2620M_OPENING_SUBLEDGER_STATE', 'V2620C_VENDOR_PAYMENT_EXACT_STATUS_MISMATCH',
           'V2620C_HPP_STATE_HAS_SUBCENT', 'V2620H_CUSTOMER_AR_STATUS_MISMATCH'}
MASTER = {'ACCESSORY_CATEGORY_UOM_MISMATCH', 'V267_GRNI_MAPPING_INVALID', 'V267_MISSING_GRNI_MAPPING'}

def classification(name, tables):
    inputs = ', '.join(tables) or 'the source expressions printed in predicate_sql'
    if name in CATALOG:
        return dict(category='CATALOG_ACCESS_COUNTER_NOT_EXECUTED', executable_now=False,
                    reason='A positive corruption would require changing grants, execute privileges or view security. That is outside the declared mutable-state controls and new access probes remain held. Clean catalog observations are not a 0→+1→0 proof.',
                    next_action='A separately authorized access-catalog qualification must bind the exact privilege/view predicate below and restore catalog identity; do not alter grants merely to complete this report.')
    if name == 'v266_missing_optimistic_version':
        return dict(category='SCHEMA_COUNTER_NOT_EXECUTED', executable_now=False,
                    reason='The detector inspects presence of version columns. Producing a missing-column defect would require schema DDL outside the authorized state-only counterfixtures.',
                    next_action='Use a separate explicit disposable schema-qualification scope if authorized; no DDL was attempted here.')
    if name in MASTER:
        return dict(category='CONFIGURATION_OR_MASTER_COUNTER_NOT_PREDECLARED', executable_now=False,
                    reason=f'The predicate consumes {inputs}. No one-record configuration/category fault constructor with exported collateral deltas was frozen or executed. This is not owner-deferred or evidence that a counterfixture is impossible.',
                    next_action='Auditor: derive a finite new master/configuration fixture from this exact predicate and existing validator/history guards, declare collateral alarm deltas before execution, and retain a full rollback.')
    if name in DERIVED:
        return dict(category='DERIVED_STATE_COUNTER_NOT_PREDECLARED', executable_now=False,
                    reason=f'The check consumes derived status/cache state in {inputs}. Additional admin-safe counterfixtures may exist, but none for this identity was prepared or executed. The current mutable allowlist does not confer PASS on this check.',
                    next_action='Auditor: pin a new one-row derived-state fixture and the exact predicate below; do not change source facts or expected values solely for green. This is an unexecuted audit item, not a writer bug.')
    return dict(category='BUSINESS_FACT_OR_LINEAGE_COUNTER_NOT_EXECUTED', executable_now=False,
                reason=f'The predicate consumes {inputs}. Normal business journeys/refusals and clean zero output were observed; a deliberately inconsistent source/lineage/journal state for this identity was not constructed. Declared counter phases preserved seven fact tables and all guards. Admin exceptions exist, so this does not assert immutable facts are technically impossible to perturb.',
                next_action='Auditor: design a one-lineage counterfixture for this exact predicate, separately declare authorized fact-table changes and collateral detector counts if needed, and export before/during/rollback all167 identities. Real cutover is a separate production gate, not a blanket reason for skipping this synthetic check.')

def main():
    definitions_path = A / 'ci_receipts/sol_artifacts/12161878541/files/SOL_R4_CURRENT_DETECTOR_DEFINITIONS.json'
    definitions = json.loads(definitions_path.read_text())
    extras_path = A / 'ci_receipts/sol_artifacts/12162647072/files/SOL_R4_MUTABLE_SOURCE_DEFINITIONS.json'
    extras = json.loads(extras_path.read_text())
    nav = json.loads((A / 'ci_receipts/STATIC_DETECTOR_LITERAL_MAP.json').read_text())
    controlled = {}
    finite = json.loads((A / 'FUNCTIONAL_BOUNDARIES_RESULT_REVIEW.json').read_text())
    for row in finite['detector_controls']:
        for key in row['exact_deltas']:
            controlled[key] = dict(case_id=row['id'], run_id=row['run_id'], artifact_id=row['artifact_id'], review='FUNCTIONAL_BOUNDARIES_RESULT_REVIEW.json')
    d07 = json.loads((A / 'DETECTOR_RESULT_REVIEW.json').read_text())
    controlled[d07['one_controlled_check']] = dict(case_id=d07['case_id'], run_id=d07['run_id'], artifact_id=d07['artifact_id'], review='DETECTOR_RESULT_REVIEW.json')
    mutable = json.loads((A / 'MUTABLE_DETECTOR_RESULT_REVIEW.json').read_text())
    for row in mutable['canonical_cases']:
        for phase in row['phases']:
            for key in phase['exact_deltas']:
                controlled[key] = dict(case_id=row['case_id'], run_id=row['run_id'], artifact_id=row['artifact_id'], review='MUTABLE_DETECTOR_RESULT_REVIEW.json')
    prevention = {}
    if (A / 'DERIVED_DETECTOR_RESULT_REVIEW.json').exists():
        derived = json.loads((A / 'DERIVED_DETECTOR_RESULT_REVIEW.json').read_text())
        prevention = derived['guard_prevention']
        for row in derived['canonical_cases']:
            if row['case_kind'] == 'DETECTOR_CONTROL':
                for phase in row['phases']:
                    for key in phase['exact_deltas']:
                        controlled[key] = dict(case_id=row['case_id'], run_id=row['run_id'], artifact_id=row['artifact_id'], review='DERIVED_DETECTOR_RESULT_REVIEW.json')
    if (A / 'PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json').exists():
        dispute = json.loads((A / 'PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json').read_text())
        for row in dispute['canonical_cases']:
            if row['case_kind'] == 'DETECTOR_CONTROL' and row['raw_status'] == 'PASS':
                for phase in row['phases']:
                    for key in phase['exact_deltas']:
                        controlled[key] = dict(case_id=row['case_id'], run_id=row['run_id'], artifact_id=row['artifact_id'], review='PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json')
    rows = []
    for navrow in nav['rows']:
        fn, name = navrow['function_observed'], navrow['check_name']
        key = fn + ':' + name
        text = definitions[fn]; pred = predicate(text, name)
        origin = dict(path=str(definitions_path.relative_to(A)), function=fn, sha256=sha256(text.encode()).hexdigest(), binding='RUNTIME_PG_GET_FUNCTIONDEF_DIRECT')
        if pred is None and fn == 'run_v268_financial_report_checks':
            text = extras['_v268_financial_report_checks_pre_scope()']; pred = predicate(text, name)
            origin = dict(path=str(extras_path.relative_to(A)), function='_v268_financial_report_checks_pre_scope', sha256=sha256(text.encode()).hexdigest(), binding='RUNTIME_PG_GET_FUNCTIONDEF_DELEGATE')
        if pred is None:
            possibilities = [c for c in navrow['occurrences'] if c.get('nearest_preceding_function') and any(x in c['nearest_preceding_function'] for x in ['checks', 'run_integrity_checks']) and not any(x in c['path'] for x in ['registry', 'selftest'])]
            for c in reversed(possibilities):
                source, metadata = read_source(c['path'])
                lines = source.splitlines(True)
                fragment = ''.join(lines[c['function_start_line'] - 1:])
                # Candidate source may contain later functions; isolate this CREATE body.
                delimiter = re.search(r'\bAS\s+(\$[\w]*\$)', fragment, re.I)
                if delimiter:
                    end = fragment.find(delimiter[1], delimiter.end())
                    if end >= 0: fragment = fragment[:end + len(delimiter[1])]
                test = predicate(fragment, name)
                if test:
                    pred = test; origin = dict(metadata, function=c['nearest_preceding_function'], line=c['line'], binding='CANDIDATE_DELEGATE_SOURCE_OBSERVED_OUTPUT_IDENTITY'); break
        assert pred is not None, key
        tables = sorted(set(re.findall(r'\b(?:from|join|update|into)\s+(erp\.[a-zA-Z0-9_]+)', pred, re.I)))
        row = dict(identity=key, function=fn, check_name=name, predicate_origin=origin,
                   predicate_sql=pred, predicate_sha256=sha256(pred.encode()).hexdigest(), input_relations=tables,
                   normal_zero_observed=True, negative_control_disposition='TIDAK_TERUJI', runtime_credit_from_static_map=0)
        if key in controlled:
            row.update(negative_control_disposition='PASS_EXACT_0_1_0', evidence=controlled[key],
                       classification=dict(category='CURRENT_EXACT_CONTROL', executable_now=False, reason='At least one frozen counter phase increments this exact identity by1 with all167 keysets and rollback equality exported.', next_action='Retain regression evidence; no PASS control is repeated for count inflation.'))
        else:
            row['classification'] = classification(name, tables)
        if key in prevention:
            row.update(prevention_evidence=prevention[key], classification=dict(category='CURRENT_NATIVE_GUARD_PREVENTION_ONLY', executable_now=False,
                       reason='Two exact P0001 refusals prevent this inconsistent configuration with guards unchanged and all167 counts remaining zero. This is prevention, not detector sensitivity.',
                       next_action='Retain prevention evidence. Sensitivity remains TIDAK TERUJI unless an explicit separate weakened-environment scope is authorized; do not weaken candidate guards or turn refusal into count+1.'))
        if name == 'V2620M_OPENING_SUBLEDGER_STATE' and key not in controlled:
            row['classification'] = dict(category='ISOLATED_OPENING_QUALIFICATION_PENDING', executable_now=True,
                       reason='The first opening control never mutated state: valid FG_REPAIR Nota predecessor raised wrong-contractor2. That alarm is preserved as a product dispute; an opening-only accepted BB fixture is declared separately.',
                       next_action='Read PAYROLL_DETECTOR_DISPUTE_PREEXECUTION_MANIFEST qualification; keep65/0/OPEN and both expected+1 unchanged, no repeat of priorPASS cases.')
        if key == 'run_v263a_payroll_integrity_checks:payroll_work_wrong_contractor':
            row.update(normal_zero_observed=False, zero_observed_on_other_control_fixtures=True,
                       valid_FG_REPAIR_predecessor_alarm=dict(count=2, run_id=39199375501, artifact_id=12163127220,
                            status='PENDING_ACTUAL_LINEAGE_DISPUTE', review='DERIVED_DETECTOR_RESULT_REVIEW.json',
                            note='Not an injected wrong-contractor state. The valid Nota source path must be resolved; do not dismiss as an adversarial fixture.'))
            if (A / 'PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json').exists():
                row['valid_FG_REPAIR_predecessor_alarm'] = dispute['false_alarm_disposition']
        if name == 'UNBALANCED_POSTED_JOURNALS':
            row['retained_reference'] = dict(origin='SOL_R1_R2_RETAINED_IN_R3_SEAL', seal='ff6374ad6edef19896c32258e3f30172a95069bd', runtime_credit_r4=0, current_exact_negative_control=False, note='Historical control reference is retained; no current duplicate V268 identity proof inferred.')
        rows.append(row)
    assert len(rows) == len({r['identity'] for r in rows}) == 167
    statuses = Counter(r['negative_control_disposition'] for r in rows)
    result = dict(state='CURRENT_PREDICATE_CATALOG_WITH_EXPLICIT_UNEXECUTED_NEGATIVE_CONTROLS', candidate_sha='663f6faefcbb9c70f0f99bbc7e78164e03521329',
                  denominator=167, status_counts=dict(statuses), category_counts=dict(Counter(r['classification']['category'] for r in rows)),
                  global_INV_D01_closed=False, audit_complete=False,
                  method='Runtime direct definitions preferred; runtime pre-scope delegate next; remaining exact output identities bind to pinned candidate delegate SQL. Static navigation never confers execution credit. All source expressions are preserved, not guessed from names.',
                  important_limit='Normal zeros do not confer sensitivity PASS. Two native guard-prevention controls remain TIDAK TERUJI for sensitivity. Legitimate FG_REPAIR false-alarm dispute is separate from opening-only sensitivity. Source/fact-lineage, held access and schema counters retain their specific scope; the protocol gate remains false.', rows=rows)
    (A / 'DETECTOR_DISPOSITIONS.json').write_text(json.dumps(result, indent=2) + '\n')
    md = ['# Disposisi 167 identitas detektor — Sol r4', '',
          f"Kontrol exact: {statuses['PASS_EXACT_0_1_0']}; belum mendapat kontrol negatif current: {statuses['TIDAK_TERUJI']}. INV-D01 dan audit_complete tetap false. Nol normal bukan bukti deteksi. Identitas fungsi+nama dipisahkan meskipun nama tampil dua kali.", '',
          'Setiap baris JSON memuat predicate SQL lengkap, input, asal/hash dan pekerjaan auditor berikut. Batas belum dikerjakan tidak disamarkan sebagai bug produk, ketidakmungkinan, atau keputusan owner. Guard yang mempunyai pengecualian admin disebutkan; tidak ada trigger/grant yang dilonggarkan.', '',
          '| Identitas | Kontrol negatif | Klasifikasi | Input predicate |', '|---|---|---|---|']
    for r in rows:
        md.append('| ' + r['identity'] + ' | ' + r['negative_control_disposition'] + ' | ' + r['classification']['category'] + ' | ' + ', '.join(r['input_relations']) + ' |')
    md += ['', 'Sumber/predicate dan tindakan per ID: [DETECTOR_DISPOSITIONS.json](DETECTOR_DISPOSITIONS.json). Tidak ada klaim seluruh sisa memerlukan cutover nyata; counterfixture sintetis, kontrol katalog yang tertahan dan gate produksi adalah pekerjaan berbeda.']
    (A / 'DETECTOR_DISPOSITIONS.md').write_text('\n'.join(md) + '\n')
    print(dict(statuses), result['category_counts'])

if __name__ == '__main__': main()
