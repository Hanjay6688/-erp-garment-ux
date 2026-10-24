"""Eight retained A families on one actual current A/B installation.

No business case is copied, renamed, weakened or counted as newly authored.
Each original business module receives its real installation-time stage state. Its
side-by-side predecessor oracle therefore uses the same captured old bodies.
Only the supplier after-use callback is bound to the complete installed stack.
"""
from importlib import import_module
import cp7_p21_current_chain_rehearsal_probe as chain
import cp7_current_installation as installation
from cp7_ab_bounded_chain import composition as product

NAMES=('cp7_supplier_transfer','cp7_kasbon_source','cp7_fg_correction_source',
    'cp7_report_credit','cp7_finance_capture','cp7_ow09_lists',
    'cp7_hpp_close','cp7_laundry_unknown_wash')
FAMILIES=tuple((name,import_module(name+'.cases'),import_module(name+'.composition'))for name in NAMES)
FAMILY_IDS={name:business.IDS+(business.RETAINED if name=='cp7_supplier_transfer'else())
    for name,business,_ in FAMILIES}
IDS=tuple(case for names in FAMILY_IDS.values()for case in names)
STATE=None


def stage_state(wanted):
    state=STATE
    for _ in range(32):
        if state is None:break
        if state.get('sources')==wanted:return state
        state=state.get('predecessor')
    raise ValueError('OWNER_FAMILY_REAL_INSTALLATION_STATE_NOT_FOUND')


def used_guard(cur):
    with chain.helper.control.product_catalog(cur):
        try:installation.rollback_preuse(cur,STATE)
        except ValueError as error:assert str(error)==product.USED_ERROR,str(error)
        else:raise AssertionError('CURRENT_USED_INSTALLATION_WAS_REMOVED')
        installation.verify(cur,STATE)


def cases(cur,today):
    if STATE is None:raise ValueError('OWNER_FAMILY_INSTALLATION_REQUIRED')
    result=[]
    for name,business,owner in FAMILIES:
        installed=stage_state(owner.sources())
        # Exact bindings from the retained native_probe entry points. Import
        # business modules only: CLI probes have process-global argv effects.
        if hasattr(business,'ORIGINALS'):business.ORIGINALS=installed['originals']
        if name=='cp7_supplier_transfer':business.CHECK_USED_ROLLBACK=used_guard
        elif name=='cp7_kasbon_source':
            business.AS_OWNER=owner.predecessor.function_ddl
            business.AS_POSTGRES=owner.predecessor.predecessor.predecessor.payment.consumer.as_owner
            business.BEFORE=installed['before']
        elif name=='cp7_fg_correction_source':
            business.AS_OWNER=owner.function_ddl;business.AS_POSTGRES=owner.as_owner
            business.BEFORE=installed['before']
        elif hasattr(business,'AS_OWNER'):business.AS_OWNER=owner.as_owner
        found=business.cases(cur,today)
        if tuple(case for case,_ in found)!=FAMILY_IDS[name]:
            raise ValueError('OWNER_FAMILY_ORIGINAL_CASE_SET_CHANGED: '+name)
        result.extend(found)
    if tuple(case for case,_ in result)!=IDS or len(set(IDS))!=len(IDS):
        raise ValueError('OWNER_FAMILY_COMBINED_CASE_SET_CHANGED')
    return result
