"""Require both complete runtime groups after independent disposable entries."""
from pathlib import Path
import json,subprocess,sys


def require(root,candidate):
    expected_dir=Path(__file__).resolve().parent
    binding=json.loads((expected_dir/'QUALIFIED_CORE.json').read_text())
    counts={};reports={}
    for label,file,group,declaration,count in (
        ('HTTP','CP7_OW04_HTTP.json','http','EXPECTED.json',8),
        ('RACES','CP7_OW04_RACES.json','races','RACE_EXPECTED.json',6)):
        ids=[r['id']for r in json.loads((expected_dir/declaration).read_text())['cases']]
        assert len(ids)==len(set(ids))==count,('OW04_FINAL_DECLARATION_CHANGED',label)
        report=json.loads((Path(root)/file).read_text());runtime=report.get(group,{})
        rows=runtime.get('cases'if label=='HTTP'else'races',{})
        assert report.get('candidate_commit')==candidate,('OW04_FINAL_CANDIDATE_CHANGED',label)
        assert report.get('core_directory_tree')==binding['core_directory_tree'],('OW04_FINAL_CORE_CHANGED',label)
        assert report.get('native_probe_blob')==binding['native_probe_blob'],('OW04_FINAL_NATIVE_PROBE_CHANGED',label)
        assert report.get('status')=='PASS'and report.get('expected_case_count')==count and report.get('observed_case_count')==count,('OW04_FINAL_INCOMPLETE',label)
        assert report.get('cp6_restored')is True and report.get('advisor_gate')is True,('OW04_FINAL_RESTORE_OR_ADVISOR',label)
        assert runtime.get('status')in('PASS','RUN_COMPLETE')and runtime.get('counts')=={'PASS':count},('OW04_FINAL_COUNTS',label)
        assert set(rows)==set(ids)and all(r.get('status')=='PASS'for r in rows.values()),('OW04_FINAL_CASE_SET',label)
        assert runtime.get('database_remaining')==0,('OW04_FINAL_DATABASE_REMAINS',label)
        if label=='HTTP':
            assert(runtime.get('auth_counts')or{}).get('restored')is True and not runtime.get('cleanup_failures'), 'OW04_FINAL_AUTH_NOT_RESTORED'
        counts[label]=count;reports[label]=dict(candidate=report['candidate_commit'],core=report['core_directory_tree'])
    return dict(label='OW04_HTTP_RACE_FINAL',status='PASS',candidate=candidate,counts=counts,
        native44_reused_candidate=binding['candidate'],native44_rerun=False,reports=reports,
        feature_complete=False,audit_complete=False,production_go=False)


if __name__=='__main__':
    assert len(sys.argv)==2,'OW04 final gate expects only the proof directory'
    candidate=subprocess.check_output(['git','-C',str(Path(__file__).resolve().parents[2]),'rev-parse','HEAD'],text=True).strip()
    try:result=require(Path(sys.argv[1]),candidate)
    except Exception as error:
        result=dict(label='OW04_HTTP_RACE_FINAL',status='INCOMPLETE',candidate=candidate,error=str(error),production_go=False)
        print(json.dumps(result),flush=True);raise
    (Path(sys.argv[1])/'OW04_HTTP_RACE_FINAL.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
