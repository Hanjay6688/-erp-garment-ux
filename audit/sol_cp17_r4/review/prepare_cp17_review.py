"""Review preserved own CP17 JSON/log. No product code or fixture is executed."""
from collections import Counter
from decimal import Decimal as D
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
BASE = ROOT / 'ci_receipts/sol_artifacts/12158177672'
LOG = ROOT / 'ci_receipts/sol_cp17_117844410757.log'
MANIFEST = ROOT / 'CP17_PREEXECUTION_MANIFEST.json'
CANDIDATE = '663f6faefcbb9c70f0f99bbc7e78164e03521329'
GROUPS = {'native': 'CP7_CP17_FIXES', 'races': 'AUDITOR_RACES_CP7_CP17_FIXES',
          'http': 'AUDITOR_HTTP_CP7_CP17_FIXES', 'browser': 'AUDITOR_BROWSER_CP7_CP17_FIXES_BROWSER',
          'browser_enteng': 'AUDITOR_BROWSER_CP7_CP17_FIXES_BROWSER_ENTENG'}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, ('DUPLICATE_JSON_KEY', key)
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_text(), object_pairs_hook=unique_object)


def contrast(foreground, background):
    def parse(text):
        values = [float(x) for x in re.fullmatch(r'rgba?\(([^)]+)\)', text)[1].split(',')]
        return values[:3], values[3] if len(values) == 4 else 1
    fg, alpha = parse(foreground)
    bg, _ = parse(background)
    if alpha < 1:
        fg = [x * alpha + y * (1 - alpha) for x, y in zip(fg, bg)]
    def luminance(rgb):
        channels = [x / 255 for x in rgb]
        linear = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in channels]
        return sum(x * weight for x, weight in zip(linear, (.2126, .7152, .0722)))
    a, b = luminance(fg), luminance(bg)
    return (max(a, b) + .05) / (min(a, b) + .05)


