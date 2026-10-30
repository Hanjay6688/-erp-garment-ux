"""Explicit writer-only source freeze; never called by runtime/CI."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE='602b4e642a0afbb1acdcfd858b9f403dc14ec336'
TREE='2b86a81b9f3b14ff1ca775825ac01bb96afaa50d'

def bind():
    assert not os.environ.get('CI'),'SKU_RECOVERY_CI_MUST_NOT_GENERATE_SOURCE'
    assert subprocess.check_output(['git','rev-parse',BASE+'^{tree}'],cwd=ROOT,text=True).strip()==TREE
    prefixes=['scripts/cp7_sku_pair_conversion/','scripts/current-sku-managed-recovery-preflight/']
    files={}
    for prefix in prefixes:
        for path in sorted((ROOT/prefix).rglob('*')):
            if not path.is_file()or path==HERE/'SOURCE.json'or'__pycache__'in path.parts or path.suffix=='.pyc':continue
            assert not path.is_symlink()
            raw=path.read_bytes();files[str(path.relative_to(ROOT))]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
    report=json.loads((HERE/'evidence/LOCAL_RECOVERY.json').read_bytes())
    assert report['status']=='PASS'and report['count']==45 and report['actual_Native_financial']==0
    assert report['sources']['recovery']==files['scripts/cp7_sku_pair_conversion/recovery.sql']['sha256']
    value=dict(status='PREPARED_LOCAL_ONLY_NATIVE_FINANCIAL_0',base_head=BASE,base_tree=TREE,
      allowed_modified_base_files=['scripts/cp7_sku_pair_conversion/composition.py','scripts/cp7_sku_pair_conversion/README.md'],
      closed_owned_prefixes=prefixes,files=files,new_native_captures=2,total_native_captures=8,
      unchanged_original_private_functions=15,new_private_functions=4,total_private_functions=19,unchanged_private_tables=5,new_public_RPC=0,
      original23_callback_files_modified=0,Native_financial_SQL_rewritten=0,
      local_SQL_controls=45,local_source_metadata_controls=11,actual_Native_financial=0,actual_real_two_session=0,
      first_602=dict(run=40961419818,job=123754856235,artifact=12937998996,archive_bytes=27564211,
        archive_sha256='698b90b0bc3dfa52a8339d0b30464c2d98721594e56abdd53b07c959223f2bcc',library_id='libfile_d2e388bf3f1081919710f344d8c2ecfb',
        observed=dict(Native_core_PASS=7,Native_cost_PASS=2,Native_cost_INCOMPLETE=1,downstream_not_reached=13),
        failing_case='SKU29_COST_GROUP_RETURN_OVER_FIRST_PART_SAFETY_REFUSAL_ONLY',
        audit_sequence=dict(before=['1317',True],after=['1322',True]),outer_used_guard='ABSENT_NOT_QUALIFIED',
        restored_all22_data_sequences_roles_CP6_advisors_Auth=True,writer_runtime=False),
      actual_successor_required=dict(original23_unchanged=True,separate_Native_capacity_positive=2,separate_busy_cache_permission_wait=2,total_planned=27),
      sequence_scope='No reset. Per-command refusal/replay includes all local sequences; actual successful sequences restore only by full outer backup.',
      default_adoption=False,production_go=False,independent_acceptance=False)
    (HERE/'SOURCE.json').write_text(json.dumps(value,indent=2)+'\n')
    return dict(status=value['status'],files=len(files),local_SQL_controls=45,actual_Native_financial=0)

if __name__=='__main__':
    assert sys.argv[1:]==['--writer-freeze'],'SKU_RECOVERY_WRITER_FREEZE_ONLY'
    print(json.dumps(bind(),sort_keys=True))
