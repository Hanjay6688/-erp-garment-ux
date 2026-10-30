"""Read-only analysis of retained actual4d raw snapshots; never a runtime oracle.

All raw differences remain in the report. Timestamp parsing only identifies
same-instant serialization differences in historical evidence; no fixture row,
expected row, financial field or runtime equality is rewritten or filtered.
"""
from collections import Counter
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import argparse
import gzip
import json
import zipfile

HERE = Path(__file__).resolve().parent
ARCHIVE_BYTES = 165206613
ARCHIVE_SHA256 = 'e841f3026e2a7dac9f1ddfea013748572f14cd67ee9dcbbca47a303137469e14'
MOBILE = 'S03_B4_MOBILE390_636597efdddb46f4ae87be31dfe4bb60_FIRST_FAILURE.json'
LATER = 'S03_B4_ACCESS_370704F731DE4104BB8F34DEF123D25E_001_BEFORE_FULL_APP_OPEN_FULL_STATE.json.gz'
TABLES = dict(FG='erp.fg_stock_movements', current_HPP='erp.hpp_versions',
    HPP_history='erp.hpp_versions', HPP_components='erp.hpp_version_components',
    journal_headers='erp.journal_entries', journal_lines='erp.journal_lines',
    ordinary_pool_journal='erp.journal_entries')


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def raw_pin(value):
    return pin(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def same_instant(before, after):
    if not isinstance(before, str) or not isinstance(after, str):
        return False
    try:
        a, b = datetime.fromisoformat(before), datetime.fromisoformat(after)
    except ValueError:
        return False
    return (a.tzinfo is not None and b.tzinfo is not None and a == b
        and a.utcoffset() != b.utcoffset())


def scan(path):
    raw = path.read_bytes()
    if len(raw) != ARCHIVE_BYTES or sha256(raw).hexdigest() != ARCHIVE_SHA256:
        raise ValueError('S03_ORDINARY_EXACT_ACTUAL_4D_ARCHIVE_REQUIRED')
    with zipfile.ZipFile(path) as archive:
        if len(archive.infolist()) != 159 or archive.testzip() is not None:
            raise ValueError('S03_ORDINARY_ALL_159_CRC_MEMBERS_REQUIRED')
        first, packed = archive.read(MOBILE), archive.read(LATER)
    later = gzip.decompress(packed); fixture = json.loads(first)['fixture']
    state = json.loads(later); tables = state['all_rows']; facts = fixture['ordinary_before_native']
    report = {}
    for group, table in TABLES.items():
        old = [fixture[group]] if group == 'ordinary_pool_journal' else facts[group]
        all_rows = {row['id']: row for row in tables[table]}; changes = []; matched = []; numeric_representation = []
        for row in old:
            after = all_rows[row['id']]; matched.append(after)
            if row.keys() != after.keys():
                raise ValueError('S03_ORDINARY_RAW_COLUMNSET_DIFFERENT:' + group)
            for key in row:
                if row[key] != after[key]:
                    changes.append(dict(id=row['id'], column=key, before=row[key], after=after[key],
                        same_instant_different_offset=same_instant(row[key], after[key])))
                elif type(row[key]) in (int, float) and type(after[key]) in (int, float) and type(row[key]) is not type(after[key]):
                    numeric_representation.append(dict(id=row['id'], column=key,
                        first_JSON=json.dumps(row[key]), later_JSON=json.dumps(after[key]), equal_numeric_value=True))
        time_changes = [change for change in changes if change['same_instant_different_offset']]
        economic = [change for change in changes if not change['same_instant_different_offset']]
        report[group] = dict(table=table, compared_rows=len(old), compared_fields=sum(len(row) for row in old),
            original_rows=raw_pin(old), later_same_id_rows=raw_pin(matched),
            equal_value_fields=sum(len(row) for row in old) - len(changes),
            equal_numeric_values_with_different_JSON_representation=numeric_representation,
            raw_differences=changes, time_representation_differences=len(time_changes),
            time_columns=dict(Counter(change['column'] for change in time_changes)),
            non_time_differences=economic, other_field_values_equal=True,
            serialized_row_bytes_equal=(raw_pin(old) == raw_pin(matched)))
    po, lot = fixture['pos'][0], fixture['lots'][0]
    later_hpp = [row for row in tables['erp.hpp_versions'] if row['lot_id'] == lot]
    later_current = [row for row in later_hpp if row['is_current']]
    hpp_ids = {row['id'] for row in later_hpp}
    later_components = [row for row in tables['erp.hpp_version_components'] if row['hpp_version_id'] in hpp_ids]
    journal_ids = {row['journal_entry_id'] for row in tables['erp.journal_lines'] if row['po_id'] == po}
    later_headers = [row for row in tables['erp.journal_entries'] if row['id'] in journal_ids]
    later_lines = [row for row in tables['erp.journal_lines'] if row['journal_entry_id'] in journal_ids]
    additions = {}
    for name, current in (('HPP_history', later_hpp), ('HPP_components', later_components),
            ('journal_headers', later_headers), ('journal_lines', later_lines)):
        original = {row['id'] for row in facts[name]}
        additions[name] = dict(before=len(original), after=len(current),
            added_ids=sorted(row['id'] for row in current if row['id'] not in original),
            removed_ids=sorted(original - {row['id'] for row in current}))
    mappings = {row['mapping_key']: row['account_id'] for row in tables['erp.accounting_account_mappings']}
    gl = {key: sum((Decimal(str(row['debit'])) - Decimal(str(row['credit']))
        for row in tables['erp.journal_lines'] if row['po_id'] == po and row['account_id'] == mappings[key]), Decimal(0))
        for key in ('WIP', 'FG_INVENTORY', 'COGS')}
    readers = {}
    for signature in ('erp.validate_attendance_hpp_pool_v1(uuid)', 'erp.compute_po_hpp_gl_targets_v2620d(uuid)',
            'erp.compute_po_hpp_gl_book_v2620e(uuid)', 'erp.run_v267_financial_truth_checks()',
            'erp.run_v268_financial_report_checks()'):
        definition = state['all22']['functions'][signature][0]
        readers[signature] = dict(definition=pin(definition.encode()),
            timezone_lines=[line.strip() for line in definition.splitlines() if 'timezone' in line.lower()])
    return dict(contract='cp7.s03.ordinary-snapshot-actual4d-analysis.v1',
        classification='HISTORICAL_RAW_EVIDENCE_ANALYSIS_NOT_RUNTIME_NORMALIZATION_OR_ACCEPTANCE',
        archive=dict(**pin(raw), crc_members=159, run_id=41033738459, artifact_id=12969123916,
            library_file_id='libfile_3f178e36455c8191bb2e284c39775d0b'),
        members={MOBILE: pin(first), LATER: dict(compressed=pin(packed), uncompressed=pin(later))},
        groups=report, later_additions=additions,
        observer_reader_source_review=dict(actual_functions=readers,
            note='Only run_v268 declares function-scoped SET TimeZone UTC; the other four definitions have no TimeZone statements. Python native_call/fixture_journal_call/auth.actor/admin wrappers change authorization only. No additional session-TimeZone scope is introduced on fresh observe/valuation/cancellation paths.'),
        legitimate_ordinary_activation=dict(current_HPP_before=raw_pin(facts['current_HPP']),
            current_HPP_after=raw_pin(later_current), current_HPP_rows_before=len(facts['current_HPP']),
            current_HPP_rows_after=len(later_current), before_total_cost=str(sum(Decimal(str(row['total_cost'])) for row in facts['current_HPP'])),
            after_total_cost=str(sum(Decimal(str(row['total_cost'])) for row in later_current)),
            GL_before=facts['GL'], GL_after={key: str(value) for key, value in gl.items()},
            full_FG_or_HPP_equality_claim=False,
            explanation='The later census follows Native ordinary pool activation: QC_GOOD valuation cache and current-HPP pointer/cost plus appended HPP/journal history legitimately differ. Every raw difference and addition is retained above.'),
        untouched_runtime_oracles=True, dropped_columns=[], actual_new_browser_credit=0,
        independent_acceptance=False, production_go=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('archive', type=Path)
    args = parser.parse_args(); result = scan(args.archive)
    target = HERE / 'evidence/ORDINARY_SNAPSHOT_ACTUAL4D_SCAN.json'
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({name: dict(rows=value['compared_rows'], time_differences=value['time_representation_differences'],
        non_time_differences=len(value['non_time_differences'])) for name, value in result['groups'].items()}))
