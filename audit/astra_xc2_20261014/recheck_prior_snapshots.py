"""Re-read existing Astra Original. No ERP transaction or comparison oracle changes."""
from pathlib import Path
import hashlib, json
root = Path(__file__).resolve().parent
raw = (root / 'evidence/prior/ASTRA_SUPPLIER_BOUNDARY_OBSERVATIONS.json').read_bytes()
review = json.loads((root / 'PRIOR_SUPPLIER_BOUNDARY_REVIEW.json').read_text())
assert hashlib.sha256(raw).hexdigest() == review['source_sha256']
observations = json.loads(raw)['observations']
assert len(observations) == 26
rows = []
for entry in review['comparisons']:
    # The archived review uses Python list indexes, starting at zero.
    a = observations[entry['before_observation']]
    b = observations[entry['after_observation']]
    kind = 'public_state' if entry['comparison'].endswith('public') else 'boundary'
    assert a['kind'] == b['kind'] == kind
    assert a['snapshot'] == b['snapshot']
    rows.append(dict(comparison=entry['comparison'], before_index=entry['before_observation'],
                     after_index=entry['after_observation'], kind=kind, raw_equal=True))
result = dict(evidence_origin='REUSED_ASTRA_ORIGINAL', original_sha256=review['source_sha256'],
              original_bytes=len(raw), observations=26, index_base=0, comparisons=rows,
              root_cause_of_two_other_failed_runs='UNDETERMINED',
              local_reader_correction='AX2-T01: initial local reader treated stored indexes as one-based; original bytes were never changed and no ERP cases were repeated.')
(root / 'PRIOR_SNAPSHOT_RECHECK.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(observations=26, equal_comparisons=len(rows), original_sha256=review['source_sha256'])))
