from pathlib import Path
from hashlib import sha256
import ast,json,subprocess,yaml
def check(repo,here,*,overrides=None):
    cfg=json.loads((here/'CONFIG.json').read_bytes());head=cfg['backend_head']
    assert subprocess.check_output(['git','-C',str(repo),'rev-parse',head+'^{tree}'],text=True).strip()==cfg['backend_tree']
    changes=subprocess.check_output(['git','-C',str(repo),'diff','--name-status',head,'HEAD'],text=True).splitlines()
    prefix='scripts/current-factory-live-heartbeat/'
    assert all(line.startswith('A\t'+prefix)or line=='A\t.github/workflows/cp7-d17-18-factory-live-heartbeat.yml'for line in changes),'BACKEND_OR_FROZEN_SOURCE_CHANGED'
    rules=json.loads((here/'ORIGIN.json').read_bytes());counts={}
    for name,rule in rules.items():
        raw=(repo/rule['path']).read_bytes();assert sha256(raw).hexdigest()==rule['sha256']
        expected=raw.decode()
        for change in rule['changes']:
            assert expected.count(change['old'])==change['count'],name
            expected=expected.replace(change['old'],change['new'])
        actual=(overrides or{}).get(name,(here/name).read_text())
        assert actual==expected,'UNDECLARED_FACTORY_OBSERVER_CHANGE:'+name
        assert sum(isinstance(n,ast.Assert)for n in ast.walk(ast.parse(actual)))==rule['assertions']>=rule['original_assertions']
        counts[name]=rule['assertions']
    factory=(here/'factory.py').read_text()
    assert factory.index('live.capture(')<factory.index('finally:')<factory.index('post_stop_public_status')
    wf=json.loads((here/'WORKFLOW_ORIGIN.json').read_bytes())
    raw=(repo/wf['path']).read_bytes();assert sha256(raw).hexdigest()==wf['sha256']
    original=yaml.safe_load(raw);expected=original
    for action in wf['changes']:
        if action['kind']=='replace':
            target=expected
            for key in action['path'][:-1]:target=target[key]
            assert target[action['path'][-1]]==action['before']
            target[action['path'][-1]]=action['after']
        else:
            assert action['kind']=='insert_steps'
            expected['jobs']['p21']['steps'][action['index']:action['index']]=action['steps']
    assert yaml.safe_load((repo/'.github/workflows/cp7-d17-18-factory-live-heartbeat.yml').read_bytes())==expected,'UNDECLARED_WORKFLOW_CHANGE'
    return dict(unchanged_backend_head=head,unchanged_entire_backend=True,qualification_derivation_exact=True,assertion_counts=counts,live_assertion_before_scheduler_stop=True,retained_six_groups=6,fresh_factory_groups=1,complete_restoration_preserved=True)
