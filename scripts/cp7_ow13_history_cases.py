"""D17-14 OW13b: complete factory history, with the retained PL5 controls.

Only the old 200-candidate refusal is superseded by the owner's explicit
requirement. The other nineteen controls and the old source file are retained.
Scale clones are labelled SYNTHETIC; their proofs still use the real prover.
"""
import cp7_pl5_history_yield_cases as retained

OLD_LIMIT = 'PL5H_LIMIT_200_UNDER_8S'
COMPLETE = 'OW13B_COMPLETE_HISTORY_200_201_501_UNDER_8S'
CONTRACT = 'cp7.ow13b.complete-history.v1'
IDS = {kind: [COMPLETE if key == OLD_LIMIT else key for key in keys]
       for kind, keys in retained.IDS.items()}
REQUIRED = dict(retained.REQUIRED)
EXPECTED = retained.EXPECTED
FUNCTIONS = retained.FUNCTIONS
SIGNATURES = retained.SIGNATURES
PRIVATE = retained.PRIVATE
races = retained.races
http_cases = retained.http_cases


def cases(cur, today):
    def complete_history():
        owner = retained.actor(cur)
        item = retained.product(cur, 'ow13b')
        production = retained.Production(cur, today)
        original = production.group(item, 40, 37)
        # SYNTHETIC scale fixture only. Every clone is checked by the ordinary
        # batch_verdict/store_proofs path, never by inserting an accepted proof.
        clones = retained.clone(cur, original['group'], 199,
                                'OW13b SYNTHETIC complete history first 200')
        groups = [original['group'], *clones]
        assert retained.prove(cur, groups) == 200
        retained.save(cur, retained.payload(), owner)
        timings = {}

        def check(count):
            actual, elapsed = retained.history(cur, item['target'], item['model'], owner)
            k = retained.available(actual, 'PRODUCT_SIZE', count, count * 40, count * 37)
            assert elapsed < 8000, elapsed
            assert {str(row['group_id']) for row in actual['proofs']} == set(map(str, groups)), actual
            assert len(actual['proofs']) == count
            assert actual['lower_bound_permille'] == str(retained.wilson(count * 37, count * 40))
            timings[str(count)] = dict(milliseconds=elapsed, groups=count,
                                      cut_pcs=count * 40, good_pcs=count * 37,
                                      lower_bound_permille=k, all_proof_ids_matched=True)

        check(200)
        extra = retained.clone(cur, clones[-1], 1, 'OW13b SYNTHETIC group 201')
        assert retained.prove(cur, extra) == 1
        groups.extend(extra)
        check(201)
        more = retained.clone(cur, extra[0], 300, 'OW13b SYNTHETIC groups 202 through 501')
        assert retained.prove(cur, more) == 300
        groups.extend(more)
        check(501)
        # A second call reads, rather than adding/rewriting proof history.
        before = retained.proofs_of(cur, groups)
        check(501)
        assert retained.proofs_of(cur, groups) == before
        return dict(status='PASS', observations=timings, synthetic_scale_clones=500,
                    native_original_finished_through_ordinary_writers=True,
                    all_proofs_from_unchanged_prover=True, ordinary_statement_timeout='8s',
                    no_source_truncation=True, no_proof_writes_during_history_read=True,
                    limits_raised=False)

    old = retained.cases(cur, today)
    assert [key for key, _ in old] == retained.IDS['native']
    result = [(COMPLETE, complete_history) if key == OLD_LIMIT else (key, case)
              for key, case in old]
    assert [key for key, _ in result] == IDS['native']
    return result
