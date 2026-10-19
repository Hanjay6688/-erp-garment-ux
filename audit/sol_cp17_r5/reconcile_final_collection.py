"""Verify registered terminal ownership, exact logs and every selected artifact byte."""
from collections import Counter
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path,PurePosixPath

ROOT=Path(__file__).resolve().parent
R=ROOT/'ci_receipts'


def main():
    reg=json.loads((R/'ROOT_RUN_REGISTER_V8.json').read_text());obs=json.loads((R/'OWN_TERMINAL_OBSERVATIONS.json').read_text())
    assert len(reg)==len(obs)==12 and {r['run_id']for r in reg}=={r['run_id']for r in obs}
    registered={r['run_id']:r for r in reg};logs=json.loads((R/'OWN_JOB_LOG_INDEX.json').read_text());by_log={j['job_id']:j for j in logs['jobs']}
    jobs={};artifacts={};identities=[]
    def verify(path,length,digest):
        b=path.read_bytes();assert len(b)==length and sha256(b).hexdigest()==digest,str(path)
    for o in obs:
        row=registered[o['run_id']];m=o['metadata']
        assert m['status']=='completed' and m['run_attempt']==1 and m['head_sha']==row['head_sha']
        assert m['head_branch']=='audit/sol-cp1-7-r5-17fa2507-20261019' and m['path']==row['workflow_path']
        for j in o['jobs']:
            assert j['status']=='completed' and j['id']not in jobs and j['run_id']==o['run_id'];jobs[j['id']]=j
            log=by_log[j['id']];assert log['workflow_sha']==m['head_sha'] and log['run_id']==o['run_id'] and log['conclusion']==j['conclusion']
            verify(R/log['log_path'],log['bytes'],log['sha256'])
        for a in o['artifacts']:
            assert a['id']not in artifacts and a['workflow_run']['id']==o['run_id'] and a['workflow_run']['head_sha']==m['head_sha'];artifacts[a['id']]=a
    assert set(jobs)==set(by_log) and len(jobs)==31 and len(artifacts)==43
    selected=0;total=0;downloads=[]
    for ident,a in artifacts.items():
        d=R/'sol_artifacts'/str(ident);receipt=json.loads((d/'DOWNLOAD_RECEIPT.json').read_text())
        assert receipt['artifact_id']==ident and receipt['run_id']==a['workflow_run']['id']
        assert receipt['archive_bytes']==a['size_in_bytes'] and receipt['archive_sha256']==a['digest'].removeprefix('sha256:') and receipt['expected_digest']==a['digest'] and receipt['digest_matches']
        required={x['path']for x in receipt['archive_inventory']if PurePosixPath(x['path']).suffix.lower()in{'.json','.jsonl','.md','.txt','.csv','.sarif'} and not x['path'].endswith('/') and '..'not in PurePosixPath(x['path']).parts and not PurePosixPath(x['path']).is_absolute()}
        assert required=={f['path']for f in receipt['selected_files']}
        for f in receipt['selected_files']:verify(d/'files'/f['path'],f['bytes'],f['sha256']);selected+=1;total+=f['bytes']
        if ident!=12181651792:
            before=json.loads((d/'files/SOL_R5_IDENTITY_BEFORE.json').read_text());after=json.loads((d/'files/SOL_R5_IDENTITY_AFTER.json').read_text())
            assert before['candidate_sha']==after['candidate_sha']=='17fa25075ba77f0853c3c16f504288ace03eec35'
            assert before['candidate_tree']==after['candidate_tree']=='65f778479093d869a3354c0b9f19b4d9a541d98a'
            assert before['product_roots']==after['product_roots'] and before['product_worktree_clean'] and after['product_worktree_clean']
            identities.append(dict(artifact_id=ident,workflow_sha=before['workflow_sha'],run_id=int(before['run_id']),product_roots=before['product_roots']))
        downloads.append(dict(artifact_id=ident,run_id=receipt['run_id'],archive_bytes=receipt['archive_bytes'],archive_sha256=receipt['archive_sha256'],selected_text_files=len(receipt['selected_files'])))
    ledger=json.loads((ROOT/'CASE_LEDGER.json').read_text())
    assert ledger['raw_status_counts']=={'PASS':1036,'INCOMPLETE':3} and ledger['case_occurrences']==1039 and ledger['unique_case_id_strings']==1034
    result=dict(state='FINAL_PROVIDER_RECONCILIATION_NOT_A_PRODUCT_VERDICT',captured_at=datetime.now(timezone.utc).isoformat(),candidate_sha='17fa25075ba77f0853c3c16f504288ace03eec35',candidate_tree='65f778479093d869a3354c0b9f19b4d9a541d98a',registered_runs=12,
                provider_conclusions=dict(Counter(o['metadata']['conclusion']for o in obs)),provider_jobs=31,job_conclusions=dict(Counter(j['conclusion']for j in jobs.values())),run_attempts=[1],exact_decoded_job_logs=31,
                provider_artifacts=43,downloaded_archives=43,all_provider_archive_digests_and_sizes_match=True,selected_text_files=selected,selected_text_bytes=total,all_selected_text_bytes_sha256_verified=True,
                candidate_identity_pairs=len(identities),all_candidate_product_roots_before_after_equal=True,
                raw_case_occurrences=1039,raw_case_status_counts=ledger['raw_status_counts'],unique_case_id_strings=1034,primary_distinct_reports=ledger['captured_primary_documents'],
                pure_capture_qualification_native_credit=0,pure_decoder_controls=4,provider_log_zip_digest_available=False,
                bootstrap_attempts={str(j['job_id']):[b['attempt']for b in j['bootstrap_markers']]for j in logs['jobs']},
                downloaded_artifacts=downloads,source_identities=identities,
                limits=['Original three provider FAILURE and raw INCOMPLETE records retained; see AUDITOR_TOOL_FAILURES.json.',
                        'The read-only captured-result qualifier adds no Native execution.',
                        'Non-CP17 identity recorder345 counts are static declaration metadata, not execution credit for those jobs.',
                        'Job logs preserve exact connector-decoded UTF-8, not a provider ZIP digest.',
                        'Binary screenshot members are excluded from textual evidence selection; no screenshots saved as deliverables.',
                        'Case occurrences and unique strings are not functionality counts or ERP percentages.'])
    (ROOT/'OWN_CI_RECEIPT_FINAL.json').write_text(json.dumps(result,indent=2)+'\n')
    (R/'OWN_CI_RECEIPT_FINAL.json').write_text(json.dumps(result,indent=2)+'\n')
    (ROOT/'RUN_REGISTER.json').write_text(json.dumps(reg,indent=2)+'\n')
    curated=json.loads((R/'OWN_JOB_LOG_INDEX.json').read_text())
    for row in curated['jobs']:
        row['steps']=row.pop('setup_steps')
        row['failed_steps']=row.pop('setup_failed_steps')
    curated['metadata_field_note']='Legacy collector fields setup_steps/setup_failed_steps held the whole job step array. Curated aliases steps/failed_steps preserve their meaning and values; original raw index and all log bytes retained.'
    (ROOT/'JOB_LOG_INDEX.json').write_text(json.dumps(curated,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ['registered_runs','provider_conclusions','provider_jobs','job_conclusions','exact_decoded_job_logs','downloaded_archives','selected_text_files','selected_text_bytes','raw_case_status_counts','candidate_identity_pairs']}))


if __name__=='__main__':main()
