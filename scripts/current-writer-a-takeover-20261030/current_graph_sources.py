"""Exact current producer bindings, including the two new D1/E namespaces.

Historical intake registries are unchanged. Unknown producers and changed
relative file sets refuse; no matching-digest search or alternative namespace.
"""
from intake_common import exact,require
from intake_s05 import CONTRACT_DIRS,FILESET_DIRS
from intake_sku27 import literal

CURRENT={
 'cp7.credit-correction-de.v1':('cp7_credit_correction_de','composition.py',(
  'review.sql','facts.sql','owning.sql','proof.sql','posting.sql','materialize.sql','closure.sql',
  'native_delta.py','composition.py')),
 'cp7.note-credit-carry.v1':('cp7_credit_correction_de','e_composition.py',(
  'note_carry/01_facts.sql','note_carry/02_plan.sql','note_carry/03_readers.sql',
  'note_carry/04_basis.sql','note_carry/05_effect.sql','note_carry/06_owning.sql',
  'note_carry/07_profile_closure.sql','e_native_delta.py','e_composition.py')),
}


def declared_files(g,value):
    maps=0;occurrences=0;paths=set();current=set()
    def walk(item):
        nonlocal maps,occurrences
        if isinstance(item,dict):
            if isinstance(item.get('files'),dict):
                files=item['files'];maps+=1
                if all(name.startswith(('scripts/','src/','docs/','tests/','.github/','supabase/'))for name in files):
                    prefix=''
                else:
                    contract=item.get('contract')
                    if contract in CURRENT:
                        directory,producer,names=CURRENT[contract]
                        exact(tuple(files),names,'ROOT_CURRENT_EXACT_D1_E_PRODUCER_FILESET:'+contract)
                        exact(literal(g,'scripts/'+directory+'/'+producer,'CONTRACT'),contract,
                            'ROOT_CURRENT_ACTUAL_DECLARED_PRODUCER_CONTRACT')
                        current.add(contract)
                    else:
                        directory=CONTRACT_DIRS.get(contract)if contract else FILESET_DIRS.get(tuple(files))
                    require(directory is not None,'ROOT_CURRENT_UNBOUND_SOURCE_PRODUCER:'+str(contract))
                    prefix='scripts/'+directory+'/'
                for name,expected in files.items():
                    path=prefix+name;g.verify_pin(path,expected);paths.add(path);occurrences+=1
            for child in item.values():walk(child)
        elif isinstance(item,list):
            for child in item:walk(child)
    walk(value)
    return dict(file_maps=maps,pin_occurrences=occurrences,unique_paths=len(paths),
        exact_producer_namespace=True,current_D1_E_contract_bindings=sorted(current),
        historical_registry_changed=False,matching_hash_or_alternative_namespace_search=False)
