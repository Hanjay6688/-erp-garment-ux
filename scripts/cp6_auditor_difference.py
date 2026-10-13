"""What differs between two boundary snapshots and two public_state values (scripts/cp6_auditor_runner.py).

Diagnosis only (Fable retest of 7a0b4a90, owner 13 Oct 2026): it names the differing part when a boundary or
public-schema comparison fails; it never decides a result. Kept free of database imports so it is unit-tested where
psycopg is not installed (CP7 Shell S0).
"""
import json


def state_difference(boundary_before,boundary_after,public_before,public_after):
    """What differs between two boundary snapshots and two public_state values; order-only differences are named."""
    out={}
    for part in sorted(set(boundary_before)|set(boundary_after)):
        a,b=boundary_before.get(part),boundary_after.get(part)
        if a==b:continue
        if isinstance(a,dict) and isinstance(b,dict):
            out['boundary.'+part]=sorted(k for k in set(a)|set(b) if a.get(k)!=b.get(k))[:50]
        else:
            same=isinstance(a,list) and isinstance(b,list) and sorted(map(json.dumps,a))==sorted(map(json.dumps,b))
            out['boundary.'+part]='ORDER_ONLY' if same else dict(before_count=len(a or []),after_count=len(b or []))
    for part in sorted(set(public_before)|set(public_after)):
        a,b=public_before.get(part),public_after.get(part)
        if a==b:continue
        if isinstance(a,dict) and isinstance(b,dict):
            out['public.'+part]=sorted(k for k in set(a)|set(b) if a.get(k)!=b.get(k))[:50]
        elif isinstance(a,list) and isinstance(b,list):
            sa,sb=set(map(json.dumps,a)),set(map(json.dumps,b))
            if sorted(map(json.dumps,a))==sorted(map(json.dumps,b)):
                first=next(i for i,(x,y) in enumerate(zip(a,b)) if x!=y)
                out['public.'+part]=dict(kind='ORDER_ONLY',entries=len(a),first_difference_at=first,before=a[first],after=b[first])
            else:
                out['public.'+part]=dict(kind='CONTENT',removed=sorted(sa-sb)[:20],added=sorted(sb-sa)[:20])
        else:
            out['public.'+part]=dict(kind='CONTENT')
    return out
