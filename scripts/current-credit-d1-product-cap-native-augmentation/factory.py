"""Public adapter: private business proxy, same13 IDs, only MULTI augmented."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util

HERE = Path(__file__).resolve().parent
TARGET = 'D_MULTIFAMILY_ORDINAL'


def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


guard=load('d1_cap_native_source_guard',HERE/'guard.py')
prelude=load('d1_cap_native_actual_preludes',HERE/'prelude.py')


def wrap(callbacks, ids, operation):
    if tuple(key for key,_ in callbacks) != tuple(ids) or len(ids) != len(set(ids)) or len(ids) != 13:
        raise ValueError('D1_CAP_NATIVE_EXACT13_CALLBACKS_REQUIRED')
    if len(ids) != 13 or list(ids).count(TARGET) != 1:
        raise ValueError('D1_CAP_NATIVE_EXACT13_CALLBACKS_REQUIRED')
    result=[]
    for key, original in callbacks:
        if key != TARGET:
            result.append((key,original));continue
        def augmented(original=original):
            evidence=operation()
            row=original()
            assert isinstance(row,dict) and row.get('status')=='PASS'
            assert 'product_cap_native_augmentation' not in row
            return dict(row,product_cap_native_augmentation=evidence)
        result.append((key,augmented))
    return result


def business(retained_business_module):
    source,api=guard.admit()
    guard.module(retained_business_module,'retained',api)
    if list(retained_business_module.IDS)!=source['original_Native13_ids']:
        raise ValueError('D1_CAP_NATIVE_ORIGINAL_IDS_CHANGED')
    def cases(cur,today):
        original=retained_business_module.cases(cur,today)
        return wrap(original,retained_business_module.IDS,
                    lambda:prelude.run(cur,today,retained_business_module,source,api))
    # Original functions retain their original globals and code identities.
    # No attribute on the supplied module or any imported fixture is changed.
    values=dict(vars(retained_business_module));values['cases']=cases
    return SimpleNamespace(**values)
