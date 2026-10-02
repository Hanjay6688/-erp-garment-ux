"""Replay the real midnight-WIB report-oracle failure without a database."""
import unittest
from cp7_native_fixture_window import window


class NativeWindowRegression(unittest.TestCase):
    def test_sale_before_midnight_and_return_after_midnight_are_both_included(self):
        q = window('2026-10-03', '2026-10-02T17:01:00+00:00',
                   '2026-10-02T16:53:00+00:00', '2026-10-02T17:00:30+00:00')
        self.assertEqual(q, {'from': '2026-10-02', 'to': '2026-10-03', 'as_of': '2026-10-03'})

    def test_startup_day_before_midnight_does_not_exclude_later_effects(self):
        q = window('2026-10-02', '2026-10-02T17:01:00+00:00', '2026-10-02T23:53:00+07:00')
        self.assertEqual(q['to'], '2026-10-03')
        self.assertEqual(q['from'], '2026-10-02')

    def test_caller_offsets_do_not_change_erp_dates(self):
        self.assertEqual(window('2026-10-03', '2026-10-02T10:01:00-07:00',
                                '2026-10-02T09:53:00-07:00'),
                         window('2026-10-03', '2026-10-03T00:01:00+07:00',
                                '2026-10-02T23:53:00+07:00'))

    def test_future_physical_event_is_not_hidden_by_widening_the_window(self):
        with self.assertRaisesRegex(AssertionError, 'FUTURE'):
            window('2026-10-03', '2026-10-03T00:01:00+07:00', '2026-10-03T00:02:00+07:00')


if __name__ == '__main__':
    unittest.main()
