"""Restore exact historical proof inputs locally; never restore a GitHub trigger."""
from pathlib import Path,PurePosixPath
from hashlib import sha256
import json,os,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def materialize():
    cfg=json.loads((HERE/'ARCHIVE.json').read_bytes());assert len(cfg['files'])==24
    assert cfg['source_body_changes']==cfg['frozen_manifest_changes']==cfg['B_changes']==0
    written=[]
    for item in cfg['files']:
        rel=PurePosixPath(item['path']);stored=PurePosixPath(item['archive'])
        assert rel.parts[:2]==('.github','workflows')and len(rel.parts)==3 and rel.suffix=='.yml'
        assert stored.parts[:3]==('scripts','current-workflow-history-isolation','frozen-workflows')and len(stored.parts)==4 and stored.suffix=='.txt'
        source=ROOT/str(stored);target=ROOT/str(rel);assert not source.is_symlink()and not target.is_symlink()
        assert source.resolve().is_relative_to(ROOT.resolve())and target.resolve().is_relative_to(ROOT.resolve())
        assert target.parent.resolve()==(ROOT/'.github/workflows').resolve()
        raw=source.read_bytes();assert len(raw)==item['bytes']and sha256(raw).hexdigest()==item['sha256']
        original=subprocess.check_output(['git','-C',str(ROOT),'show',cfg['base_head']+':'+str(rel)]);assert raw==original
        for name in item['frozen_manifests']:
            declaration=json.loads((ROOT/name).read_bytes());assert declaration['files'][str(rel)]==item['sha256']
        tracked=subprocess.check_output(['git','-C',str(ROOT),'ls-files','--',str(rel)],text=True).strip();assert not tracked,'HISTORICAL_WORKFLOW_MUST_NOT_BE_ACTIVE_IN_GIT'
        if target.exists():assert target.is_file()and target.read_bytes()==raw,'EXISTING_PROOF_INPUT_MISMATCH'
        else:
            with target.open('xb')as f:f.write(raw)
        written.append(str(rel))
    assert len(set(written))==24
    return dict(status='EXACT_HISTORICAL_PROOF_INPUTS_ONLY',files=len(written),all_bytes_equal_frozen_original=True,Git_workflow_entries_restored=0,active_workflow_behavior_added=False)
if __name__=='__main__':print(json.dumps(materialize()))
