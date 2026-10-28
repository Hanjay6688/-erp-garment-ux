"""Reject undeclared changes to the source oracle before running it."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def check(*,candidate=None):
    rule=json.loads((HERE/'ORIGIN.json').read_bytes())
    raw=subprocess.check_output(['git','-C',str(ROOT),'show',rule['head']+':'+rule['path']])
    assert sha256(raw).hexdigest()==rule['sha256']
    expected=raw.decode()
    for c in rule['changes']:
        assert expected.count(c['old'])==c['count'];expected=expected.replace(c['old'],c['new'])
    assert(candidate if candidate is not None else(HERE/'check.py').read_text())==expected,'UNDECLARED_ASSEMBLY_ORACLE_CHANGE'
    return True
if __name__=='__main__':
    check()
    s=importlib.util.spec_from_file_location('complete_source',HERE/'check.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    value=m.check();out=ROOT/'cp6-proof/current-complete-components/SOURCE.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
