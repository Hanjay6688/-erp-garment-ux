"""Admit each exact B report schema; source-v2 uses source_v2_sha256."""
from hashlib import sha256

MAPS={
    'MODEL_SELECTION_ORIGINAL_REPORT':{'selection_source_sha256':7},
    'PHYSICAL_BINDING_ORIGINAL_REPORT':{'binding_source_sha256':6},
    'MODEL_TARGET_SOURCE_V2_ORIGINAL_REPORT':{'source_v2_sha256':19},
    'MODEL_TARGET_CONSUMER_V2_ORIGINAL_REPORT':{'target_v2_source_sha256':33},
    'MODEL_TARGET_BROWSER_V2_ORIGINAL_REPORT':{'target_v2_source_sha256':50},
    'MODEL_TARGET_TRANSPORT_V2_A_ORIGINAL_REPORT':{'target_v2_source_sha256':36,'partition_source_sha256':2},
    'MODEL_TARGET_TRANSPORT_V2_B_ORIGINAL_REPORT':{'target_v2_source_sha256':36,'partition_source_sha256':2},
}


def verify(repo,variable,actual):
    expected=MAPS[variable]
    observed={key:value for key,value in actual.items()if isinstance(value,dict)and 'source'in key and key.endswith('sha256')}
    assert set(observed)==set(expected),('COMPONENT_SOURCE_FIELDS_CHANGED',variable,sorted(observed))
    result={}
    for key,count in expected.items():
        values=observed[key];assert len(values)==count,('COMPONENT_SOURCE_PIN_COUNT_CHANGED',variable,key)
        for path,digest in values.items():
            relative=path if path.startswith(('scripts/','src/'))else'scripts/'+path
            assert sha256((repo/relative).read_bytes()).hexdigest()==digest,(variable,key,relative)
        result[key]=count
    return result
