from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess

def exact_provenance_guard(before,after):
    old=("  where l.vendor_id=p_vendor and j.status in('POSTED','REVERSED')\n"
         "   and l.account_id in(select account_id from cp7_vendor_receivable.sources_v1 where vendor_id=p_vendor)\n"
         "  group by l.account_id,l.vendor_id,l.journal_entry_id)").encode()
    new=("  where (l.vendor_id=p_vendor or not exists(\n"
         "    select 1 from cp7_vendor_receivable.sources_v1 owner_source\n"
         "    where owner_source.account_id=l.account_id and owner_source.vendor_id=l.vendor_id))\n"
         "   and j.status in('POSTED','REVERSED')\n"
         "   and l.account_id in(select account_id from cp7_vendor_receivable.sources_v1 where vendor_id=p_vendor)\n"
         "  group by l.account_id,l.vendor_id,l.journal_entry_id)").encode()
    if before.count(old)!=1 or after!=before.replace(old,new,1):
        raise ValueError('VENDOR_PROVENANCE_EXACT_GUARD_DERIVATION_REQUIRED')
    return dict(scope='ONLY_PRIVATE_PROVE_OBSERVED_VENDOR_PREDICATE',before_sha256=sha256(before).hexdigest(),
        after_sha256=sha256(after).hexdigest(),Native_money_or_date_or_HPP_calculation_changed=False)

def admitted(repo,here,product):
    cfg=json.loads((here/'CONFIG.json').read_bytes());source=json.loads((here/'SOURCE.json').read_bytes())
    assert cfg['contract']=='cp7.vendor-receivable-native.v1'
    assert cfg['production_go']is cfg['independent_acceptance']is False
    for path,digest in source['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    changed=subprocess.check_output(['git','-C',str(repo),'diff','--name-only',cfg['base_head'],'HEAD'],text=True).splitlines()
    assert set(changed)<=set(source['allowed_changes']),'UNDECLARED_VENDOR_DELTA'
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no']).strip()
    parent=product.parent().sources()
    whole=sha256(json.dumps(parent,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    assert whole==cfg['whole_backend_sha256'],'QUALIFIED_PARENT_BACKEND_CHANGED'
    proof=cfg['backend_original'];raw=(Path(os.environ['CP7_VENDOR_BACKEND_ORIGINALS'])/proof['name']).read_bytes()
    assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    actual=json.loads(raw)
    assert actual['status']=='PASS'and actual['qualification_commit']==cfg['backend_head']
    assert actual['source_declaration']['current_installation']==parent
    # Retain the exact first incomplete result. A successor declaration never
    # rewrites that result to pretend its six passes covered this observer.
    failure=cfg['first_failure_original']
    failed_raw=(Path(os.environ['CP7_VENDOR_BACKEND_ORIGINALS'])/failure['name']).read_bytes()
    assert len(failed_raw)==failure['bytes']and sha256(failed_raw).hexdigest()==failure['sha256']
    failed=json.loads(failed_raw)
    assert failed['status']=='INCOMPLETE'and failed['qualification_commit']==failure['head']
    failed_group=failed['committed']['VENDOR_RECEIVABLE_NATIVE7_AND_USED_INVERSE']['native']
    assert failed_group['counts']=={'PASS':6,'INCOMPLETE':1}
    assert failed_group['cases']['OW08B_VENDOR_REFUND_REPLAY_INVERSE_HISTORY']['status']=='INCOMPLETE'
    from cp7_vendor_receivable.cases import IDS
    assert cfg['native_case_ids']==list(IDS)
    current=product.sources();assert current['predecessor']==parent
    predecessor=failed['source_declaration']['current_installation']
    sql_path='scripts/cp7_vendor_receivable/receivable.sql'
    before_sql=subprocess.check_output(['git','-C',str(repo),'show',failure['head']+':'+sql_path])
    assert sha256(before_sql).hexdigest()==predecessor['files'][sql_path]
    guard=exact_provenance_guard(before_sql,(repo/sql_path).read_bytes())
    approved=dict(predecessor,files=dict(predecessor['files']))
    approved['files'][sql_path]=guard['after_sha256']
    assert current==approved,'UNDECLARED_VENDOR_RUNTIME_CHANGE'
    combined=cfg['combined11'];selected=combined.get('accepted_observer_native7')
    if selected is None:raise ValueError('VENDOR_COMBINED_CLOSED_COMPLETE_OBSERVER_NATIVE7_REQUIRED')
    assert selected['head']==cfg['provenance_successor']['observer_successor']
    followup=repo/'scripts/current-vendor-receivable-followup'
    assert json.loads((followup/'CONFIG.json').read_bytes())['accepted_native7']==selected
    spec=importlib.util.spec_from_file_location('combined_vendor_precursor_gate',followup/'gate.py')
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    originals=Path(os.environ['CP7_VENDOR_NATIVE7_ORIGINALS'])
    # This full precursor qualifies the unchanged base, not the new predicate.
    # Seven fresh Native cases on current must PASS before followup operations.
    prerequisite=gate.checked(dict(accepted_native7=selected),
        (originals/selected['original']['name']).read_bytes(),
        (originals/selected['package']['name']).read_bytes(),predecessor,IDS)
    return dict(status='QUALIFIED_BACKEND3194_AND_VENDOR_DELTA_ADMITTED',qualification=source,
        current_installation=current,qualified_parent_installation=parent,backend_head=cfg['backend_head'],
        whole_backend_sha256=whole,Native_case_ids=list(IDS),
        first_failure=dict(failure,counts=failed_group['counts']),runtime_identical_to_first_attempt=False,
        approved_private_provenance_guard=guard,
        complete_precursor_native7=prerequisite,fresh_current_native7_required_before_followup=True,
        predecessor_browser_B_retained_not_reexecuted=True,production_go=False,independent_acceptance=False)
