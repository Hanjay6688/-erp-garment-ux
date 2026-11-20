"""Exercise the first CP7 installation on the actual independently delivered BF archive."""
import hashlib
import json
import os
from pathlib import Path
import psycopg
import cp6_g01_fingerprint as fingerprint
import cp7_current_installation as entry

OUT=Path(os.environ["RUNNER_TEMP"])/"cp75-original-observations"
def mark():
    with psycopg.connect(host=os.environ["PGHOST"],dbname="cp6_rollback",user="supabase_admin") as c:
        c.execute("set local search_path=pg_catalog,public")
        rows=c.execute(fingerprint.SUMMARY).fetchone()[0]
        return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()
if __name__=="__main__":
    pin=json.loads((OUT/"clean-opened.json").read_text())
    assert pin["origin_run"]==44800849536 and os.environ["PGHOST"].endswith("/clean-socket")
    with psycopg.connect(host=os.environ["PGHOST"],dbname="cp6_rollback",user="supabase_admin") as c,c.cursor() as q:
        state=entry.install(q)
        proof=entry.verify(q,state)
    observed=mark()
    seal="88aaa699d6af770e1481c3e0cc1881dc45749fb881a0b12b1996885f770884d2"
    assert observed==seal,(observed,seal)
    (OUT/"clean-first-release.json").write_text(json.dumps({"source_run":pin["origin_run"],"before":pin["catalogue"],
        "first_release_catalogue":observed,"receipt":proof,"global_parity":False,"production_go":False},indent=2,default=str)+"\n")
