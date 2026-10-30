"""Complete sequence prefixes, never per-savepoint sequence restoration."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import re
import traceback
import uuid

ROOT=Path(__file__).resolve().parents[2]

def sequences(data):
    result={k:deepcopy(v)for k,v in data.items()if k.startswith('sequence:')}
    if len(result)!=15:raise ValueError('SKU27_EXACT_CURRENT_FIFTEEN_SEQUENCES_REQUIRED')
    return result

def prefix(before,after):
    if set(before)!=set(after):raise ValueError('SKU27_SEQUENCE_SET_CHANGED')
    changes={}
    for name in before:
        a,b=before[name],after[name]
        if not(isinstance(a,list)and isinstance(b,list)and len(a)==len(b)==2
          and isinstance(a[0],str)and isinstance(b[0],str)and type(a[1])is bool and type(b[1])is bool):
            raise ValueError('SKU27_SEQUENCE_RAW_ABI_CHANGED')
        if int(b[0])<int(a[0])or(a[1]and not b[1])or(not a[1]and not b[1]and a!=b):
            raise ValueError('SKU27_SEQUENCE_RESEED_OR_UNATTRIBUTED_REWIND')
        if a!=b:changes[name]=dict(before=a,after=b,last_value_delta=str(int(b[0])-int(a[0])))
    return dict(before=deepcopy(before),after=deepcopy(after),changed=changes,
      all_current_sequences_recorded=True,per_case_sequence_restore_claim=False,
      full_sequence_restoration_owned_by='FULL_OUTER_DATABASE_BACKUP_RESTORE_AND_ALL_FIVE_PACKAGE_GATES')

def strict_rollback(before,after):
    if before['catalog']!=after['catalog']:raise ValueError('SKU27_STRICT_ROLLBACK_CATALOG_CHANGED')
    a,b=before['data'],after['data']
    if {k:v for k,v in a.items()if not k.startswith('sequence:')}!={k:v for k,v in b.items()if not k.startswith('sequence:')}:
        raise ValueError('SKU27_STRICT_ROLLBACK_ALL_TABLE_ROWS_CHANGED')
    return dict(all22_equal=True,all_current_table_rows_equal=True,sequence_prefix=prefix(sequences(a),sequences(b)))

def wrap(cases,n):
    def tracked(name,operation):
        def invoke():
            if not re.fullmatch('[A-Z0-9_]+',name):raise ValueError('SKU27_CASE_ID_REQUIRED')
            before=sequences(n.capture_current()['data_and_sequences'])
            failure=None
            try:result=operation()
            except Exception as error:
                failure=dict(error=type(error).__name__+':'+str(error),traceback=traceback.format_exc())
                raise
            finally:
                observation_error=None
                try:after=sequences(n.capture_current()['data_and_sequences'])
                except Exception as error:
                    after=None;observation_error=error
                observation=dict(case_id=name,before=before,after=after,first_failure=failure,
                  observation_error=None if observation_error is None else str(observation_error),
                  per_savepoint_sequence_restore_claim=False,full_restore_required=True)
                path=ROOT/'cp6-proof/t3'/('SKU27_SEQUENCE_PREFIX_'+name+'_'+uuid.uuid4().hex+'.json')
                path.parent.mkdir(parents=True,exist_ok=True)
                raw=(json.dumps(observation,indent=2,sort_keys=True,default=str)+'\n').encode();path.write_bytes(raw)
                if failure is None and observation_error is not None:raise observation_error
            return dict(result,complete_case_sequence_prefix=prefix(before,after),
              complete_case_sequence_raw=dict(path=str(path.relative_to(ROOT)),bytes=len(raw),sha256=sha256(raw).hexdigest()))
        return name,invoke
    return[tracked(name,operation)for name,operation in cases]
