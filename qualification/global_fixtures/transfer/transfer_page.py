"""Extend the pinned transfer-page binding with its ordinary access oracle."""

from hashlib import sha256
from pathlib import Path
from types import ModuleType


REBIND_SHA = '3d645ff00268175db58ae2c7d94389e0b4547828b841a84f7a5eb74d8b2c886f'
PRIVATE_PERMISSION_ROUTE = '''    actor, role = cur.execute("""
        select auth.uid()::text, erp.current_app_role()
        where erp.has_permission('warehouse.procurement.view') and erp.has_permission('finance.ap.view')
          and erp.has_permission('finance.ap.pay')
    """).fetchone() or (None, None)
    cases.b.api.admin(cur)
    require(actor == str(cases.auth.base.OPERATOR_AUTH) and role in ("OWNER", "ADMIN"),
            CASE + "_SEEDED_NATIVE_ACTOR_AND_EFFECTIVE_PERMISSIONS_REQUIRED")'''
PUBLIC_PERMISSION_ROUTE = '''    access, = cur.execute("select public.erp_get_my_access_v1()").fetchone()
    cases.b.api.admin(cur)
    profile = access.get("profile", {})
    actor, role = profile.get("auth_user_id"), profile.get("role_code")
    permission_keys = {"warehouse.procurement.view", "finance.ap.view", "finance.ap.pay"}
    require(access.get("allowed") is True
            and actor == str(cases.auth.base.OPERATOR_AUTH) and role in ("OWNER", "ADMIN")
            and permission_keys <= set(access.get("permissions", ())),
            CASE + "_SEEDED_NATIVE_ACTOR_AND_EFFECTIVE_PERMISSIONS_REQUIRED")'''
OBSERVER_TIME_ROUTE = (
    '''                require(all(before[key] == after[key] for key in ("backend_start", "query_start", "reader_xmin"))
                        and wait_before["wait_start"] == wait_after["wait_start"] and writer_xids,''',
    '''                require(all(stamp(before[key]) == stamp(after[key]) for key in ("backend_start", "query_start"))
                        and before["reader_xmin"] == after["reader_xmin"]
                        and stamp(wait_before["wait_start"]) == stamp(wait_after["wait_start"]) and writer_xids,''',
)


def load_binding(base_path):
    """Load only the checked bytes of the existing source adapter."""
    path = Path(base_path).absolute()
    raw = path.read_bytes()
    if path.is_symlink() or sha256(raw).hexdigest() != REBIND_SHA:
        raise ValueError('OW06_TRANSFER_PAGE_BASE_BINDING_CHANGED')
    binding = ModuleType('ow06_transfer_page_binding')
    binding.__file__ = str(path)
    exec(compile(raw, str(path), 'exec', dont_inherit=True), vars(binding))
    binding.ROUTES = (*binding.ROUTES, (PRIVATE_PERMISSION_ROUTE, PUBLIC_PERMISSION_ROUTE))
    return binding


def bind(audit, base_path):
    binding = load_binding(base_path)
    page = binding.bind(audit)
    path = Path(audit).absolute() / binding.OBSERVER
    raw = binding.exact(path, binding.OBSERVER_SHA)
    before, after = OBSERVER_TIME_ROUTE
    text = raw.decode()
    binding.require(text.count(before) == 1 and after not in text, 'OW06_TRANSFER_PAGE_OBSERVER_TIME_ROUTE_CHANGED')
    derived = text.replace(before, after, 1)
    binding.require(derived.replace(after, before, 1).encode() == raw, 'OW06_TRANSFER_PAGE_OBSERVER_INVERSE_CHANGED')
    logic = page.observe.__globals__
    logic['__file__'] = str(path)
    exec(compile(derived, str(path), 'exec', dont_inherit=True), logic)
    # The observer's exception and function identities must stay shared with the page.
    for name in ('Refusal', 'require', 'begin', 'idle', 'observe', 'reply_bytes'):
        setattr(page, name, logic[name])
    return page
