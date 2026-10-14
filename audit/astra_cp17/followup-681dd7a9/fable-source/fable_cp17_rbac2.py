"""Fable cp17 RBAC run 2: only FABLE_RBAC:PUBLIC_FACADES_SECURITY (run 1 38571378585 hit a psycopg placeholder error in the
LIKE pattern before reaching the oracle; the other two cases of run 1 are final). Oracle unchanged."""
import os
os.environ['FABLE_RBAC_ONLY']='facades'
import fable_cp17_rbac as base
def cases(cur,today):return base.cases(cur,today)
def races(tools,today):return []
def http_cases(http,today):return []
