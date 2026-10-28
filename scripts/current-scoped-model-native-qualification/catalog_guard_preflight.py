"""Local catalog/data guard controls; synthetic additions, no Native DB credit."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json, sys
_CLI_ARGS=sys.argv[1:]
sys.argv=sys.argv[:1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cp7_current_scoped_model_installation as product


def run(manifest_path):
    raw=Path(manifest_path).read_bytes(); backup=json.loads(raw)
    before=backup['catalog']; data=backup['data']; assert len(before)==22
    module=product.runtime
    after=deepcopy(before)
    after['schemas'][module.SCHEMA]=['synthetic-test-only']
    for key in module.FUNCTIONS:after['functions'][key]=['synthetic-test-only']
    for key in module.FK_TRIGGERS:after['triggers'][key]=['synthetic-test-only']
    state=dict(catalog=module.own_catalog(after))
    product.admit_catalog(before,after,state,module)
    rows=dict(data);rows[module.TABLE]=product.EMPTY
    product.admit_data(data,rows,module)
    controls=[]
    def refuses(label,op,prefix):
        try:op()
        except ValueError as error:assert str(error).startswith(prefix),str(error)
        else:raise AssertionError('GUARD_ACCEPTED_'+label)
        controls.append(label)
    changed=deepcopy(after);key=next(iter(before['functions']));changed['functions'][key]=['unauthorized']
    refuses('old_function_changed',lambda:product.admit_catalog(before,changed,state,module),'CURRENT_SCOPED_MODEL_UNDECLARED_CATALOG_DELTA')
    changed=deepcopy(after);key=next(iter(module.FK_TRIGGERS));del changed['triggers'][key]
    refuses('declared_parent_FK_missing',lambda:product.admit_catalog(before,changed,state,module),'CURRENT_SCOPED_MODEL_STAGE_CATALOG_CHANGED')
    changed=deepcopy(after);changed['triggers']['cp7_model_native.registry:unexpected']=['unauthorized']
    refuses('undeclared_parent_trigger',lambda:product.admit_catalog(before,changed,state,module),'CURRENT_SCOPED_MODEL_UNDECLARED_CATALOG_DELTA')
    changed=deepcopy(after);del changed['aggregates']
    refuses('catalog_dimension_missing',lambda:product.admit_catalog(before,changed,state,module),'CURRENT_SCOPED_MODEL_CATALOG_GROUPS_CHANGED')
    key=next(k for k in data if k.startswith('sequence:'));changed=dict(rows);changed[key]=['advanced']
    refuses('old_sequence_advanced',lambda:product.admit_data(data,changed,module),'CURRENT_SCOPED_MODEL_INSTALL_CHANGED_ROWS_OR_SEQUENCES')
    key=next(k for k in data if not k.startswith('sequence:'));changed=dict(rows);changed[key]=['changed']
    refuses('old_rows_changed',lambda:product.admit_data(data,changed,module),'CURRENT_SCOPED_MODEL_INSTALL_CHANGED_ROWS_OR_SEQUENCES')
    changed=dict(rows);changed['unexpected.table']=product.EMPTY
    refuses('undeclared_table_added',lambda:product.admit_data(data,changed,module),'CURRENT_SCOPED_MODEL_INSTALL_CHANGED_ROWS_OR_SEQUENCES')
    changed=dict(rows);changed[module.TABLE]=[1,'nonempty']
    refuses('new_table_not_empty',lambda:product.admit_data(data,changed,module),'CURRENT_SCOPED_MODEL_INSTALL_CHANGED_ROWS_OR_SEQUENCES')
    refuses('runtime_table_preexists',lambda:product.admit_data(rows,rows,module),'CURRENT_SCOPED_MODEL_INSTALL_CHANGED_ROWS_OR_SEQUENCES')
    return dict(status='PASS',scope='LOCAL_GUARD_ONLY_SYNTHETIC_NEW_CATALOG_ROWS',
      trusted_manifest_sha256=sha256(raw).hexdigest(),baseline_groups=len(before),baseline_data_keys=len(data),
      declared_parent_FK_additions=sorted(module.FK_TRIGGERS),positive_catalog_and_data_controls=2,
      negative_controls=controls,Native_runtime_qualified=False,production_go=False)


if __name__=='__main__':print(json.dumps(run(_CLI_ARGS[0]),indent=2))
