"""Check the ordinary Auth paths against actual Full25 and the 461-relation review."""

from argparse import ArgumentParser
from contextlib import chdir
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile


CATALOGUE = 'ecf858d67f43c0967cfe6f38c51338dea64331ef6c0d1264786a8967f856e2a4'
SCOPE = '9a8374a4e563cf99591b1b7d4dfbc845ea787a8e9801355213945a07b2da13f1'
CORE = '7a98648ee70dc193c378ac46788073262da53883b71e7985ef62e9c09d6d475c'
CACHE = 'df1618772fa052ceb6bad74b563f2b0ddee27e39876c1e3bb241dd6be8b7b421'
SNAPSHOT = 'scripts/current-global-first-snapshot-preparation/REVIEWED_READER_IMAGES.json'
READER_IMAGES = 'ea51351de5f00b7e28107e177800edcbc34a4e7f68644d2b23c49d442b71ad19'
S05 = 'public.erp_cp7_get_accessory_standard_report_v1(date,date,uuid,uuid,text,integer,integer)'
ACL = 'erp.app_role_permissions'
SEQ = 'erp.audit_logs_id_seq'


def exact(raw, expected):
    if sha256(raw).hexdigest() != expected:
        raise ValueError('GLOBAL_AUTH_SCOPE_EXACT_RETAINED_SOURCE_REQUIRED:' + expected)
    return raw


def trace(reach, name, roots, direct, scope):
    observed = reach.trace(name, roots, direct)
    written = sorted({table for table, _ in observed['events']})
    outside = sorted(set(written) - scope)
    if outside or observed['unsupported_writes']:
        raise ValueError('GLOBAL_AUTH_SCOPE_OUTSIDE_OR_UNSUPPORTED_PERSISTENT_WRITES:' + name)
    return dict(roots=roots, relations=written, writes=len(observed['events']), routines=len(observed['routines']),
                FK_triggers=len(observed['fk_observations']), unresolved_parse=observed['parse_or_dynamic_open'],
                unbound_qualified_calls=[call for call in observed['unbound_calls']
                                         if '.' in call and not call.startswith('pg_catalog.')],
                catalogue_operators=[call for call in observed['unbound_calls'] if call.startswith('pg_catalog.')],
                outside_relations=outside)


def check(candidate, archive, proposed, parser_runtime, census):
    from global_scope import PGCRYPTO
    import pglast
    import review_relations as review

    assert pglast.__version__ == 'v7.20' and pglast.get_postgresql_version() == (17, 7)

    with ZipFile(archive) as bundle:
        raw = exact(bundle.read('SKU_GLOBAL_PARENT_ACTUAL_FULL25.json'), CATALOGUE)
    rows = review.indexed(json.loads(raw))
    scope = set(json.loads(exact(proposed.read_bytes(), SCOPE))['proposed_relations'])
    core = json.loads(exact((candidate / 'scripts/cp7_global_nonpo_envelope/INSTALL_PLAN.json').read_bytes(), CORE))
    images = json.loads(exact((candidate / SNAPSHOT).read_bytes(), READER_IMAGES))
    cache, _ = review.trusted_cache(review.HERE / review.CACHE, CACHE)
    definitions, sources, _, _, _ = review.cached_planned(cache, rows, core)
    for name, row in (images['new_rows'] | images['new_helpers']).items():
        if definitions.get(name) != (row[0], row[2]):
            raise ValueError('GLOBAL_AUTH_SCOPE_LATEST_READER_SOURCE_CHANGED:' + name)
    parser_input = review.INTAKE / 'parser-inputs/scan_saved_writer_census.py'
    with chdir(candidate), review.intake.source_fence(candidate) as fence, review.intake.frozen_review():
        from review_writer_delta import parser_for, retained_facts

        tracer, _ = review.exact_tracer(review.intake.profile_reader())
        parser = review.CachedParser(parser_for(parser_input, parser_runtime), cache['body_cache'])
        facts = tracer.Facts(definitions, retained_facts(census), parser, rows)
        reach = tracer.Reach(rows, core, facts)
        routes = {
            'D1': (tracer.ROOTS['D1'], ()),
            'E': (tracer.ROOTS['E'], ()),
            'S05_REPORT': ((S05,), ()),
            'ACCESS': (('public.erp_get_my_access_v1()',), ()),
            'ACTOR': ((), (('erp.app_users', 'INSERT', 'Exact Auth login mapping'),)),
            'PERMISSION': ((), ((ACL, 'DELETE', 'Exact ADMIN mapping removed'),
                                (ACL, 'INSERT', 'Exact ADMIN mapping restored'))),
        }
        observed = {name: trace(reach, name, roots, direct, scope) for name, (roots, direct) in routes.items()}
        for name in ('S05_REPORT', 'ACCESS', 'ACTOR', 'PERMISSION'):
            assert not observed[name]['unresolved_parse'], (name, observed[name]['unresolved_parse'])
            assert not observed[name]['unbound_qualified_calls'], (name, observed[name]['unbound_qualified_calls'])
        for name in ('D1', 'E'):
            open_routines = observed[name]['unresolved_parse']
            assert set(open_routines) == set(PGCRYPTO) and set(map(tuple, open_routines.values())) == {('opaque_language',)}
            assert not observed[name]['unbound_qualified_calls']
            for signature, symbol in PGCRYPTO.items():
                definition, language = definitions[signature]
                assert language == 'c' and f"AS '$libdir/pgcrypto', $function${symbol}$function$\n" in definition
        assert observed['S05_REPORT']['writes'] == observed['ACCESS']['writes'] == 0
        assert observed['ACTOR']['relations'] == ['erp.app_users', 'erp.audit_logs']
        assert observed['PERMISSION']['relations'] == [ACL]
        assert rows['relations'][SEQ][1] == 'S'
        view = rows['relations']['public.v_erp_my_profile']
        assert view[1] == 'v'
    assert len(scope) == 461 and not fence['attempts'] and not fence['network_nonGit_attempts']
    before = set().union(*(entry['relations'] for entry in observed.values()))
    return dict(status='GLOBAL_ORDINARY_AUTH_SOURCE_RELATION_REVIEW_VERIFIED', candidate_relations=len(scope),
                combined_write_relation_names=len(before), source_pins=dict(full25=CATALOGUE, scope=SCOPE, core=CORE,
                reader_images=READER_IMAGES, cache=CACHE, retained_plan=sources['installation_plan']),
                routes=observed, profile_view='public.v_erp_my_profile',
                separate_application_sequence=SEQ, issuer_database='postgres',
                application_database='cp6_rollback', source_fence=fence, actual_SQL_executed=0,
                actual_Auth_cases=0, complete_input_review=False, production_go=False)


def main():
    parser = ArgumentParser(description=__doc__)
    for name in ('candidate', 'archive', 'proposed', 'parser-runtime', 'census'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    proof = check(*(getattr(args, name).resolve() for name in ('candidate', 'archive', 'proposed', 'parser_runtime', 'census')))
    print(json.dumps(proof, indent=2))


if __name__ == '__main__':
    main()
