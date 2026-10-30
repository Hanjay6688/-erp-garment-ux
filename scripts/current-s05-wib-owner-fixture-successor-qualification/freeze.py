"""Seal only the new qualifier and explicit historical242 declaration pin."""
from pathlib import Path
from hashlib import sha256
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NS='scripts/current-s05-wib-owner-fixture-successor-qualification/'
WORKFLOW='.github/workflows/cp7-current-s05-wib-owner-fixture-successor.yml'


def build():
    paths={str(p.relative_to(ROOT))for p in HERE.rglob('*')if p.is_file()and p.name!='SOURCE.json'}
    paths|={WORKFLOW,'scripts/current-s05-current-ac-editor-qualification/SOURCE.json'}
    cfg=json.loads((HERE/'CONFIG.json').read_bytes());files={}
    for name in sorted(paths):
        p=ROOT/name
        if p.is_symlink():raise ValueError('S05_FIXTURE_SOURCE_SYMLINK:'+name)
        raw=p.read_bytes();files[name]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest(),mode='100755'if p.stat().st_mode&0o111 else'100644')
    return dict(contract='cp7.s05-wib-owner-fixture-successor-source.v1',status='PREPARED_NOT_NATIVE_QUALIFIED',
        base_public_head=cfg['base_public_head'],base_public_tree=cfg['base_public_tree'],historical_current_AC_source242_sha256=cfg['historical_current_AC_source_sha256'],
        original_callback_source_sha256=cfg['original_cases_sha256'],original_callback_body_substitutions=0,
        private_case_scope_wrappers=2,private_dependency_bindings=['fixture','issue_note'],
        product_Native_reader_cost_FIFO_money_datecohort_oracle_changes=0,accepted_fresh_native10=None,
        fresh_required_Native_cases=10,extra_case_credit_for_negative_setup_or_committed_witness=0,
        actual_new_Native_Auth_browser_races=0,production_go=False,independent_acceptance=False,files=files)


if __name__=='__main__':
    source=build();raw=(json.dumps(source,indent=2)+'\n').encode();(HERE/'SOURCE.json').write_bytes(raw)
    print(json.dumps(dict(files=len(source['files']),bytes=len(raw),sha256=sha256(raw).hexdigest())))
