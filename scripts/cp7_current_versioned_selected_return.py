"""Apply the exact selected-customer correction after the versioned target layer.

The same proven delta keeps every original authority/catalog field and every
row/sequence. The composer verifies the actual prior prefix before this stage.
"""
from hashlib import sha256
from pathlib import Path
import cp7_selected_return_customer_delta as delta

CONTRACT='cp7.current-versioned-selected-return-stage.v1'
FUNCTIONS={}
SCHEMAS=()


def verify_sources():
    return dict(contract=CONTRACT,adapter_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),delta=delta.sources())


def admit_catalog(before,after,state):
    if(state['sources']!=verify_sources()or before!=state['delta']['before']or after!=state['delta']['after']
       or after!=delta.expected(before)):
        raise ValueError('CURRENT_VERSIONED_SELECTED_RETURN_UNDECLARED_CATALOG_DELTA')


def verify(cur,state):
    if state['sources']!=verify_sources():raise ValueError('CURRENT_VERSIONED_SELECTED_RETURN_SOURCE_CHANGED')
    proof=delta.verify(cur,state['delta'])
    return dict(stage=CONTRACT,selected_return=proof,new_private_functions=0,new_schemas=0,existing_replacements=1,
        unchanged_authority_and_all_other_catalog_fields=True,production_go=False)


def install_delta(cur,predecessor_checker):
    if not callable(predecessor_checker):raise ValueError('CURRENT_VERSIONED_SELECTED_RETURN_PARENT_REQUIRED')
    predecessor_checker(cur)
    state=dict(sources=verify_sources(),delta=delta.install_delta(cur))
    verify(cur,state);return state


def rollback_preuse(cur,state):
    verify(cur,state)
    return delta.rollback_preuse(cur,state['delta'])
