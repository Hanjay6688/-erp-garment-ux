"""Execute a frozen candidate probe with first-result-only audit retry policy."""
from pathlib import Path
import json
import runpy
import sys
import hashlib

ROOT=Path(__file__).resolve().parent
PRODUCT=ROOT.parents[2]/'auditor'
name=sys.argv[1]
assert Path(name).name==name and name.endswith('.py')
m=json.loads((ROOT/'AFFECTED_REGRESSION_PREEXECUTION_MANIFEST.json').read_text())
assert name in m['probe_sha256']
source=PRODUCT/'scripts'/name
assert hashlib.sha256(source.read_bytes()).hexdigest()==m['probe_sha256'][name]
sys.path.insert(0,str(PRODUCT/'scripts'))
import cp6_auditor_business_day as day
from cp17_once import first_only
day.with_retry=first_only
sys.argv=[str(source)]
runpy.run_path(str(source),run_name='__main__')
