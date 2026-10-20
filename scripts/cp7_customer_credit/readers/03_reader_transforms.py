"""Exact current-reader deltas. Pure derivation only, never an installer.

The owning installer must first verify its trusted predecessor stack. Captured
function/view definitions and metadata must match that approved manifest; this
module never turns an unverified capture into its own approval. Existing history
event/count readers remain unchanged. New private helper has no app capability.
"""
from hashlib import sha256


def digest(text):
    return sha256(text.encode()).hexdigest()


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('CP7_CREDIT_READER_EXACT_PREDECESSOR_CHANGED: ' + old[:90])
    return text.replace(old, new, 1)


def header_body(body):
    # MATERIALIZED is inside the guarded scalar branch: nonfinancial calls do
    # not invoke the privileged core. E is calculated once per requested header.
    old = "||case when p_financial then (select jsonb_build_object('financial',jsonb_build_object("
    new = ("||case when p_financial then (with credit_effective as materialized("
           "select gross,returned,paid+erp._cp7_current_credit_adjustment(h.id) paid from amounts)"
           " select jsonb_build_object('financial',jsonb_build_object(")
    changed = once(body, old, new)
    return once(changed, " from amounts) else '{}'::jsonb end", " from credit_effective) else '{}'::jsonb end")


def summary_body(body):
    return once(body, 'with inv as(select * from cp7_customer_history.invoices(p_customer)),',
                'with inv as(select * from cp7_credit.customer_history_invoices(p_customer,p_financial)),')


def workspace_body(body):
    return once(body, 'from cp7_customer_history.invoices(v_cust.id)i',
                'from cp7_credit.customer_history_invoices(v_cust.id,v_financial)i')


def receivables_view(select_definition):
    # Exact current Native view has three uses of this raw-P expression. Keep
    # its joins, security_invoker, columns, row visibility and existing ACLs.
    old = 'COALESCE(p.paid_amount, 0::numeric)'
    if select_definition.count(old) != 3:
        raise ValueError('CP7_CREDIT_RECEIVABLE_VIEW_PREDECESSOR_CHANGED')
    return select_definition.replace(old, '(' + old + ' + erp._cp7_receivable_credit_adjustment(sh.id))')


TRANSFORMS = {
    'cp7_sales.header(erp.sales_headers,boolean)': header_body,
    'cp7_customer_history.summary(uuid,boolean)': summary_body,
    'cp7_customer_history.workspace(jsonb)': workspace_body,
}


def derive(captured, approved):
    """Metadata approval is independently supplied by the trusted whole build."""
    identity = captured['identity']
    if identity not in TRANSFORMS or approved['identity'] != identity:
        raise ValueError('CP7_CREDIT_READER_UNEXPECTED_IDENTITY')
    actual = {k: captured[k] for k in ('identity', 'owner', 'acl', 'security_definer', 'volatility', 'config')}
    actual.update(definition_sha256=digest(captured['definition']), body_sha256=digest(captured['body']))
    if actual != approved:
        raise ValueError('CP7_CREDIT_READER_UNAPPROVED_SOURCE_OR_METADATA')
    if captured['body'] not in captured['definition']:
        raise ValueError('CP7_CREDIT_READER_BODY_NOT_CAPTURED')
    changed = TRANSFORMS[identity](captured['body'])
    definition = once(captured['definition'], captured['body'], changed)
    return definition, {**approved, 'target_definition_sha256': digest(definition),
                        'target_body_sha256': digest(changed), 'Native_execution_proven': False}


HISTORY_HELPER_SQL = r"""
create function cp7_credit.customer_history_invoices(p_customer uuid,p_financial boolean)
returns table(sale_id uuid,sale_number text,sale_date timestamptz,due_date date,sale_status text,location_id uuid,
 qty_pcs bigint,line_count bigint,gross numeric,returned numeric,paid numeric,net numeric,open_balance numeric,state text)
language sql stable security definer set search_path=''as $$
 with original as materialized(select *from cp7_customer_history.invoices(p_customer)),
 adjusted as materialized(select original.*,
  case when p_financial then erp._cp7_current_credit_adjustment(sale_id)else 0::numeric end credit_adjustment
  from original)
 select sale_id,sale_number,sale_date,due_date,sale_status,location_id,qty_pcs,line_count,gross,returned,
  paid+credit_adjustment,net,
  case when state='ACTIVE_RECEIVABLE'then open_balance-credit_adjustment else open_balance end,state
 from adjusted
$$;
alter function cp7_credit.customer_history_invoices(uuid,boolean)owner to postgres;
revoke all on function cp7_credit.customer_history_invoices(uuid,boolean)
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_customer_history_read;
"""
