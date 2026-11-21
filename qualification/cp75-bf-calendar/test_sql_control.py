"""Optional PostgreSQL integration control, invoked by the short Writer workflow."""
import json
import os
from pathlib import Path
import subprocess
import unittest
from datetime import date, timedelta
from calendar_probe import days, evaluate, names


@unittest.skipUnless(os.environ.get("CP75_SQL_CONTROL")=="1", "disposable PostgreSQL control only")
class SQLControl(unittest.TestCase):
    def test_attached_then_detached(self):
        def sql(text):
            return subprocess.check_output(["psql","-XAtq","-v","ON_ERROR_STOP=1","-c",text], text=True)
        source = date(2026,11,20)
        sql("CREATE SCHEMA realtime; CREATE TABLE realtime.messages (inserted_at timestamp) PARTITION BY RANGE(inserted_at)")
        for name, day in zip(names(source), days(source), strict=True):
            sql(f"CREATE TABLE realtime.{name} PARTITION OF realtime.messages FOR VALUES FROM ('{day}') TO ('{day+timedelta(days=1)}')")
        reader = Path(__file__).with_name("observe.sql").read_text()
        def read():
            observed = json.loads(sql(reader))
            self.assertEqual(observed["read_only"],"on")
            return evaluate(observed,{"utc_day": source.isoformat()})
        good = read()
        self.assertTrue(good["matches_source_names_and_bounds"])
        sql("ALTER TABLE realtime.messages DETACH PARTITION realtime.messages_2026_11_20")
        changed = read()
        self.assertFalse(changed["matches_source_names_and_bounds"])
        self.assertEqual(changed["postgresql"]["detached_daily_tables"],["messages_2026_11_20"])
        target = Path(os.environ["RUNNER_TEMP"])/"calendar-controls/sql-control.json"
        target.write_text(json.dumps({"synthetic_control": True, "attached": good, "detached":changed}, indent=2)+"\n")
