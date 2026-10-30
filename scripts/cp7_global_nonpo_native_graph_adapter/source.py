"""Closed standalone SQL/source capability; no installer or financial caller."""
from pathlib import Path
from hashlib import sha256
import json
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CLOSED='CP7_GLOBAL_NONPO_RUNTIME_CLOSED_READONLY_INSPECTOR_ONLY'
SQL_FILES=('authority.sql','scope.sql','capture.sql','inspect.sql')


def runtime_entry():
    raise ValueError(CLOSED)


def function_text(text,name):
    start=re.search(r'(?im)^create\s+(?:or\s+replace\s+)?function\s+'+re.escape(name)+r'\s*\(',text)
    if start is None:
        raise ValueError('EXACT_SOURCE_FUNCTION_MISSING:'+name)
    tag=re.search(r'(?i)\bas\s+(\$[a-z0-9_]*\$)',text[start.start():])
    if tag is None:
        raise ValueError('EXACT_SOURCE_BODY_DELIMITER_REQUIRED:'+name)
    begin=start.start()+tag.end();end=text.index(tag[1],begin)
    return text[begin:end],text[start.start():end+len(tag[1])+1]


def source_contract(root=ROOT,here=HERE):
    root,here=Path(root),Path(here)
    authority=json.loads((here/'AUTHORITY.json').read_bytes())
    if authority['required_final_composition_parent']is not None or authority['runtime_entry']is not None:
        raise ValueError('NEW_EXPLICIT_RUNTIME_SUCCESSOR_REQUIRED_NOT_A_SOURCE_RESEAL')
    if authority['new_roles']or authority['new_public_RPC']or authority['production_go']is not False:
        raise ValueError('STANDALONE_READONLY_PRIVATE_PREPARATION_ONLY')
    qualifier=root/'scripts/current-global-nonpo-native-graph-qualification'
    native=(qualifier/'retained/Native_authority.sql').read_text()
    parent=(qualifier/'retained/Current_parent_readers.sql').read_text()
    for signature,pin in authority['known_functions'].items():
        name=signature.split('(')[0]
        body,full=function_text(native if name.startswith('erp.')else parent,name)
        if sha256(body.encode()).hexdigest()!=pin['prosrc_sha256']or sha256(full.encode()).hexdigest()!=pin['source_function_sha256']:
            raise ValueError('EXACT_KNOWN_SOURCE_BODY_CHANGED:'+signature)
        if pin['source'].startswith(('scripts/','supabase/')):
            raw=(root/pin['source']).read_text();live,_=function_text(raw,name)
            if live!=body:
                raise ValueError('RETAINED_BODY_NOT_ACTUAL_TRACKED_PARENT_SOURCE:'+signature)
    for name,pin in authority['parent_source_files'].items():
        raw=(root/name).read_bytes()
        if len(raw)!=pin['bytes']or sha256(raw).hexdigest()!=pin['sha256']:
            raise ValueError('EXACT_CURRENT_SOURCE_IMPORT_CHANGED:'+name)
    sql='\n'.join((here/name).read_text()for name in SQL_FILES)
    # Ignore SQL literals, including the pinned-source JSON inside authority.sql.
    code=re.sub(r"'(?:[^']|'')*'",'STRING_LITERAL',sql)
    if re.search(r'(?i)\b(insert\s+into|delete\s+from|update\s+[a-z]|lock\s+table)\b|\b(?:nextval|gen_random_uuid|pg_advisory\w*)\s*\(',code):
        raise ValueError('READONLY_INSPECTOR_WRITER_RANDOM_SEQUENCE_OR_LOCK_CALL')
    names=re.findall(r'(?im)^create function\s+([\w.]+)',sql)
    if set(names)!={f'cp7_global_nonpo_native_graph.{n}_v1'for n in('authority','scope','capture','inspect')}or len(names)!=4:
        raise ValueError('EXACT_FOUR_PRIVATE_INSPECTOR_FUNCTIONS_REQUIRED')
    for name in names:
        body,full=function_text(sql,name);header=full[:full.index(body)]
        if not re.search(r'(?i)language\s+(?:sql|plpgsql)\s+stable\s+security\s+definer',header):
            raise ValueError('ALL_INSPECTOR_FUNCTIONS_STABLE_PRIVATE_REQUIRED')
    forbidden={signature.split('(')[0]for signature,pin in authority['known_functions'].items()if pin['inspection_only_never_called']}
    if any(re.search(r'\b'+re.escape(name)+r'\s*\(',code)for name in forbidden):
        raise ValueError('AUTHORITY_ONLY_NATIVE_WRITER_OR_DISPATCHER_CALLED')
    return dict(status='EXACT_STANDALONE_READONLY_SOURCE_NOT_RUNTIME_ADMISSION',known_source_functions=len(authority['known_functions']),
        own_private_STABLE_functions=4,required_final_parent=None,runtime_entry=None,
        writer_or_phantom_lock_closed=False,actual_Native_credit=0,production_go=False,independent_acceptance=False)
