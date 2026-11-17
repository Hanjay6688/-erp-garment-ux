"""Use the retained S05 preimage for ordinary Auth on the owning database."""

from contextlib import chdir
import json

from scope_witness import capture


FIXTURE = 's05/fixture.py'
EXPECTED = 's05/EXPECTED.json'
PINS = {
    FIXTURE: 'aa0550a36e0cb5f73b91641278ff8edf27dac52428911eefb6300a406c96dd35',
    EXPECTED: 'e24ab647f081ec3bba57fa5e4177a892290a0b85efbfd0e7caeb7e18cb57c7c9',
}


def bind(assets, candidate, *, owner, plan, catalogue_raw, relations, trusted_connection, identity_sql):
    for name, expected in PINS.items():
        owner.exact(assets / name, expected)
    owner.require(owner.pin(catalogue_raw) == owner.CATALOGUE_PIN, 'GLOBAL_AUTH_S05_EXACT_FULL25_REQUIRED')
    with chdir(candidate), owner.import_paths(candidate / 'scripts'):
        fixture = owner.load('global_auth_exact_ordinary_S05_fixture', assets / FIXTURE)
    parent = json.loads(catalogue_raw)
    started = False

    def prepare(*, attempt, verify, today):
        nonlocal started
        plan.check_registry(attempt)
        owner.require(not started and attempt.phase == 'ACTIVE', 'GLOBAL_AUTH_S05_ONE_OWNING_FIXTURE_REQUIRED')
        tag = attempt.attempt.replace('-', '')[-10:]
        bound = fixture.Fixture(tag=tag, parent_catalogue=parent, verify_global=verify)
        started = True

        def sample(cur):
            return capture(cur, expected_database='cp6_rollback', mode='transaction')

        with trusted_connection() as conn, conn.cursor() as cur:
            try:
                owner.require(cur.execute(identity_sql).fetchone() == attempt.app,
                              'GLOBAL_AUTH_S05_EXACT_APPLICATION_REQUIRED')
                bound.begin(cur)
                before = sample(cur)
                data = bound.prepare_report(cur, lambda a, b: fixture.compare_attempts(a, b, relations))
                owner.require(data['dates']['runtime_WIB_day'] == today.isoformat(), 'GLOBAL_AUTH_S05_DATED_FIXTURE_REQUIRED')
                staged = sample(cur)
                proof = fixture.note_write_evidence(before, staged, relations)
                # After COMMIT, inspect the recost table on its original backend and release that backend.
                conn.commit()
                removed = fixture.observe_temp_after_terminal(cur, staged)
                reading = fixture.report_result(cur, data, data['master'])
                return reading, dict(write_scope=proof, temporary=removed, dates=data['dates'])
            finally:
                conn.rollback()

    return prepare
