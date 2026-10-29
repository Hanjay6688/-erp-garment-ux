"""Exact additive identities and existing-object boundary. No DB or network.

The identity list is rendered locally from this stage's own SQL; it is not a
capture of the qualified Native parent. Actual install captures its current
all22 catalog and derives twelve Native hooks, one private facade hook and
two clones from those actual bodies.
"""
from pathlib import Path
import json,re
from . import native_delta

HERE=Path(__file__).resolve().parent
SCHEMA=native_delta.SCHEMA
TABLES=tuple(SCHEMA+'.'+name for name in('decisions_v1','sources_v1','reversals_v1','allocations_v1','allocation_reversals_v1','requests_v1','cancel_context_v1'))
PUBLIC=('public.erp_cp7_get_attendance_choice_v1(date,date,integer,integer)',
        'public.erp_cp7_preview_attendance_choice_v1(text,jsonb)',
        'public.erp_cp7_save_attendance_choice_v1(text,jsonb,uuid)')

def declared_functions():
    result=set(native_delta.CLONES)
    for name,args in re.findall(r'create function ([a-z0-9_.]+)\(([^)]*)\)',(HERE/'choice.sql').read_text()):
        aliases={'timestamptz':'timestamp with time zone'}
        types=[aliases.get(arg.strip().split()[1],arg.strip().split()[1])for arg in args.split(',')]if args.strip()else[]
        result.add(name+'('+','.join(types)+')')
    return result

def transition(before,after,definitions):
    identities=json.loads((HERE/'NEW_CATALOG_IDENTITIES.json').read_bytes())['objects']
    if set(before)!=set(after)or len(before)!=22 or set(identities)!=set(before):raise ValueError('CP7_S03_ALL22_REQUIRED')
    if set(definitions)!=set(native_delta.SIGNATURES):raise ValueError('CP7_S03_EXACT_CAPTURE13_REQUIRED')
    if set(identities['functions'])!=declared_functions():raise ValueError('CP7_S03_DECLARED_IDENTITIES_CHANGED')
    changed=set()
    for group in before:
        additions=set(after[group])-set(before[group])
        if additions!=set(identities[group]):raise ValueError('CP7_S03_EXACT_NEW_IDENTITIES_REQUIRED:'+group)
        for key,old in before[group].items():
            new=after[group].get(key)
            if old==new:continue
            if(group=='functions'and key in definitions and new is not None
               and new[0]==definitions[key]and old[1:]==new[1:]):
                changed.add(key);continue
            raise ValueError('CP7_S03_UNDECLARED_CATALOG_DELTA:'+group+':'+key)
    if changed!=set(definitions):raise ValueError('CP7_S03_EXACT_CHANGED_CAPTURE13_REQUIRED')