def main():
    declaration = read(MANIFEST)
    report_path = BASE / 'files/CP7_CP17_FIXES.json'
    report = read(report_path)
    receipt = read(BASE / 'DOWNLOAD_RECEIPT.json')
    assert receipt['digest_matches']
    for item in receipt['selected_files']:
        data = (BASE / 'files' / item['path']).read_bytes()
        assert len(data) == item['bytes'] and sha256(data).hexdigest() == item['sha256']
    identities = [read(BASE / 'files' / ('SOL_R4_IDENTITY_' + phase + '.json')) for phase in ('BEFORE', 'AFTER')]
    for identity in identities:
        assert identity['candidate_sha'] == CANDIDATE and identity['candidate_tree'] == declaration['candidate_tree']
        assert identity['workflow_sha'] == '3eb1edd795efdbfb77a57c9165f05d5d5dc8ca13'
        assert identity['run_id'] == '39184657689' and identity['run_attempt'] == '1'
        assert identity['product_worktree_clean']
        for path, value in identity['product_roots'].items():
            assert value == subprocess.check_output(['git', 'rev-parse', CANDIDATE + ':' + path], cwd=REPO, text=True).strip()
    assert report['source_sha256'] == 'f883ec3fbe1c4cdde4a9249b1ed83afd2e62cfedceec2e6277a25ec0f2609318'
    assert report['predeclared_case_sha256'] == declaration['declaration_sha256']
    assert report['required_case_counts'] == declaration['required_case_counts']
    assert report['required_case_ids'] == declaration['required_case_ids']
    assert report['expected_case_count'] == report['observed_case_count'] == declaration['expected_case_count'] == 341
    assert report['cp6_restored'] and report['advisor_gate'] and report['restore_raw_public_equal']
    assert all(report['restore_components'].values())
    rows, groups = [], {}
    for group, label in GROUPS.items():
        result = report[group]
        cases = result['races' if group == 'races' else 'cases']
        wanted = declaration['required_case_ids'][group]
        assert len(cases) == len(wanted) == len(set(wanted)) == declaration['required_case_counts'][group]
        assert Counter(cases.keys()) == Counter(wanted)
        assert result['counts'] == {'PASS': len(wanted)}
        for case_id, observation in cases.items():
            assert observation['status'] == 'PASS'
            if 'full_boundary_restored' in observation:
                assert observation['full_boundary_restored'] and observation['public_schema_unchanged']
            if 'business_day' in observation:
                assert len(set(observation['business_day'].values())) == 1
            rows.append({'candidate_sha': CANDIDATE, 'workflow_sha': identities[0]['workflow_sha'],
                         'run_id': 39184657689, 'attempt': 1, 'artifact_id': 12158177672,
                         'group': group, 'case_id': case_id, 'raw_status': observation['status'],
                         'oracle_origin': 'WRITER_DECLARED_OR_R3_AUDITOR_REPRODUCTION_ADOPTED_BY_WRITER',
                         'fixture_origin': 'WRITER_SYNTHETIC_DISPOSABLE', 'observation': observation})
        if group != 'native':
            assert result['database_remaining'] == 0
        if group in ('http', 'browser', 'browser_enteng'):
            assert result['auth_counts']['restored'] and not result['cleanup_failures']
        groups[group] = {'count': len(cases), 'case_ids': list(cases), 'raw_status_counts': result['counts']}
    assert len({row['case_id'] for row in rows}) == len(rows) == 341

    # Check the first actual per-case log occurrence, not only the final report's green totals.
    log_rows, summaries = [], {}
    for line_number, line in enumerate(LOG.read_text().splitlines(), 1):
        clean = re.sub(r'^\S+Z\s*', '', line)
        if not clean.startswith('{'):
            continue
        try:
            value = json.loads(clean)
        except json.JSONDecodeError:
            continue
        label = value.get('group')
        if label not in GROUPS.values():
            continue
        group = next(k for k, v in GROUPS.items() if v == label)
        if 'case' in value:
            case_id = value['case'] + ('_ENTENG' if group == 'browser_enteng' else '')
            log_rows.append((group, case_id, value['status']))
        if 'enteng_requests_answered_by_loopback' in value:
            summaries[group] = {'line': line_number, **{k: value.get(k) for k in (
                'status', 'failed_stage', 'error', 'console_errors', 'users_created',
                'auth_cleanup_failures', 'enteng_requests_answered_by_loopback', 'enteng_route_errors')}}
    assert Counter(log_rows) == Counter((r['group'], r['case_id'], r['raw_status']) for r in rows)
    assert summaries['browser_enteng']['enteng_requests_answered_by_loopback'] == 1364
    for summary in summaries.values():
        assert summary['status'] == 'RUN_COMPLETE' and not summary['enteng_route_errors']
        assert not summary['auth_cleanup_failures'] and summary['console_errors'] == 0

    native = report['native']['cases']
    positive = native['CP17_R4_02_REOPEN_POSITIVE_ADJUSTMENT_INVERSE_ASTRA']
    assert positive['stock'] == [10, 12, 10] and positive['blockers'] == []
    assert sum(D(str(movement[1])) for movement in positive['movements']) == D(10)
    assert positive['movements'][-1][2] == positive['movements'][-2][0]
    assert [D(x) for x in positive['hpp_before_after']] == [D(120), D(10)]
    assert native['CP17_R4_02_POSITIVE_INVERSE_DOES_NOT_HIDE_ACTIVE_USE']['blocked'] == [{'qty': 2, 'kind': 'FG_USED'}]
    po = native['CP17_R3_01_AUTO_PO_NUMBER_1000_BOUNDED']
    assert po['actual_number'] == po['expected_number'] == 'PO-261017-1000'
    assert po['elapsed_seconds'] <= po['deadline_seconds'] == 3
    cash = native['CP17_R2_SPENT_INCOME_CORRECTION_COMMITS']
    assert D(cash['corrected_to']) - D(cash['spent']) == D(cash['bank_after']) == D('5.01')
    late = report['races']['races']['CP17_RACE_R4_03_AUDIT_LOWER_ID_LATE_COMMIT_ASTRA']
    assert late['held_row_invisible_at_first_page'] and late['observed_holder_state'] == 'idle in transaction'
    assert late['held_id'] < late['higher_committed_id'] <= int(late['as_of'])
    assert late['final_count'] == late['first_count'] + 1 == 9
    assert late['missed_ids'] == [str(late['held_id'])] and late['changed'] == [False, True, True]
    assert late['newer_signalled'] and late['fresh_same_cutoff_ids'] == late['all_native_ids']
    ordinary = report['races']['races']['CP17_RACE_R4_03_AUDIT_ORDINARY_ORDER_KEEPS_MARK']
    assert ordinary['mark'] == str(len(ordinary['walked'])) + '-' + str(sum(int(x) for x in ordinary['walked']))
    old = report['http']['cases']['CP17_HTTP_R4_01_EVERY_CLOSED_ROUTE_REFUSED_APP_ROUTES_OPEN']
    assert old['closed_routes_refused'] == 25 and old['answer'] == [403] and old['nothing_written']
    assert old['app_routes_answer'] == {'erp_get_my_access_v1': 200, 'erp_cp7_get_hpp_pools_v1': 200}
    denied = report['http']['cases']['CP17_HTTP_R4_01_POOL_PUBLIC_REVOKED_MANAGE_ASTRA']
    assert denied['native_rows'] == [] and denied['legacy']['body']['code'] == '42501'
    assert denied['legacy']['body']['message'] == 'CP7_PUBLIC_ROUTE_CLOSED'

    # The host overwrites the same two readability filenames during the later Enteng group.
    inventory = read(ROOT / 'SCREEN_PREEXECUTION_INVENTORY.json')
    expected_menus = {'Dashboard'}
    for section, items in inventory['sections'].items():
        expected_menus |= {section + ' › ' + item for item in items}
    expected_menus |= {'Pengaturan & Audit › ' + item for item in inventory['admin']}
    assert len(expected_menus) == inventory['expected_unique_menus'] == 47
    readability = []
    for device in ('DESKTOP', 'MOBILE'):
        path = BASE / 'files' / ('CP17_BROWSER_R4_04_CONNECTED_TEXT_READABLE_' + device + '.json')
        detail = read(path)
        menu_names = [row['menu'] for row in detail['menus']]
        extra = 'Keuangan › HPP & Rekalkulasi › pratinjau pool'
        assert set(menu_names) - {extra} == expected_menus and len(menu_names) == 48
        assert len(menu_names) == len(set(menu_names))
        assert not detail['low'] and detail['hpp_states_opened'] == ['preview']
        independent_ratios = [contrast(row['color'], row['background']) for row in detail['wip']]
        assert len(independent_ratios) == 145 and min(independent_ratios) >= 4.5
        assert all(abs(actual - row['ratio']) <= .02 for actual, row in zip(independent_ratios, detail['wip']))
        readability.append({'device': device, 'detail_origin': 'ENTENG_LAST_WRITER_OF_SAME_FILENAME',
                            'exact_47_menu_set': True, 'extra_preview_states': 1, 'draft_form_measured': False,
                            'wip_rows_recomputed': 145, 'minimum_unrounded_contrast': min(independent_ratios),
                            'measured': detail['measured'], 'skipped': detail['skipped'],
                            'sha256': sha256(path.read_bytes()).hexdigest()})
    for group in ('browser', 'browser_enteng'):
        suffix = '_ENTENG' if group.endswith('enteng') else ''
        for device in ('DESKTOP', 'MOBILE'):
            cases = report[group]['cases']
            rate = cases['CP17_BROWSER_R3_09_RATE_CHOICE_' + device + suffix]
            assert D(rate['new_rate_record']['wage']) == D(rate['new_rate_record']['pcs']) * (D(5) + D(1)) == D(12)
            pool = cases['CP17_BROWSER_R3_04_HPP_POOL_' + device + suffix]['replacement']
            assert pool['pcs'] == 20 and sorted(D(x) for x in pool['allocations'].values()) == [D(500), D(500)]
            assert sum(D(x) for x in pool['allocations'].values()) == D(1000)
        note = report[group]['cases']['CP17_BROWSER_R3_05_ACCESSORY_NOTE_TO_PAYROLL_DESKTOP' + suffix]
        assert D(note['labor']) - D(note['deduction']) == D(note['net']) == D(3900)
        assert note['reversed_note']['deducted'] is False and D(note['reversed_note']['amount']) == D(1500)

    ledger = ROOT / 'ci_receipts/SOL_CP17_CASE_LEDGER.jsonl'
    ledger.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows))
    result = {'report_state': 'FINAL_REVIEWED_CP17_COMPONENT_SCOPE', 'candidate_sha': CANDIDATE,
              'workflow_sha': identities[0]['workflow_sha'], 'run_id': 39184657689, 'attempt': 1,
              'artifact_id': 12158177672, 'job_id': 117844410757,
              'raw_status': report['status'], 'groups': groups, 'canonical_case_occurrences': len(rows),
              'unique_declared_id_strings': 341, 'predeclared_multisets_equal': True,
              'actual_log_per_case_multiset_equal': True, 'internal_business_day_retry_observed': False,
              'member_files_rehashed': len(receipt['selected_files']), 'hash_mismatches': 0,
              'report_sha256': sha256(report_path.read_bytes()).hexdigest(), 'log_sha256': sha256(LOG.read_bytes()).hexdigest(),
              'log_capture': 'Exact GitHub connector decoded text; not a provider ZIP digest',
              'ledger_path': str(ledger.relative_to(ROOT)), 'ledger_sha256': sha256(ledger.read_bytes()).hexdigest(),
              'transport_summaries_from_log': summaries,
              'transport_scope': '1364 Enteng-origin fetches answered by loopback; no route errors. '
                                 'Source routes both fetch/continue to local API and workflow checks host resolves '
                                 'to127.0.0.1. Build uses placeholder key. This is not hosted Enteng acceptance '
                                 'and request count is not a case count.',
              'readability': readability,
              'readability_limits': 'Ordinary group retains summary only; full same-named details were overwritten '
                                    'by Enteng. Draft pool form never opened. Faded/disabled/image/unparsed text '
                                    'is excluded. Other menus retain counts/no-low flags, not every positive color row.',
              'native_guard': 'Eight writer callers exercise assigned txid. Own fresh-tx review confirms OWNER/ADMIN two PASS IDs/eight calls with NULL at each entry; STAFF remains unexecuted after two preserved Sol fixture errors. See FRESH_TX_RESULT_REVIEW.json; no no-allocation or benchmark claim.',
              'race_qualification': '39 raw two-session/schedule PASS does not imply39 strict races. Barrier-only '
                                    'cases lack observed waits/PID trace; four new paging schedules have explicit '
                                    'commit/visibility outcomes. Preserve raw status and these limits.',
              'oracle_origin': 'WRITER_OR_R3_AUDITOR_REPRODUCTION; SOL_PREEXEC_CONTRACT_AND_DOCUMENT_ARITHMETIC_SEPARATE',
              'fixture_origin': 'WRITER_SYNTHETIC_DISPOSABLE',
              'old_r3_21_browser_INCOMPLETE': 'Preserved on b53; current663 candidate has57 ordinary browser PASS. '
                                                'Different product qualification, not relabel of old result.',
              'cp6_restored': True, 'advisor_gate': True, 'product_roots_clean_before_after': True,
              'feature_complete': False, 'audit_complete': False, 'production_go': False}
    (ROOT / 'CP17_RESULT_REVIEW.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('CP17 exact341 report/log rows reviewed; arithmetic,47-menu set and290 WIP ratios independently checked; transport1364 loopback; qualified scope only.')


if __name__ == '__main__':
    main()
