from hashlib import sha256
import json
def check(repo,here):
    rules=json.loads((here/'ORIGIN.json').read_bytes())
    for name,rule in rules.items():
        raw=(repo/rule['path']).read_bytes();assert sha256(raw).hexdigest()==rule['sha256']
        expected=raw.decode()
        for change in rule['changes']:
            assert expected.count(change['old'])==change['count'];expected=expected.replace(change['old'],change['new'])
        assert (here/name).read_text()==expected,name
    old=(repo/'scripts/current-frozen-finance-stage-profile/runner.py').read_text()
    exact=old[old.index('def functions('):old.index('def exercise(')]
    current=(here/'measurements.py').read_text()
    assert current[current.index('def functions('):current.index('def exercise(')]==exact
    return dict(probe_and_full_restoration_exact_derivation=True,measurement_savepoint_and_outer_rollback_unchanged=True,
        source_B_and_product_SQL_unchanged=True,diagnostic_only=True)
