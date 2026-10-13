"""Run the candidate's unchanged writer probe. No monkeypatch or comparator replacement."""
from pathlib import Path
import sys,runpy
product=Path.cwd().parent/'auditor'
probe=sys.argv[1]
assert '/' not in probe and probe.endswith('.py')
sys.path.insert(0,str(product/'scripts'))
sys.argv=[str(product/'scripts'/probe),*sys.argv[2:]]
runpy.run_path(sys.argv[0],run_name='__main__')
