"""Unchanged OW05 Native28 plus OW05b Native6 on the current AB installation."""
from cp7_contractor_correction import native_cases as correction
import ow05_native_edge_cases as edges
import cp7_r3_rate_cases as rates
from cp7_contractor_guidance import cases as guidance,composition as guidance_product

FAMILY_IDS=dict(correction=correction.IDS,edges=edges.IDS,
    retained_rates=tuple(rates.NATIVE),guidance=guidance.IDS)
IDS=tuple(case for family in FAMILY_IDS.values()for case in family)
STATE=None


def guidance_state():
    wanted=guidance_product.sources();state=STATE
    for _ in range(32):
        if state is None:break
        if state.get('sources')==wanted:return state
        state=state.get('predecessor')
    raise ValueError('CURRENT_MANDOR_REAL_GUIDANCE_STAGE_REQUIRED')


def cases(cur,today):
    if STATE is None:raise ValueError('CURRENT_MANDOR_INSTALLATION_REQUIRED')
    stage=guidance_state()
    guidance.ORIGINALS=stage['originals'];guidance.AS_OWNER=guidance_product.as_owner
    result=correction.cases(cur,today)+edges.cases(cur,today)+rates.cases(cur,today)+guidance.cases(cur,today)
    assert tuple(name for name,_ in result)==IDS and len(set(IDS))==len(IDS)==34
    return result
