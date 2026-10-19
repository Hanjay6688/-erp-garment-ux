"""Qualify decoding of existing, pinned Native observations; no DB replay."""
from decimal import Decimal as D
from hashlib import sha256
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parent
MANIFEST=ROOT/'READER_MULTIROW_CAPTURE_Q2_PREEXECUTION_MANIFEST.json'
CASE='SOL_R5_ALL11_EMPTY_AND_MULTIROW_SINGLE_STATEMENT'


def decoded_numeric(value):
    # to_jsonb(SQL NULL)::text is SQL NULL, delivered by psycopg as None.
    # A JSON string 'null' is also preserved as None. Neither becomes zero.
    if value is None:return None
    return json.loads(value,parse_float=D,parse_int=D)


def qualify(archive_path,out_path):
    m=json.loads(MANIFEST.read_text());raw=Path(archive_path).read_bytes()
    result=dict(status='INCOMPLETE',classification='QUALIFIED_CAPTURE_REVIEW_NOT_NEW_NATIVE_EXECUTION',
                candidate_sha=m['candidate_sha'],source_run_id=m['source_run_id'],source_artifact_id=m['source_artifact_id'],
                source_archive_sha256=sha256(raw).hexdigest(),native_case_credit_added=0,
                original_provider_failure_preserved=True,original_raw_case_status='INCOMPLETE',
                original_auditor_tool_error='json.loads(None) after all11 SQL comparisons and PO literal assertions had completed',
                production_go=False,independent_acceptance=False,source_members={})
    try:
        assert sha256(raw).hexdigest()==m['source_archive_sha256']
        assert sha256(Path(__file__).read_bytes()).hexdigest()==m['qualifier_sha256']
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            def member(name):
                matches=[n for n in z.namelist() if n==name or n.endswith('/'+name)]
                assert len(matches)==1,(name,matches)
                b=z.read(matches[0]);result['source_members'][name]=dict(bytes=len(b),sha256=sha256(b).hexdigest())
                return json.loads(b)
            evidence=member(CASE+'_OBSERVATIONS.json')
            report=member('SOL_R5_READER_MULTIROW.json')
            before=member('SOL_R5_IDENTITY_BEFORE.json');after=member('SOL_R5_IDENTITY_AFTER.json')
        assert before['candidate_sha']==after['candidate_sha']==m['candidate_sha']
        assert before['candidate_tree']==after['candidate_tree']==m['candidate_tree']
        assert before['product_roots']==after['product_roots'] and before['product_worktree_clean'] and after['product_worktree_clean']
        group=report['groups']['reader_multirow'];case=group['cases'][CASE]
        assert report['status']=='INCOMPLETE' and case['status']=='INCOMPLETE'
        assert case['error']=='the JSON object must be str, bytes or bytearray, not NoneType'
        assert 'json.loads(r[1])' in case['traceback']
        assert group['complete_boundary_restored'] is True and case['full_boundary_restored'] is True and case['public_schema_unchanged'] is True
        assert not group['missing'] and report['cp6_restored'] is True
        assert not case['session_leaks']['advisory_locks'] and not case['session_leaks']['other_sessions']
        a=evidence['installed_answers'];b=evidence['legacy_graph_answers']
        assert set(a)==set(b)==set(m['readers']) and a==b
        for s,row in a.items():
            assert row['empty']==dict(kind='ROWS',rows=[]),(s,row['empty'])
            assert row['multirow']['kind']=='ROWS' and {r[0] for r in row['multirow']['rows']}=={0,1,2,3}
        po=a['erp.compute_po_hpp_gl_book_v2620e(uuid)']['multirow']['rows']
        actual=[tuple(decoded_numeric(r[1])[k] for k in ('fg_value','cogs_value','other_out_value')) for r in po]
        assert actual==[(D(108),D(12),D(0)),(D(0),D(0),D(0)),(D(0),D(0),D(0)),(D(108),D(12),D(0))]
        life=a['erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid)']['multirow']['rows']
        observed=[decoded_numeric(r[1]) for r in life]
        assert observed==[D(24),D(-12),None,D(24)],observed
        assert life[2][1] is None,'SQL_NULL_MUST_REMAIN_NONE'
        controls=[('SQL_NULL',None,None),('JSON_NULL','null',None),('POSITIVE','24.00',D(24)),('NEGATIVE','-12.00',D(-12))]
        for name,value,expected in controls:assert decoded_numeric(value)==expected,name
        result.update(status='PASS',all11_graph_answers_equal=True,all11_empty_queries_return_no_rows=True,
                      all11_single_statement_ordinals_complete=True,po_literal_rows=[list(map(str,r)) for r in actual],
                      lifecycle_literal_rows=[None if x is None else str(x) for x in observed],
                      pure_decoder_controls=[dict(id=name,status='PASS') for name,_,_ in controls],
                      actual_native_outer_and_case_boundary_restore_proved=True,
                      unexecuted_final_inner_fingerprint_assertion_claimed=False,
                      limitation='This qualifies reading the already captured Native SQL results. It does not turn the original raw INCOMPLETE or provider FAILURE into PASS, add a new Native execution, or claim the final inner fingerprint assertion ran.')
    except Exception as e:
        result.update(error=str(e));raise
    finally:
        Path(out_path).write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:result.get(k) for k in ['status','classification','native_case_credit_added','error']}))


if __name__=='__main__':qualify(sys.argv[1],sys.argv[2])
