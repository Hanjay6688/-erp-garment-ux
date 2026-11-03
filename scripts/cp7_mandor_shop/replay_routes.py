"""Two exact private replay guards; original source and models stay frozen.

Fresh allocation and buyer commands already retain the four permission-table
locks through commit. Cached allocation/save-sale outcomes bypass those fresh
paths. Lock and reread the current action access before either cached return.
This adds no role, grant, financial write or new function identity.
"""
from hashlib import sha256

ALLOCATION = dict(bytes=16985, sha256='e57c96f8289ef95cbce60b337ccba57109c4428115448526f79ed82f42b3a0c2')
FACADES = dict(bytes=12008, sha256='64d51f4afcbacf6a3d575ec72f4fd785dce520c049b43550c85defb72b615fda')
BEFORE = ' if old_.actor is not null then\n'
LOCK = '  lock table erp.app_permissions,erp.app_role_permissions,erp.app_roles,erp.app_users in share mode nowait;\n'
GUARDS = {
    'allocation.sql': LOCK + "  if cp7_mandor_shop.access_now(p_action)is distinct from a_ then\n"
        "   raise exception using errcode='42501',message='CP7_MANDOR_SHOP_ACCESS_CHANGED';end if;\n",
    'composed_facades_with_native_dispatch.sql': LOCK + "  if cp7_mandor_shop.buyer_access(p_action)is distinct from access_ then\n"
        "   raise exception using errcode='42501',message='CP7_MANDOR_SHOP_ACCESS_CHANGED';end if;\n",
}


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def derive(allocation,facades):
    originals={'allocation.sql':allocation,'composed_facades_with_native_dispatch.sql':facades.encode()}
    expected={'allocation.sql':ALLOCATION,'composed_facades_with_native_dispatch.sql':FACADES}
    derived={};routes=[]
    for name,raw in originals.items():
        if pin(raw)!=expected[name]:raise ValueError('MANDOR_REPLAY_EXACT_ORIGINAL_SOURCE_REQUIRED:'+name)
        text=raw.decode();after=BEFORE+GUARDS[name]
        if text.count(BEFORE)!=1 or after in text:raise ValueError('MANDOR_REPLAY_ONE_CACHED_RETURN_BRANCH_REQUIRED:'+name)
        changed=text.replace(BEFORE,after,1)
        if changed.count(after)!=1 or changed.replace(after,BEFORE,1).encode()!=raw:
            raise ValueError('MANDOR_REPLAY_COMPLETE_ORIGINAL_NOT_RECOVERED:'+name)
        derived[name]=changed
        routes.append(dict(file=name,before=BEFORE,after=after,count=1,original=pin(raw),derived=pin(changed.encode())))
    return derived,dict(status='TWO_PRIVATE_REPLAY_PERMISSION_LOCK_ROUTES_PREPARED_NOT_RUNTIME',routes=routes,
        exact_original_inputs_recovered=True,permission_tables_locked_before_cached_outcome=True,
        fresh_business_paths_unchanged=True,new_function_identities=0,new_roles_or_grants=0,
        actual_Native_cases=0,actual_two_session_races=0,production_go=False,independent_acceptance=False)
