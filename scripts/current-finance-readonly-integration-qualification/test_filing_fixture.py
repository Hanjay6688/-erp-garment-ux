import unittest
import filing_fixture as fixture


class FilingFixtureBoundary(unittest.TestCase):
    def test_only_three_filing_cases_are_prepared(self):
        calls = []
        def original():
            calls.append('case')
            return {'status': 'PASS', 'expected_money': '123.45'}
        def prepare(cur, today):
            calls.append('prepare')
            return {'status': 'PASS', 'pools': ['old-seed-only']}
        source = [(key, original) for key in sorted(fixture.FILING_IDS)] + [('OTHER_CASE', original)]
        wrapped = fixture.wrap(source, None, None, prepare)
        self.assertIs(wrapped[-1][1], original)
        result = wrapped[0][1]()
        self.assertEqual(calls, ['prepare', 'case'])
        self.assertEqual(result['expected_money'], '123.45')
        self.assertEqual(result['fixture_preparation']['pools'], ['old-seed-only'])

    def test_incomplete_preparation_does_not_run_original(self):
        def forbidden():
            self.fail('case ran with incomplete HPP fixture')
        with self.assertRaisesRegex(ValueError, 'FIXTURE_NOT_READY'):
            fixture.prepared(forbidden, None, None, lambda *_: {'status': 'INCOMPLETE'})

    def test_original_oracle_failure_propagates(self):
        def failed():
            raise AssertionError('original monetary oracle')
        with self.assertRaisesRegex(AssertionError, 'original monetary oracle'):
            fixture.prepared(failed, None, None, lambda *_: {'status': 'PASS'})

    def test_original_incomplete_is_never_promoted(self):
        result = fixture.prepared(lambda: {'status': 'INCOMPLETE', 'error': 'original failure'},
                                  None, None, lambda *_: {'status': 'PASS'})
        self.assertEqual(result['status'], 'INCOMPLETE')
        self.assertEqual(result['error'], 'original failure')


if __name__ == '__main__':
    unittest.main()
