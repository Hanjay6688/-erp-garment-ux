"""Mechanical ledger of captured own reports; counts are not product judgments."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / 'ci_receipts/sol_artifacts'
OWN = {'SOL_R5_ORIGINAL_CONTROLS.json', 'SOL_R5_READER_GRAPH.json',
       'SOL_R5_READER_MULTIROW.json', 'SOL_R5_READER_MAPPING_Q2.json', 'SOL_R5_READER_MAPPING_Q3.json', 'SOL_R5_REPAIR_NEGATIVE_VECTOR.json'}


def walk(node, pointer=''):
    if isinstance(node, dict):
        for key, value in node.items():
            at = pointer + '/' + str(key).replace('~','~0').replace('/','~1')
            if key in ('cases', 'races') and isinstance(value, dict) and value and all(isinstance(v,dict) and 'status' in v for v in value.values()):
                yield at, value
            else:
                yield from walk(value, at)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from walk(value, pointer + '/' + str(i))


def main():
    docs = {}; entries = []
    for path in sorted(ARTIFACTS.glob('*/files/*.json')):
        if not path.name.startswith('CP7_') and path.name not in OWN:
            continue
        raw = path.read_bytes(); digest = sha256(raw).hexdigest()
        artifact = int(path.parts[-3])
        if digest in docs:
            docs[digest]['copies'].append(dict(artifact_id=artifact,path=str(path.relative_to(ROOT))))
            continue
        body = json.loads(raw)
        doc = dict(path=str(path.relative_to(ROOT)), sha256=digest, bytes=len(raw), artifact_id=artifact,
                   label=body.get('label'), status=body.get('status'), copies=[], groups=[])
        docs[digest] = doc
        for pointer, cases in walk(body):
            group = dict(pointer=pointer, cases=len(cases), counts=dict(Counter(r['status'] for r in cases.values())))
            doc['groups'].append(group)
            for ident,row in cases.items():
                entry=dict(case_id=ident,raw_status=row['status'],artifact_id=artifact,document=doc['path'],
                           document_sha256=digest,group_pointer=pointer,
                           evidence_origin='INDEPENDENT_NATIVE_RERUN',
                           oracle_origin=row.get('oracle_origin','WRITER_ACCEPTED_ORACLE_EXECUTED_BY_SOL'),
                           fixture_origin=row.get('fixture_origin','WRITER_SYNTHETIC_DISPOSABLE'),
                           case_row_sha256=sha256(json.dumps(row,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest())
                for field in ('error','traceback','full_boundary_restored','public_schema_unchanged','business_day','no_route','harness_check_failed'):
                    if field in row:entry[field]=row[field]
                entries.append(entry)
        doc['case_occurrences']=sum(g['cases'] for g in doc['groups'])
    out=dict(state='MECHANICAL_CAPTURE_LEDGER_NOT_A_PRODUCT_VERDICT',candidate_sha='17fa25075ba77f0853c3c16f504288ace03eec35',
             captured_primary_documents=len(docs),case_occurrences=len(entries),
             unique_case_id_strings=len({r['case_id'] for r in entries}),
             raw_status_counts=dict(Counter(r['raw_status'] for r in entries)),
             non_pass=[r for r in entries if r['raw_status']!='PASS'],
             documents=list(docs.values()),cases=entries,
             limits=['Byte-identical report copies count once. Different full-stack executions remain separate occurrences.',
                     'Case payloads are not recursively counted as new cases.',
                     'P21 steps and P19 measurements are reviewed separately, not invented as case IDs.',
                     'A raw PASS can be an expected refusal, a detector sensitivity control, or a measurement; it is not full acceptance.'])
    (ROOT/'CASE_LEDGER.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:out[k] for k in ['captured_primary_documents','case_occurrences','unique_case_id_strings','raw_status_counts']}))


if __name__=='__main__':main()
