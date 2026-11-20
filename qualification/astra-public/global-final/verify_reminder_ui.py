"""Run Astra's browser observations on the sealed disposable Global and preserve one receipt per case."""
import hashlib
import importlib.util
import json
import os
import subprocess
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

PIN = "486d344e0ce47d2b184e2a7bfccf2a927424d184"
TREE = "77942cec7dfc18b96c820f79dfdc9b90bee7ade0"
ROOT = Path(os.environ["GITHUB_WORKSPACE"])
TRANSPORT = ROOT / "rig/qualification/cp75-reminders"
OUT = Path(os.environ["WRITER_RESULTS"])
OUT.mkdir(parents=True, exist_ok=True)
def oid(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
pins = {"check.py":"8e6230a7e636aff92ba2b527afba88d4225b1db7","browser.cjs":"4e832e0bb87bcc95fe00893640194a396b3b4672","candidate.json":"bdd314ca953940005b26d89b205944df10aab1eb","ui.patch":"1b5c05fead938791b43fb7f24d1e21d7d7a193d1"}
assert all(oid(TRANSPORT/name)==value for name,value in pins.items())
spec=importlib.util.spec_from_file_location("fixture",TRANSPORT/"check.py")
fixture=importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
assert fixture.RELEASE["product"]==PIN and fixture.RELEASE["tree"]==TREE
fixture.install()
app=fixture.APP
subprocess.run(["npm","ci","--no-audit","--no-fund"],cwd=app,check=True)
# Reuse the verified transport/bootstrap only. All scenarios after launching Chrome are auditor-owned.
source=(TRANSPORT/"browser.cjs").read_text().split("  const browser=await chromium.launch",1)
assert len(source)==2
cases=Path(__file__).with_name("verify_reminder_browser.json")
driver=OUT/"independent.cjs"
driver.write_text(source[0]+json.loads(cases.read_text()))
with ThreadingHTTPServer(("127.0.0.1",0),fixture.Adapter) as server:
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        subprocess.run(["node",str(driver),str(app),str(OUT),f"http://127.0.0.1:{server.server_address[1]}"],cwd=app,check=True)
    finally:
        server.shutdown()
        thread.join()
rows=json.loads((OUT/"browser.json").read_bytes())
assert len({i["id"] for i in rows})==len(rows)==16
assert all(i["outcome"] in {"PASS","FAIL"} for i in rows)
fixture.store("verdict",dict(candidate=PIN,tree=TREE,run=os.environ["GITHUB_RUN_ID"],head=os.environ["GITHUB_SHA"],
   results=[{"id":r["id"],"outcome":r["outcome"]} for r in rows],production_go=False))
if any(r["outcome"]=="FAIL" for r in rows):
    raise SystemExit("One or more product expectations failed, see per-case observations")
