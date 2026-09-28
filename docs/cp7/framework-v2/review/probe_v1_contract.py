"""Independent offline review of the CP7 preparation contract, never ERP execution."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'history/v1'
schema = json.loads((PACKAGE / 'contracts/analysis.schema.json').read_text())
example = json.loads((PACKAGE / 'contracts/analysis.example.json').read_text())
validator = Draft202012Validator(schema, format_checker=FormatChecker())
rows = []

def probe(name, change, expected_schema_acceptance, meaning):
    sample = deepcopy(example)
    change(sample)
    errors = sorted(validator.iter_errors(sample), key=lambda e: str(list(e.path)))
    accepted = not errors
    rows.append({
        'id': name,
        'schema_accepted': accepted,
        'review_observation_reproduced': accepted == expected_schema_acceptance,
        'meaning': meaning,
        'errors': [{'path': list(e.path), 'message': e.message} for e in errors[:2]],
    })

probe('CONTROL-original', lambda x: None, True, 'The supplied complete example is valid.')
probe('CONTROL-NaN', lambda x: x['recommendations'][0]['actual_fg'].update(value='NaN'), False,
      'Malformed numeric text is correctly rejected.')
probe('C01-fractional-PCS', lambda x: x['recommendations'][0]['actual_fg'].update(value='0.5'), True,
      'COUNT/PCS integrality is stated in prose but not enforced by this shape schema.')
probe('C02-over-allocation', lambda x: x['sources'][1]['allocated'].update(value='21'), True,
      'Allocated21 exceeds physical/eligible20; a runtime semantic validator must reject it.')
probe('C03-incomplete-capture', lambda x: x['snapshot'].update(capture_complete=False), True,
      'COMPLETE with incomplete capture passes shape validation; semantic gate is necessary.')
probe('C04-negative-lost-sales', lambda x: x['timeline'][0].update(mode='LOST_SALES', balance_end='-2'), True,
      'LOST_SALES retaining negative inventory as backlog passes shape validation.')
probe('C05-unknown-demand', lambda x: x['timeline'][0].update(demand={
      'state': 'UNKNOWN', 'unit': 'PCS', 'reason': 'AVAILABILITY_UNKNOWN', 'refs': []}), False,
      'Typed UNKNOWN cannot currently be represented in timeline.demand.')
probe('C06-unmet-demand-field', lambda x: x['timeline'][0].update(unmet_demand='2'), False,
      'The timeline prohibits an explicit unmet-demand output; prose requires that distinction.')
probe('C07-source-target-edge', lambda x: x.update(allocations=[{
      'source_key': x['sources'][1]['source_key'],
      'target_key': x['recommendations'][0]['target']['key'],
      'size_id': '30', 'input_qty': '10', 'projected_output_qty': '10',
      'match': 'CANDIDATE_MATCH'}]), False,
      'No typed allocation-edge collection exists in AnalysisResult; actions only contain ID lists.')

# A daily summary loses when the shortage occurred. These are separate synthetic
# contracts, not an ERP oracle accepted by the owner. Amounts are in exact PCS.
def intraday(events):
    balance = 0
    earliest_gap = None
    for time, delta in events:
        balance += delta
        if balance < 0 and earliest_gap is None:
            earliest_gap = time
    return {'end_balance': balance, 'earliest_gap': earliest_gap}

time_examples = {
    'morning_demand_evening_supply': intraday([('08:00', -5), ('16:00', 5)]),
    'morning_supply_evening_demand': intraday([('08:00', 5), ('16:00', -5)]),
    'daily_summary_in_both': {'demand': 5, 'supply': 5, 'balance_end': 0},
    'conclusion': 'Same daily totals do not prove absence of an intraday gap; output needs timing evidence or an explicit conservative timing convention.',
}

edges = {
    'allocation_1': {'S1->A': 10, 'S1->B': 0, 'S2->A': 0, 'S2->B': 10},
    'allocation_2': {'S1->A': 0, 'S1->B': 10, 'S2->A': 10, 'S2->B': 0},
    'same_marginal_totals': {'S1': 10, 'S2': 10, 'A': 10, 'B': 10},
    'conclusion': 'Source totals and target totals cannot reconstruct source-to-target matching, allocation, or provenance.',
}

manifest = {
    'review_scope': 'FRAMEWORK_AND_OFFLINE_SCHEMA_ONLY',
    'erp_runtime_tests': 'NOT_RUN',
    'framework_version': 'CP7-BACKBONE-20260928-v1',
    'inputs_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in [ROOT / 'history/v1/CP7_Framework_Lengkap_20260928.md',
                                PACKAGE / 'contracts/analysis.schema.json',
                                PACKAGE / 'contracts/backbone.ts']},
    'probe_count': len(rows),
    'all_review_observations_reproduced': all(r['review_observation_reproduced'] for r in rows),
    'caution': 'Schema acceptance is not proof an ERP implementation accepts a bad transaction. The package is proposed, and P01 is explicitly responsible for final contracts. The shipped semantic checks cover only its original example; these mutations do not rerun that example checksum.',
    'probes': rows,
    'allocation_counterexample': edges,
    'intraday_counterexample': time_examples,
}
out = ROOT / 'review/V1_PROBE_REPLAY.json'
out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: manifest[k] for k in ['review_scope', 'erp_runtime_tests', 'probe_count', 'all_review_observations_reproduced']}, ensure_ascii=False))
for row in rows:
    print(row['id'], 'SCHEMA_ACCEPTS' if row['schema_accepted'] else 'SCHEMA_REJECTS')
