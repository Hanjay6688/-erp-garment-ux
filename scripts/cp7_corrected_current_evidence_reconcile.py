"""Compare preserved Originals to the corrected entrypoint without moving credit.

The predecessor's UI/migration trees can remain unchanged while the installed
private function changes. Report those identities separately. A predecessor
PASS never becomes a corrected-entrypoint runtime PASS through source reuse.
"""
from pathlib import Path
from collections import Counter
from hashlib import sha256
import argparse,json,zipfile
import cp7_current_evidence_reconcile as previous


def exact_paths(value,expected,path=''):
    if isinstance(value,dict):
        if value==expected:return [path]
        return [found for key,child in value.items()for found in exact_paths(child,expected,path+'/'+key)]
    if isinstance(value,list):
        return [found for key,child in enumerate(value)for found in exact_paths(child,expected,path+'/'+str(key))]
    return []


def original_path(receipt):
    # Strict-group reports deliberately keep their original basename. Select
    # the top-level Original by its recorded bytes AND hash, never basename
    # alone or a convenient first match.
    matches=[f['path']for f in receipt['preserved_files']
        if Path(f['path']).name==receipt['original_name']
        and f['bytes']==receipt['original_bytes']and f['sha256']==receipt['original_sha256']]
    assert len(matches)==1,(receipt['original_name'],matches)
    return matches[0]


def predecessor_comparisons(archive,installation):
    head=previous.git('rev-parse','HEAD')
    assert not previous.git('status','--porcelain','--',*previous.PRODUCT_PATHS),'DIRTY_PRODUCT'
    result=dict(evidence_type='WRITER_STATIC_SOURCE_COMPARISON',current_head=head,
        current_tree=previous.git('rev-parse','HEAD^{tree}'),archive_bytes=archive.stat().st_size,
        archive_sha256=sha256(archive.read_bytes()).hexdigest(),product_paths=list(previous.PRODUCT_PATHS),
        current_product_trees={p:previous.git('rev-parse',head+':'+p)for p in previous.PRODUCT_PATHS},
        reports=[],newly_executed_cases=0,full_qualification_complete=False,independent_acceptance=False,production_go=False)
    with zipfile.ZipFile(archive)as z:
        assert z.testzip()is None,'ARCHIVE_CRC_FAILURE'
        assert len(z.namelist())==len(set(z.namelist())),'DUPLICATE_ARCHIVE_MEMBERS'
        index=json.loads(z.read('INDEX.json'))
        for receipt in index['report_receipts']:
            for item in receipt['preserved_files']:
                raw=z.read(item['path'])
                assert len(raw)==item['bytes']and sha256(raw).hexdigest()==item['sha256'],item['path']
            raw=z.read(original_path(receipt));report=json.loads(raw)
            assert report['status']==receipt['status'],'HISTORICAL_STATUS_MISMATCH'
            maps=[]
            for pointer,files in previous.file_maps(report.get('source_declaration',{}),'/source_declaration'):
                changed=[]
                for path,expected in files.items():
                    target=previous.ROOT/path;assert target.resolve().is_relative_to(previous.ROOT),path
                    actual=sha256(target.read_bytes()).hexdigest()if target.is_file()else None
                    if actual!=expected:changed.append(dict(path=path,expected=expected,observed=actual))
                maps.append(dict(path=pointer,checked_files=len(files),differences=changed))
            changed=previous.git('diff','--name-only',receipt['head'],head,'--',*previous.PRODUCT_PATHS).splitlines()
            result['reports'].append(dict(original=receipt['original_name'],historical_status=receipt['status'],
                run_id=receipt['run_id'],artifact_id=receipt['artifact_id'],qualified_head=receipt['head'],
                original_bytes=len(raw),original_sha256=sha256(raw).hexdigest(),product_path_changes=changed,
                matching_installed_source_objects=previous.matching_objects(report,installation,installation['product']),
                declared_file_map_comparisons=maps,receipt=receipt['git_receipt_url'],runtime_rerun_here=False,
                historical_status_reclassified=False))
    result['historical_status_counts']=dict(Counter(r['historical_status']for r in result['reports']))
    result['all_product_paths_unchanged']=all(not r['product_path_changes']for r in result['reports'])
    result['reports_with_direct_current_installation_or_product_identity']=sum(bool(r['matching_installed_source_objects'])for r in result['reports'])
    result['limitations']=[
        'Source equivalence is not runtime or independent acceptance.',
        'Repository-relative file maps and complete recursive source identities are compared separately.',
        'All declared archived bytes and historical statuses are verified; first failures remain preserved.',
        'An identical basename in a strict-group report is disambiguated by recorded full Original size and SHA256.',
        'No source-map difference changes a historical outcome or duplicates a case budget.']
    return result


def reconcile(archive):
    import cp7_current_return_installation as current
    import cp7_current_return_recovery as recovery
    source=current.sources();old=current.predecessor.sources();recovery_source=recovery.sources()
    result=predecessor_comparisons(archive,old)
    result['contract']='cp7.corrected-current-preserved-evidence-reconciliation.v1'
    result['corrected_installation']=source
    result['corrected_recovery']=recovery_source
    result['installed_private_function_semantics_changed_from_predecessor']=True
    result['declared_function_delta']=current.delta.sources()
    result['source_identity_is_not_current_runtime_acceptance']=True
    classifications=[]
    with zipfile.ZipFile(archive)as z:
        index=json.loads(z.read('INDEX.json'))
        receipts={(r['run_id'],r['artifact_id']):r for r in index['report_receipts']}
        for row in result['reports']:
            # Rename the old comparator's vocabulary; leave Original bytes and
            # historical outcomes untouched and keep its complete comparisons.
            identities=row.pop('matching_installed_source_objects')
            row['matching_predecessor_source_objects']=[dict(item,identity=item['identity'].replace('CURRENT_','PREDECESSOR_'))for item in identities]
            receipt=receipts[(row['run_id'],row['artifact_id'])]
            report=json.loads(z.read(original_path(receipt)));declaration=report.get('source_declaration',{})
            corrected=exact_paths(declaration,source,'/source_declaration')
            predecessor=exact_paths(declaration,old,'/source_declaration')
            row['corrected_installation_declaration_paths']=corrected
            row['predecessor_installation_declaration_paths']=predecessor
            row['corrected_recovery_declaration_paths']=exact_paths(declaration,recovery_source,'/source_declaration')
            classification='EXACT_CORRECTED_DECLARATION'if corrected else'EXACT_PREDECESSOR_DECLARATION'if predecessor else'NO_COMPLETE_ENTRYPOINT_DECLARATION'
            row['entrypoint_source_classification']=classification
            row['runtime_outcome_promoted_or_inherited']=False
            classifications.append(classification)
    result['reports_with_predecessor_installation_or_product_identity']=result.pop('reports_with_direct_current_installation_or_product_identity')
    result['entrypoint_declaration_counts']=dict(Counter(classifications))
    result['limitations'] += [
        'Unchanged UI/migration trees do not mean unchanged installed private-function semantics.',
        'An exact corrected declaration binds source only; review each Original case result, restoration and package gates separately.',
        'No old PASS, failure, case budget, independent acceptance or production authority is promoted by this comparison.']
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();result=reconcile(args.archive)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in('current_head','historical_status_counts','entrypoint_declaration_counts','newly_executed_cases','production_go')}))
