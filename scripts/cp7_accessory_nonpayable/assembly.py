"""Full financial + owner-settings delta for the unchanged owning package engine.

The accepted FREE3 parent is installed by the caller. These wrappers own one
atomic delta, never a connection, commit, parent receipt or runtime default.
"""
from . import composition as financial,settings_stage as settings

USED_ERROR=settings.USED_ERROR

def parent():return financial.parent()
def runtime():return financial.runtime()
def sources():return settings.sources()
def verify(cur,state):return settings.verify(cur,state)

def install_delta(cur,qualified_FREE3):
    financial.qualification()
    _,_,_,base,_=runtime()
    with base.atomic(cur):
        return settings.install_delta(cur,financial.install_delta(cur,qualified_FREE3))

def install(cur):return settings.install(cur)

def rollback_delta_preuse(cur,state):
    financial.qualification()
    _,_,_,base,_=runtime()
    with base.atomic(cur):
        # A settings-used refusal must occur before either inverse can apply.
        owner=settings.rollback_delta_preuse(cur,state)
        money=financial.rollback_delta_preuse(cur,state['parent'])
        if owner.get('used_guard_before_DDL')is not True or money.get('used_guard_before_DDL')is not True:
            raise ValueError('NONPAYABLE_BOTH_EXACT_PREUSE_INVERSE_GUARDS_REQUIRED')
        return dict(status='NONPAYABLE_FULL_FINANCIAL_AND_SETTINGS_PREUSE_DELTA_INVERSE',
            used_guard_before_DDL=True,settings=owner,financial=money)

def rollback_preuse(cur,state):return settings.rollback_preuse(cur,state)
