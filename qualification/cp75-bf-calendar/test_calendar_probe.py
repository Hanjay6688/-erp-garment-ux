import copy
import unittest
from datetime import date, timedelta
from calendar_probe import SOURCE_HEAD, SOURCE_JOB, SOURCE_RUN, days, evaluate, names, source_window


class CalendarTest(unittest.TestCase):
    def setUp(self):
        self.anchor = date(2026, 11, 20)
        self.job = {"id": SOURCE_JOB, "run_id": SOURCE_RUN, "head_sha": SOURCE_HEAD,
                    "conclusion": "success", "steps": [
                        {"name": "Start disposable database", "conclusion": "success",
                         "started_at": "2026-11-20T19:18:52Z", "completed_at": "2026-11-20T19:20:08Z"}]}
        children = [{"schema": "realtime", "name": name, "kind": "r", "is_partition": True,
                     "bound": f"FOR VALUES FROM ('{d} 00:00:00') TO ('{d+timedelta(days=1)} 00:00:00')"}
                    for d, name in zip(days(self.anchor), names(self.anchor), strict=True)]
        self.obs = {"postmaster_day_utc": "2026-11-21", "children": children, "detached_daily_tables": []}

    def test_restore_next_day_preserves_source_window(self):
        result = evaluate(self.obs, source_window(self.job))
        self.assertTrue(result["matches_source_names_and_bounds"])
        self.assertFalse(result["matches_restored_postmaster_names"])

    def test_same_day_and_later_restart(self):
        for day, is_live in [("2026-11-20", True), ("2027-01-05", False)]:
            with self.subTest(day=day):
                result = evaluate(dict(self.obs, postmaster_day_utc=day), source_window(self.job))
                self.assertTrue(result["matches_source_names_and_bounds"])
                self.assertEqual(result["matches_restored_postmaster_names"], is_live)

    def test_missing_extra_wrong_bounds_schema_and_detached(self):
        for mutation in ["missing", "extra", "bounds", "schema", "detached", "not_partition"]:
            o = copy.deepcopy(self.obs)
            if mutation == "missing": o["children"].pop()
            if mutation == "extra": o["children"].append(o["children"][-1])
            if mutation == "bounds": o["children"][0]["bound"] = "DEFAULT"
            if mutation == "schema": o["children"][0]["schema"] = "public"
            if mutation == "detached": o["detached_daily_tables"].append("messages_2026_11_18")
            if mutation == "not_partition": o["children"][0]["is_partition"] = False
            with self.subTest(mutation=mutation):
                self.assertFalse(evaluate(o, source_window(self.job))["matches_source_names_and_bounds"])

    def test_refuse_different_origin_or_ambiguous_source_day(self):
        for job in [dict(self.job, id=1), dict(self.job, head_sha="0"*40),
                    dict(self.job, steps=[dict(self.job["steps"][0], completed_at="2026-11-21T00:01:00Z")])]:
            with self.assertRaises(ValueError):
                source_window(job)
