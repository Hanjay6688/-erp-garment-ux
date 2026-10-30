"""Seal only this new qualifier; old282/current319 declarations stay exact."""
from pathlib import Path
from hashlib import sha256
import json
import os
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NS='scripts/current-credit-e1-phase-native17-qualification/'
WORKFLOW='.github/workflows/cp7-credit-e1-phase-native17.yml'
PUBLIC='fe2ae370c00e68437c4951c28c3a1038ce35fb38'


def build():
    old=json.loads((ROOT/'scripts/current-credit-e1-current-d1-native17-qualification/SOURCE.json').read_bytes())
    phase=json.loads((ROOT/'scripts/current-credit-e1-consumer-phase-successor/SOURCE.json').read_bytes())
    paths=set(old['files'])|set(phase['files'])|{'scripts/current-credit-e1-consumer-phase-successor/SOURCE.json',WORKFLOW}
    paths|={str(p.relative_to(ROOT))for p in HERE.rglob('*')if p.is_file()and p.name!='SOURCE.json'}
    source=dict(old)
    source.update(status='PREPARED_CURRENT_PHASE_FRESH_NATIVE17_NOT_EXECUTED',prepared_backend_head=PUBLIC,
        prepared_backend_tree='600d4575309e67a5575d7896382b38a27e000d7e',retained_source282_sha256='7a92b13976bd8cc24d19bc9f3ccb379f8a582bf7370ded4b23739296603d14fc',
        retained_source319_sha256='c1899ebed78fd3cd94a6e8e2d148fc6fe34911b48951aa1756e9e46dbef38ce3',
        source_transition='EXPLICIT_TWO_SQL_PHASE_HELPER_PRIVATE40_TO41',accepted_native17=None,files={})
    for name in sorted(paths):
        p=ROOT/name
        if p.is_symlink():raise ValueError('SOURCE_SYMLINK:'+name)
        raw=p.read_bytes();source['files'][name]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest(),mode='100755'if p.stat().st_mode&0o111 else'100644')
    delta=subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only',old['frozen_parent_head'],PUBLIC],text=True,
        env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_OPTIONAL_LOCKS':'0'}).splitlines()
    source['allowed_child_paths']=sorted(set(delta)|{name for name in paths if name.startswith(NS)}|{NS+'SOURCE.json',WORKFLOW})
    return source


if __name__=='__main__':
    source=build();raw=(json.dumps(source,indent=2)+'\n').encode();(HERE/'SOURCE.json').write_bytes(raw)
    print(json.dumps(dict(files=len(source['files']),bytes=len(raw),sha256=sha256(raw).hexdigest())))
