"""Qualification-only full-row observation in one explicitly recorded timezone.

The first report did not retain failed before/after values. UTC is a hypothesis
correction to a session-dependent observer, not a claim about that failed row.
No product function, business assertion, row, timestamp or nested JSON is edited.
"""
from hashlib import sha256
import json

class CaptureObserver:
    def __init__(self,native):
        self.native=native;self.original=native.stored_capture;self.observations=[]

    def read(self,cur,cid):
        raw=self.original(cur,cid)
        zone=cur.execute('show TimeZone').fetchone()[0]
        columns={r[0]for r in cur.execute("select attname from pg_attribute where attrelid='cp7_finance_capture.captures'::regclass and attnum>0 and not attisdropped and atttypid='timestamptz'::regtype").fetchall()}
        cur.execute("select set_config('TimeZone','UTC',true)")
        try:canonical=self.original(cur,cid)
        finally:cur.execute("select set_config('TimeZone',%s,true)",(zone,))
        assert cur.execute('show TimeZone').fetchone()[0]==zone
        changed=sorted(k for k in set(raw)|set(canonical)if raw.get(k)!=canonical.get(k))
        assert set(raw)==set(canonical)and set(changed)<=columns,('CAPTURE_NON_TIMESTAMP_RENDERING_CHANGED',changed)
        digest=lambda row:sha256(json.dumps(row,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.observations.append(dict(capture_id=str(cid),session_timezone=zone,
            raw_full_row=raw,UTC_full_row=canonical,raw_sha256=digest(raw),UTC_sha256=digest(canonical),
            rendered_timestamp_fields=changed,all_fields_retained=len(canonical),session_timezone_restored=True))
        return canonical

    def install(self):
        assert self.native.stored_capture is self.original
        self.native.stored_capture=self.read

    def restore(self):self.native.stored_capture=self.original
