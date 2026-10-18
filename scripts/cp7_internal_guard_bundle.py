"""R4-05 (owner D17-1): erp.require_internal() answers the common case with one context probe.

Diagnosis (CI run 39157467151, function counters of one direct capture at 100 targets): the protected owner report
calls erp.require_internal() about 32,000 times per capture with financial figures (erp.account_id per checked row),
and the CP7 stack had grown the guard to one query per private command context table (ten). The guard alone took
3.9 s of the capture's 6.3 s server time; at 300 targets the capture with figures stopped at the 8 s limit.

Every branch between the service-role line and the final role test is (checked below, one CASE and nothing else)
  if exists(select 1 from <context> c where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current()
   and case when <the same two identity filters> and ... then <checks> else false end) then return;end if;
It can only admit, and only through a row of this backend and transaction: the identity filters are repeated inside
its CASE, so no check (and no fine refusal raised by one) runs for any other row. With no such row in any of those
tables every branch admits nothing and the guard's answer is the final role test alone. That case is now answered
first: a transaction without a transaction id has inserted nothing, so it has no such row (each command writes its
row with txid_current(), which a new id never equals); otherwise one probe of the same tables with the same identity
filters decides (local PG16: 103 -> 18 us per call without an id, 42 us with one). With any row present the unchanged dispatch
runs, so every check and every fine refusal keeps its place. Nothing is cached and no grant changes. Install patches
the definition after a hash check of the body in place (like every earlier delta of this guard); uninstall restores the
Native guard through the `originals` every F03 installer already replays.
"""
import hashlib
import re

import cp7_sales_bundle as sales

ANCHOR = sales.EARLY_ANCHOR
FALLBACK = (" v_app_role:=erp.current_app_role();\n"
            " if coalesce(v_app_role,'') not in('OWNER','ADMIN','STAFF') then raise exception 'Internal ERP access required';end if;\nend")
MARK = '-- R4-05 one context probe'
BRANCH = re.compile(r"\s*if exists\(select 1 from ([a-z0-9_]+\.[a-z0-9_]*context) c where c\.backend_pid=pg_backend_pid\(\)\s+"
                    r"and c\.transaction_id=txid_current\(\) and case when c\.backend_pid=pg_backend_pid\(\)\s+"
                    r"and c\.transaction_id=txid_current\(\) and (?:(?!\bend\b).)*?\s+else false end\) then return;end if;", re.S)
COMMENT = re.compile(r'^[ \t]*--.*$', re.M)


def contexts(definition):
    """The context tables of the dispatch, after proving it holds nothing but admitting context branches."""
    assert definition.count(ANCHOR) == 1 and definition.count(FALLBACK) == 1 and MARK not in definition, 'CP7_INTERNAL_GUARD_SHAPE_CHANGED'
    dispatch = definition.split(ANCHOR, 1)[1].split(FALLBACK, 1)[0]
    rest = COMMENT.sub('', BRANCH.sub('', dispatch))
    tables = list(dict.fromkeys(BRANCH.findall(dispatch)))
    assert tables and not rest.strip(), ('CP7_INTERNAL_GUARD_DISPATCH_CHANGED', rest.strip()[:300])
    return tables


def probe(tables):
    rows = '\n  union all '.join('select 1 from %s x where x.backend_pid=pg_backend_pid() and x.transaction_id=txid_current()' % t
                                for t in tables)
    return (' ' + MARK + ' (scripts/cp7_internal_guard_bundle.py): without a private command context row of this\n'
            ' -- backend and transaction no branch below admits; only the final role test decides. A transaction that has\n'
            ' -- no transaction id yet has written no row (a context row carries the id of the transaction that wrote it).\n'
            ' if txid_current_if_assigned() is null or not exists(' + rows + ')then\n'
            "  if coalesce(erp.current_app_role(),'') not in('OWNER','ADMIN','STAFF') then raise exception 'Internal ERP access required';end if;\n"
            '  return;\n'
            ' end if;')


def patched_internal(definition):
    return definition.replace(ANCHOR, ANCHOR + '\n' + probe(contexts(definition)), 1)


def extension(body_before):
    """The install delta; body_before is the guard body the F03 stack leaves in place (checked by hash)."""
    old_hash = hashlib.sha256(body_before.encode()).hexdigest()
    return """do $patch$ declare d text;begin
 if(select encode(extensions.digest(prosrc,'sha256'),'hex') from pg_proc where oid='erp.require_internal()'::regprocedure)<>'%s' then raise exception 'CP7_INTERNAL_GUARD_PREDECESSOR_CHANGED';end if;
 d:=pg_get_functiondef('erp.require_internal()'::regprocedure);
 execute replace(d,$anchor$%s$anchor$,$delta$%s$delta$);
end $patch$;""" % (old_hash, ANCHOR, ANCHOR + '\n' + probe(contexts(body_before)))


def unpatched(body):
    """The installed guard without its probe, and the probe."""
    assert body.count(MARK) == 1 and body.count(ANCHOR + '\n') == 1, 'CP7_INTERNAL_GUARD_PROBE_MISSING'
    start = body.index(ANCHOR + '\n') + len(ANCHOR) + 1
    end = body.index('\n end if;', start) + len('\n end if;')
    return body[:start - 1] + body[end:], body[start:end]


def verify(cur):
    body = cur.execute("select prosrc from pg_proc where oid='erp.require_internal()'::regprocedure").fetchone()[0]
    original, fast = unpatched(body)
    # The probe reads exactly the tables of the dispatch it stands for, with the same identity filters.
    assert fast == probe(contexts(original)), 'CP7_INTERNAL_GUARD_PROBE_DIFFERS'
    return dict(stage='R4_05_INTERNAL_GUARD_ONE_CONTEXT_PROBE', tables=len(contexts(original)))
