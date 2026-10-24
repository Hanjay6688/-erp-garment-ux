"""Unchanged B policy/v2/dated-target Auth and races, admitted on full A composition."""
from pathlib import Path
from hashlib import sha256
import ast,inspect
import cp7_ow11_model_policy_transport_cases as policy
import cp7_ow11_model_evaluation_v2_transport_cases as evaluation

import cp7_ow11_model_target_transport_cases as target

MODULES=dict(policy=policy,evaluation=evaluation,target=target)
GROUPS={name+'_'+kind:list(module.IDS[kind])for name,module in MODULES.items()for kind in('http','races')}
IDS=tuple(key for group in GROUPS.values()for key in group)
assert len(IDS)==len(set(IDS))==28

def source_binding():
    result={}
    for name,module in MODULES.items():
        p=Path(module.__file__);text=p.read_text();tree=ast.parse(text);bodies={}
        for factory in('races','http_cases'):
            node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==factory)
            actual=inspect.getsource(getattr(module,factory)).strip()
            assert actual==ast.get_source_segment(text,node).strip(),('RETAINED_MODEL_TRANSPORT_BODY_CHANGED',name,factory)
            bodies[factory]=sha256(actual.encode()).hexdigest()
        result[name]=dict(path='scripts/'+p.name,file_sha256=sha256(p.read_bytes()).hexdigest(),factory_body_sha256=bodies)
    return dict(retained=result,excluded_component_catalog_anchors=[m.IDS['native'][0]for m in MODULES.values()],
        original_28_business_cases_unchanged=True,only_setup_hooks=['policy.native.install','evaluation.native.install','target.qualified.install'])
