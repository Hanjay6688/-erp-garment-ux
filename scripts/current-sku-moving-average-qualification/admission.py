"""Closed source and exact accepted SKU27 parent admission before database use."""
from hashlib import sha256
from pathlib import Path
import ast
import json
import os
import subprocess

def admitted(repo,here,product,derivation):
    cfg=json.loads((here/'CONFIG.json').read_bytes());source=json.loads((here/'SOURCE.json').read_bytes())
    if cfg['contract']!='cp7.sku-moving-average-native5.v1':raise ValueError('SKU_MOVAVG_CONTRACT_CHANGED')
    for path,digest in source['files'].items():
        if sha256((repo/path).read_bytes()).hexdigest()!=digest:raise ValueError('SKU_MOVAVG_SOURCE_CHANGED:'+path)
    def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
    changed=git('diff','--name-only',cfg['base_head'],'HEAD').decode().splitlines()
    if not set(changed)<=set(source['allowed_changes']):raise ValueError('SKU_MOVAVG_UNDECLARED_SUCCESSOR_CHANGE')
    if git('status','--porcelain','--untracked-files=no').strip():raise ValueError('SKU_MOVAVG_TRACKED_WORKTREE_DIRTY')
    for path,digest in cfg['parent_runtime_files'].items():
        raw=(repo/path).read_bytes()
        if sha256(raw).hexdigest()!=digest or raw!=git('show',cfg['parent_source_head']+':'+path):
            raise ValueError('SKU_MOVAVG_PARENT_SOURCE_CHANGED:'+path)
    if derivation!=cfg['runner_derivation']:raise ValueError('SKU_MOVAVG_RUNNER_DERIVATION_CHANGED')
    tree=ast.parse((repo/'scripts/cp7_sku_moving_average/qualification_cases.py').read_text())
    ids=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='IDS'for t in n.targets))
    if list(ids)!=cfg['native_case_ids']or len(set(ids))!=5:raise ValueError('SKU_MOVAVG_CASE_PLAN_CHANGED')
    originals=Path(os.environ['CP7_SKU_PARENT_ORIGINALS'])
    parent=cfg['qualified_parent'];proofs={}
    for name,pin in parent['originals'].items():
        raw=(originals/name).read_bytes()
        if len(raw)!=pin['bytes']or sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('SKU_MOVAVG_PARENT_ORIGINAL_CHANGED:'+name)
        proofs[name]=dict(bytes=len(raw),sha256=pin['sha256'])
    report=json.loads((originals/'CP7_SKU_MANAGED_RECOVERY_NATIVE27.json').read_bytes())
    expected_parent=dict(status='PASS',qualification_commit=parent['head'],required_case_ids_pass=True,
      actual_Native_cases=12,base_Native_cases=7,cost_Native_cases=5,actual_two_session_races=3,
      actual_Native_session_permission_waits=7,actual_Native_nonblocking_busy_cases=1,
      actual_Auth_HTTP_cases=0,actual_browser_cases=4,actual_business_cases=27,
      real_Auth_browser_claim=True,baseline_full22_all_rows_all_sequences_equal=True,
      restore_raw_public_equal=True,cp6_restored=True,baseline_advisors_equal=True,advisor_gate=True,
      production_go=False,independent_acceptance=False)
    if any(type(report.get(key))is not type(value)or report[key]!=value for key,value in expected_parent.items()):
        raise ValueError('SKU_MOVAVG_PARENT_NOT_TERMINAL_NATIVE27')
    for name,count in(('CP7_SKU_PAIR_CONVERSION_NATIVE7.json',7),('CP7_SKU_GROUP_COST_NATIVE5.json',5)):
        value=json.loads((originals/name).read_bytes())
        if value.get('status')!='PASS'or value.get('counts')!={'PASS':count}or value.get('complete_boundary_restored')is not True:
            raise ValueError('SKU_MOVAVG_PARENT_COMPONENT_NOT_TERMINAL:'+name)
    package=json.loads((originals/'T3_PACKAGE_INSTALL.json').read_bytes())
    if package.get('gate')!={'installed':True,'primary_unchanged':True,'backup_restore_drill':True,'security_advisors':True,'writer_runtime':True}:
        raise ValueError('SKU_MOVAVG_PARENT_PACKAGE_NOT_TERMINAL')
    files=json.loads((originals/'T3_PACKAGE_FILES_INSTALL.json').read_bytes())
    expected_keys=['A'+chr(n)for n in range(ord('C'),ord('Z')+1)]+['B'+chr(n)for n in range(ord('A'),ord('F')+1)]
    if files.get('status')!='ALL_FILES_INSTALLED'or files.get('files')!=[dict(key=key,status='PASS')for key in expected_keys]:
        raise ValueError('SKU_MOVAVG_PARENT_PACKAGE_FILES_NOT_TERMINAL')
    backup=json.loads((originals/'T3_BACKUP_RESTORE_DRILL.json').read_bytes())
    if backup.get('status')!='RESTORED_IDENTICAL'or not backup.get('checks')or not all(backup['checks'].values())or backup.get('data',{}).get('differ')!={}:
        raise ValueError('SKU_MOVAVG_PARENT_BACKUP_NOT_IDENTICAL')
    current=product.sources();parent_sources=product.parent().sources()
    if current['predecessor']!=parent_sources or current['files']!=cfg['runtime_files']:raise ValueError('SKU_MOVAVG_RUNTIME_SOURCE_CHANGED')
    return dict(status='EXACT_ACCEPTED_SKU27_PARENT_AND_MOVAVG_CHILD_ADMITTED',qualification=source,
      qualified_parent=dict(head=parent['head'],tree=parent['tree'],run_id=parent['run_id'],job_id=parent['job_id'],artifact_id=parent['artifact_id'],proofs=proofs),
      current_installation=current,runner_derivation=derivation,actual_Native_case_ids=list(ids),
      current_installation_entrypoint=dict(module='cp7_sku_moving_average.composition',install='install',verify='verify',rollback_preuse='rollback_preuse'),
      production_go=False,independent_acceptance=False)
