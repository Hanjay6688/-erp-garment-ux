"""Exact retained four-helper source and actual-reference compatibility only.

No installer, SQL execution or final-parent/runtime admission is provided.
All19 metadata vectors are compared; raw ACLs/OIDs are never inferred from them.
"""
from pathlib import Path
from hashlib import sha256,sha1
import json,re

HERE=Path(__file__).resolve().parent
HELPERS=HERE/'graph_helpers'
ORIGIN_HEAD='a6ded9cd4ce23a6d59cd32e42ca9bb33d793f8cc'
ORIGIN_TREE='55da7c6ab29d9bfda68962be27da0db7ad931662'
NAMES=('authority','scope','capture','inspect')


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def source():
    origin=json.loads((HERE/'READONLY_GRAPH_ORIGIN.json').read_bytes())
    if origin['head']!=ORIGIN_HEAD or origin['tree']!=ORIGIN_TREE:
        raise ValueError('GLOBAL_READONLY_EXACT_RETAINED_ORIGIN_REQUIRED')
    expected={n+'.sql'for n in NAMES}|{'AUTHORITY.json'}
    if set(origin['files'])!=expected:raise ValueError('GLOBAL_READONLY_EXACT_FIVE_RETAINED_FILES_REQUIRED')
    for name,value in origin['files'].items():
        raw=(HELPERS/name).read_bytes()
        if pin(raw)!={k:value[k]for k in('bytes','sha256')}or sha1(('blob '+str(len(raw))+'\0').encode()+raw).hexdigest()!=value['git_blob']:
            raise ValueError('GLOBAL_READONLY_EXACT_RETAINED_BLOB_CHANGED:'+name)
    authority=json.loads((HELPERS/'AUTHORITY.json').read_bytes())
    if authority['runtime_entry']is not None or authority['required_final_composition_parent']is not None:
        raise ValueError('GLOBAL_READONLY_FINAL_PARENT_NOT_ADOPTED_BY_SOURCE_COPY')
    reference=authority['actual_source_profile']
    if len(reference['functions'])!=19 or any(len(row)!=19 for row in reference['functions'].values()):
        raise ValueError('GLOBAL_READONLY_COMPLETE_ACTUAL19_BY19_REFERENCE_REQUIRED')
    text='\n'.join((HELPERS/(n+'.sql')).read_text()for n in NAMES)
    code=re.sub(r"'(?:[^']|'')*'",'STRING_LITERAL',text)
    code=re.sub(r'/\*[\s\S]*?\*/|--[^\n]*','',code)
    if re.search(r'(?i)\b(?:insert\s+into|delete\s+from|update\s+[a-z]|lock\s+table|for\s+(?:update|share))\b|\b(?:nextval|gen_random_uuid|pg_advisory\w*|set_config)\s*\(',code):
        raise ValueError('GLOBAL_READONLY_HELPER_WRITER_SEQUENCE_LOCK_OR_CONTEXT_CALL')
    names=re.findall(r'(?im)^create function\s+([a-z0-9_.]+)\(',text)
    if set(names)!={'cp7_global_nonpo_native_graph.'+n+'_v1'for n in NAMES}or len(names)!=4:
        raise ValueError('GLOBAL_READONLY_EXACT_FOUR_PRIVATE_HELPERS_REQUIRED')
    for name in names:
        start=re.search(r'(?im)^create function\s+'+re.escape(name)+r'\(',text)
        tag=re.search(r'(?i)\bas\s+(\$[a-z0-9_]*\$)',text[start.start():])
        if tag is None or not re.search(r'(?i)language\s+(?:plpgsql|sql)\s+stable\s+security\s+definer',text[start.start():start.start()+tag.start()]):
            raise ValueError('GLOBAL_READONLY_EXACT_STABLE_SECURITY_DEFINER_REQUIRED')
    forbidden={n.split('(')[0]for n,r in authority['known_functions'].items()if r['inspection_only_never_called']}
    if any(re.search(r'\b'+re.escape(n)+r'\s*\(',code)for n in forbidden):
        raise ValueError('GLOBAL_READONLY_NATIVE_AUTHORITY_ONLY_WRITER_CALLED')
    return dict(status='EXACT_RETAINED_GRAPH_HELPER4_SOURCE_NOT_FINAL_PARENT_OR_RUNTIME',
        origin_head=ORIGIN_HEAD,origin_tree=ORIGIN_TREE,exact_retained_files=5,private_STABLE_helpers=4,
        actual_reference_functions=19,attributes_per_function=19,
        final_accepted_parent_adopted=False,raw_ACLs_or_OIDs_inferred=False,
        actual_SQL_executed=0,actual_Native_cases=0,production_go=False,independent_acceptance=False)


def compare_current(catalog):
    source();reference=json.loads((HELPERS/'AUTHORITY.json').read_bytes())['actual_source_profile']
    if len(catalog)!=22:raise ValueError('GLOBAL_READONLY_ACTUAL_ALL22_REQUIRED')
    for signature,row in reference['functions'].items():
        if catalog['functions'].get(signature)!=row:
            raise ValueError('GLOBAL_READONLY_ACTUAL_FULL19_NATIVE_REFERENCE_CHANGED:'+signature)
    if catalog['relations'].get('erp.v_current_hpp')!=reference['view_relation']:
        raise ValueError('GLOBAL_READONLY_ACTUAL_NATIVE_VIEW_PROFILE_CHANGED')
    return dict(status='SAVED_CURRENT_ALL19_NATIVE_FUNCTION_ATTRIBUTES_AND_VIEW_EQUAL_RETAINED_REFERENCE',
        actual_reference_functions=19,attributes_per_function=19,view_equal=True,
        fresh_Runtime_or_final_parent_adoption=False,actual_SQL_executed=0,actual_Native_cases=0)


if __name__=='__main__':print(json.dumps(source(),sort_keys=True))
