"""Retain clone comparison outputs only after all source/runtime checks finish."""
from pathlib import Path
from hashlib import sha256
import argparse,json

NAMES=('CLONE_install.source-erp.sql','CLONE_install.clone-erp.sql',
       'CLONE_install.database-identity.txt','CLONE_install.txt','CLONE_install.connection-fence.txt')

def retain(source,destination):
    source=Path(source);destination=Path(destination);destination.mkdir(parents=True,exist_ok=True);rows=[]
    for name in (*NAMES,'CLONE_install.erp.diff'):
        path=source/name
        if not path.exists():continue
        if path.is_symlink()or not path.is_file():raise ValueError('JOIN_CLONE_REGULAR_EVIDENCE_REQUIRED')
        raw=path.read_bytes();target=destination/name
        if target.exists()and target.read_bytes()!=raw:raise ValueError('JOIN_FIRST_CLONE_EVIDENCE_COLLISION')
        if target!=path:target.write_bytes(raw)
        if target.read_bytes()!=raw:raise ValueError('JOIN_CLONE_ORIGINAL_BYTES_NOT_RETAINED')
        rows.append(dict(name=name,bytes=len(raw),sha256=sha256(raw).hexdigest()))
    result=dict(status='EXACT_AVAILABLE_CLONE_ORIGINALS_RETAINED',files=rows,
        all_five_outputs_present=set(NAMES).issubset({row['name']for row in rows}),
        output_absence_is_not_PASS=True,SQL_executed_by_retainer=False,source_guard_weakened=False,actual_case_credit=0)
    (destination/'JOIN_CLONE_OUTPUTS_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--destination',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(retain(args.source,args.destination)))
