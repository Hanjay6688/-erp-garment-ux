"""Retain exact safe proof members without duplicating repository code, dumps or screenshots."""
from pathlib import Path
import hashlib,json,re,zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
E=ROOT.parent/'sol-evidence'
DEST=ROOT.parent/'SOL_CP17_dfab13bf_20261016_EVIDENCE.zip'
meta=json.loads((OUT/'ARTIFACT_REGISTER.json').read_text())
candidate='dfab13bf62398a69a02bf6221c06d29075e5e40b'
workflow_shas=sorted({r['run']['head_sha'] for r in json.loads((OUT/'RUN_REGISTER.json').read_text())['runs']})
index=dict(candidate_sha=candidate,contains_hosted_data=False,contains_original_CP2_backup=False,
    selected_originals=[],omitted_members=[],logs=[],
    repository_sources=dict(repo='Hanjay6688/-erp-garment-ux',candidate_sha=candidate,workflow_commits=workflow_shas,
       source_paths='audit/sol_cp17_combined/* and .github/workflows/audit-sol-* at each declared workflow SHA',
       native_providers='Candidate scripts from source_commit/provider_sha256 in the exact retained JSON outcomes',
       repository_backed_code_duplicated_into_library=False),
    report_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.suffix in ['.md','.json','.csv'] and p.name not in ['PROOF_ARCHIVE_POINTER.json','SEAL_MANIFEST.json']})
secret=re.compile(rb'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|postgres(?:ql)?://[^\s]+:[^\s]+@')
with zipfile.ZipFile(DEST,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as target:
    for a in meta['artifacts']:
        path=E/f"{a['id']}.zip"
        raw=path.read_bytes()
        assert len(raw)==a['size_in_bytes'] and hashlib.sha256(raw).hexdigest()==a['digest'].removeprefix('sha256:')
        with zipfile.ZipFile(path) as source:
            for member in source.infolist():
                if member.is_dir():continue
                value=source.read(member);ext=Path(member.filename).suffix.lower()
                record=dict(artifact_id=a['id'],run_id=a['run_id'],original_member=member.filename,
                    original_member_bytes=len(value),original_member_sha256=hashlib.sha256(value).hexdigest(),original_zip_sha256=a['digest'])
                if ext in ['.json','.txt','.log','.sarif']:
                    assert not secret.search(value),('credential-shaped value',a['id'],member.filename)
                    name=f"native-originals/{a['id']}/{member.filename}"
                    target.writestr(name,value);record.update(archive_member=name,redacted=False);index['selected_originals'].append(record)
                else:
                    record['reason']='SCREENSHOT_NOT_A_REQUESTED_DELIVERABLE' if ext in ['.png','.jpg','.jpeg'] else 'DATABASE_DUMP_OR_NONREPORT_NOT_INCLUDED'
                    index['omitted_members'].append(record)
    for name in ['owner_initial.log','diagnostic_initial.log','initial_retest.log']:
        raw=(E/name).read_bytes();value=raw;redactions=0
        if name=='initial_retest.log':
            value,redactions=re.subn(rb'postgres(?:ql)?://[^\s]+',b'[REDACTED_SYNTHETIC_DATABASE_CONNECTION_URL]',raw)
        assert not secret.search(value),name
        dest='logs/'+name;target.writestr(dest,value)
        index['logs'].append(dict(archive_member=dest,original_sha256=hashlib.sha256(raw).hexdigest(),retained_sha256=hashlib.sha256(value).hexdigest(),credential_url_redactions=redactions,full_original_kept_privately_in_current_workspace=True))
    comparator=E/'PUBLIC_STATE_COMPARATOR_LOG.json'
    value=comparator.read_bytes();assert not secret.search(value)
    target.writestr('logs/PUBLIC_STATE_COMPARATOR_LOG.json',value)
    target.writestr('INDEX.json',json.dumps(index,ensure_ascii=False,indent=2)+'\n')
    target.writestr('README.txt',
        'Independent Sol CP1–CP7 proof, candidate '+candidate+'\n'
        'Exact safe JSON/TXT/SARIF outcomes, selected original logs and per-member/ZIP hashes.\n'
        'SQL dumps and screenshots are deliberately excluded; their member hashes are in INDEX.json.\n'
        'No hosted data or original CP2 recovery material is included. One synthetic connection URL in one log is redacted; original and retained hashes are recorded.\n'
        'Probe source is retained in the immutable audit workflow commits listed in INDEX.json, rather than duplicated from the git repository.\n'
        'Native, real Auth/browser and HTTP-mock claims must be read separately, as marked in the outcomes and final reports.\n')
receipt=dict(filename=DEST.name,local_path=str(DEST),bytes=DEST.stat().st_size,sha256=hashlib.sha256(DEST.read_bytes()).hexdigest(),
    exact_report_members=len(index['selected_originals']),omitted_members=len(index['omitted_members']),
    contains_screenshots=False,contains_sql_dumps=False,contains_original_CP2=False,repository_sources='immutable Git commits; not duplicated',
    status='PREPARED_NOT_YET_SAVED')
(OUT/'PROOF_ARCHIVE_POINTER.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
