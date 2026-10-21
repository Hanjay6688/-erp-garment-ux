"""Source-owned Native trigger validator. Importing never connects.

Only the atomic owning installer may capture and validate its known phase.
Runtime equality is installed only after that source validation succeeds.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAPTURE_SQL = (HERE/'capture.sql').read_text()
SEMANTIC_FK = ('relation','columns','parent','parent_columns','update_action',
    'delete_action','match_type','deferrable','initially_deferred','validated')


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)


def fk_key(value):
    return canonical({k:value[k]for k in SEMANTIC_FK})


def fail(reason, detail=''):
    raise ValueError('OW04_BOUNDED_TRIGGER_GUARD_' + reason + (': '+str(detail)if detail else''))


def declarations(repo):
    manifest=json.loads((HERE/'SOURCE_PINS.json').read_text())
    for name,want in manifest['repository_source_pins'].items():
        if sha256((Path(repo)/name).read_bytes()).hexdigest()!=want:
            fail('REPOSITORY_SOURCE_CHANGED',name)
    return manifest


def render_runtime_guard(snapshot, manifest, phase_name, expected_sha256_pg):
    # Never bless a raw first capture: source-owned ordinary functions,
    # attachments, FK semantics and RI built-ins must all be valid first.
    validate_source(snapshot,manifest,phase_name)
    if not isinstance(expected_sha256_pg,str)or len(expected_sha256_pg)!=64 or any(c not in '0123456789abcdef'for c in expected_sha256_pg):
        fail('RUNTIME_POSTGRES_CAPTURE_SHA256_REQUIRED')
    query=CAPTURE_SQL.strip().removesuffix(';')
    delimiter='$ow04_source_trigger_runtime$'
    if delimiter in query:
        fail('RUNTIME_SQL_DELIMITER')
    tables=','.join(sorted(manifest['tables']))
    return ("create or replace function cp7_credit.assert_source_native_trigger_census_v1()returns void\n"
        "language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as "+delimiter+"\n"
        "declare actual_sha256 text;begin\n"
        # Compatible with ordinary DML, conflicting with CREATE/DROP TRIGGER
        # and table-rewriting DDL for the rest of this source transaction.
        " lock table "+tables+" in row exclusive mode;\n"
        " select cp7_credit.pg_jsonb_sha256(q.value)into actual_sha256 from("+query+")q(value);\n"
        " if actual_sha256 is distinct from '"+expected_sha256_pg+"'then\n"
        "  raise exception 'CP7_CREDIT_SOURCE_NATIVE_TRIGGER_CENSUS_CHANGED';end if;\n"
        "end "+delimiter+";\n"
        "alter function cp7_credit.assert_source_native_trigger_census_v1()owner to postgres;\n"
        "revoke all on function cp7_credit.assert_source_native_trigger_census_v1()from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;\n")


def capture(cur):
    # Caller must use existing catalog_path: PostgreSQL deparsing depends on
    # search_path. This check does not change role, commit, or create a scope.
    if cur.execute('show search_path').fetchone()[0] not in ('', '""'):
        fail('CATALOG_SEARCH_PATH_REQUIRED')
    return cur.execute(CAPTURE_SQL).fetchone()[0]


def _index(rows,key):
    found={}
    for row in rows:
        k=key(row)
        if k in found:fail('DUPLICATE_IDENTITY',k)
        found[k]=row
    return found


def _counter_difference(actual,expected):
    return dict(missing=[dict(identity=k,count=n)for k,n in(expected-actual).items()],
                unknown=[dict(identity=k,count=n)for k,n in(actual-expected).items()])


def _ordinary_functions(snapshot, phase):
    wanted={x['identity']:x for x in phase['functions']}
    actual=_index(snapshot['functions'],lambda r:r['identity'])
    attached={x['function']for x in snapshot['triggers']if not x['internal']}
    if attached != set(wanted):fail('ORDINARY_FUNCTION_SET',sorted(attached^set(wanted)))
    for identity,expected in wanted.items():
        got=actual.get(identity)
        if got is None:fail('FUNCTION_MISSING',identity)
        for key in ('owner','language','security_definer','volatility','config',
                    'result','input_arguments','body_sha256'):
            if got[key]!=expected[key]:fail('FUNCTION_'+key.upper(),identity)
        if sorted(got['acl'],key=canonical)!=sorted(expected['acl'],key=canonical):
            fail('FUNCTION_ACL',dict(function=identity,expected=expected['acl'],actual=got['acl']))
        if expected['definition_sha256']is not None and got['definition_sha256']!=expected['definition_sha256']:
            fail('FUNCTION_DEFINITION',identity)
        if sha256(got['definition'].encode()).hexdigest()!=got['definition_sha256']or sha256(got['body'].encode()).hexdigest()!=got['body_sha256']:
            fail('FUNCTION_CAPTURE_HASH',identity)
        # These are the declared/default CREATE FUNCTION attributes of all18
        # reviewed no-argument PL/pgSQL trigger functions, not live-inferred.
        raw=got['proc_raw']
        defaults={'prokind':'f','proretset':False,'proisstrict':False,'proleakproof':False,
                  'proparallel':'u','procost':100,'prorows':0,'pronargs':0,'pronargdefaults':0,
                  'proargnames':None,'proargmodes':None,'proallargtypes':None,'probin':None,
                  'prosqlbody':None}
        for key,expected_value in defaults.items():
            if raw.get(key)!=expected_value:fail('FUNCTION_UNDECLARED_ATTRIBUTE',identity+' '+key)
        if str(raw.get('prosupport'))not in ('0','-'):fail('FUNCTION_SUPPORT',identity)
    return actual


def _ri_expected(manifest, phase):
    target=set(manifest['tables']);out=Counter()
    action={'a':'noaction','r':'restrict','c':'cascade','n':'setnull','d':'setdefault'}
    for fk in phase['foreign_keys']:
        key=fk_key(fk)
        if fk['relation']in target:
            for event,typ in (('ins',5),('upd',17)):
                out[(fk['relation'],key,'pg_catalog.RI_FKey_check_'+event+'()',typ,
                    fk['deferrable'],fk['initially_deferred'],fk['parent'])]+=1
        if fk['parent']in target:
            for event,typ,kind in (('del',9,'delete_action'),('upd',17,'update_action')):
                code=fk[kind]
                deferred=fk['deferrable']if code=='a'else False
                initially=fk['initially_deferred']if code=='a'else False
                out[(fk['parent'],key,'pg_catalog.RI_FKey_'+action[code]+'_'+event+'()',
                    typ,deferred,initially,fk['relation'])]+=1
    return out


def validate_source(snapshot, manifest, phase_name):
    if phase_name not in manifest['phases']:fail('PHASE',phase_name)
    phase=manifest['phases'][phase_name]
    rels=_index(snapshot['relations'],lambda r:r['relation'])
    if set(rels)!=set(manifest['tables']):fail('RELATION_SET')
    for rel,row in rels.items():
        if row['owner']!='postgres'or row['kind']!='r'or row['relispartition']or row['relhasrules']:
            fail('RELATION_METADATA_OR_RULES',rel)
    # No tgenabled='O' filtering: disabled or replica-only unknowns also fail.
    wanted={(x['relation'],x['name']):x for x in manifest['ordinary_triggers']}
    actual=_index([x for x in snapshot['triggers']if not x['internal']],lambda r:(r['relation'],r['name']))
    if set(actual)!=set(wanted):fail('ORDINARY_ATTACHMENT_SET',sorted(set(actual)^set(wanted)))
    skip={'source'}
    for key,expected in wanted.items():
        for field,value in expected.items():
            if field not in skip and actual[key].get(field)!=value:
                fail('ORDINARY_ATTACHMENT_FIELD',str(key)+' '+field)
    functions=_ordinary_functions(snapshot,phase)
    actual_fks=Counter(fk_key(r['semantic'])for r in snapshot['foreign_keys'])
    expected_fks=Counter(fk_key(r)for r in phase['foreign_keys'])
    if actual_fks!=expected_fks:
        fail('FOREIGN_KEY_SOURCE_CENSUS',_counter_difference(actual_fks,expected_fks))
    internals=[]
    for tr in snapshot['triggers']:
        if not tr['internal']:continue
        if tr['enabled']!='O'or tr['argument_count']!=0 or tr['args_hex']!=''or tr['columns']or tr['condition']is not None or tr['old_table']is not None or tr['new_table']is not None or tr['parent_trigger']is not None:
            fail('INTERNAL_TRIGGER_SHAPE',tr['name'])
        c=tr['constraint']
        if not c or c['type']!='f'or not c['semantic']:fail('UNKNOWN_INTERNAL_CONSTRAINT',tr['name'])
        fn=functions.get(tr['function'])
        if fn is None or not tr['function'].startswith('pg_catalog.RI_FKey_')or fn['language']!='internal'or fn['owner']!='postgres'or fn['security_definer']or fn['config']or fn['input_arguments']or fn['result']!='trigger':
            fail('UNKNOWN_INTERNAL_FUNCTION',tr['function'])
        # Pin the actual built-in C entry name as well as its qualified SQL
        # identity; a user-created PL/pgSQL function cannot masquerade here.
        if fn['body']!=tr['function'].split('.',1)[1][:-2]:fail('RI_INTERNAL_ENTRY_POINT',tr['function'])
        internals.append((tr['relation'],fk_key(c['semantic']),tr['function'],tr['trigger_type'],
            tr['deferrable'],tr['initially_deferred'],tr['referenced_relation']))
    expected_internals=_ri_expected(manifest,phase)
    if Counter(internals)!=expected_internals:
        fail('INTERNAL_ATTACHMENT_SOURCE_CENSUS',_counter_difference(Counter(internals),expected_internals))
    attached={x['function']for x in snapshot['triggers']}
    if set(functions)!=attached:fail('FUNCTION_CAPTURE_SET')
    return dict(phase=phase_name,ordinary_attachments=len(actual),ordinary_functions=len(phase['functions']),
        internal_attachments=len(internals),foreign_keys=len(phase['foreign_keys']),
        capture_sha256=sha256(canonical(snapshot).encode()).hexdigest(),
        classification='SOURCE_AND_METADATA_ONLY_NOT_NATIVE_EXECUTION')


def verify_unchanged(snapshot, recorded, manifest, phase_name):
    proof=validate_source(snapshot,manifest,phase_name)
    validate_source(recorded,manifest,phase_name)
    # Full raw capture includes all OIDs, definitions, constraints, pg_proc
    # fields and ACLs. Portable source equality alone is insufficient here.
    if snapshot!=recorded:fail('RECORDED_CATALOG_CHANGED')
    return proof


def expected_transition(before,after,manifest,before_phase,after_phase):
    """Install/uninstall known phase delta; never bless live differences.

    Only the one source-derived opening-return function target may change
    definition/body. Adding/removing private OW04 FK attachments is allowed
    only by each phase's exact source-owned FK set. Existing raw attachments,
    functions and constraints must survive unchanged, including their OIDs.
    """
    validate_source(before,manifest,before_phase)
    validate_source(after,manifest,after_phase)
    common_fk_semantics={fk_key(x)for x in manifest['phases'][before_phase]['foreign_keys']} & \
        {fk_key(x)for x in manifest['phases'][after_phase]['foreign_keys']}
    for semantic in common_fk_semantics:
        # Semantic equality cannot authorize DROP/CREATE of an old FK. Its
        # constraint OID/name and every old RI attachment must also survive.
        for collection,semantic_of in (
            ('foreign_keys',lambda r:fk_key(r['semantic'])),
            ('triggers',lambda r:fk_key(r['constraint']['semantic'])if r['internal']else None),
        ):
            old_rows=Counter(canonical(r)for r in before[collection]if semantic_of(r)==semantic)
            new_rows=Counter(canonical(r)for r in after[collection]if semantic_of(r)==semantic)
            if old_rows!=new_rows:
                fail('PREEXISTING_FK_OR_RI_RECREATED',collection+' '+semantic)
    changed='erp.sync_opening_hpp_after_return_status()'
    for name,keyfn in (('relations',lambda r:r['relation']),('triggers',lambda r:r['trigger_oid']),
                       ('functions',lambda r:r['identity']),('foreign_keys',lambda r:r['oid'])):
        old=_index(before[name],keyfn);new=_index(after[name],keyfn)
        for key in set(old)&set(new):
            if name=='functions'and key==changed:
                x=deepcopy(old[key]);y=deepcopy(new[key])
                for f in ('definition','definition_sha256','body','body_sha256'):
                    x.pop(f,None);y.pop(f,None)
                x['proc_raw'].pop('prosrc',None);y['proc_raw'].pop('prosrc',None)
                if x!=y:fail('OPENING_FUNCTION_METADATA_DELTA')
            elif old[key]!=new[key]:fail('UNDECLARED_PHASE_METADATA_DELTA',str(key))
        if name in ('relations','functions')and set(old)!=set(new):fail('PHASE_IDENTITY_DELTA',name)
        # Ordinary trigger OIDs must remain the same across phase changes.
        if name=='triggers':
            ordinary_old={r['trigger_oid']for r in old.values()if not r['internal']}
            ordinary_new={r['trigger_oid']for r in new.values()if not r['internal']}
            if ordinary_old!=ordinary_new:fail('ORDINARY_TRIGGER_RECREATED')
    return dict(before=before_phase,after=after_phase,source_validated=True)
