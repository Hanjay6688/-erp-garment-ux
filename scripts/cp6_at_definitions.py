"""AT narrows new WIP output to identities valid on its physical business day.

Opening stock intentionally permits expired historical identities. Neither its
resolver nor the AS production import validator is changed by this repair.
"""
import cp6_as_definitions as predecessor

OUTPUT='erp.complete_initial_import_wip_v1(jsonb)'
OLD={OUTPUT:predecessor.FUNCTIONS[OUTPUT]}
FUNCTIONS=dict(OLD)
old="      and p.effective_from<(v_date+1)::timestamp at time zone 'Asia/Jakarta'\n"
new=old+"      and (p.effective_to is null or p.effective_to>v_date::timestamp at time zone 'Asia/Jakarta')\n"
assert FUNCTIONS[OUTPUT].count(old)==1
FUNCTIONS[OUTPUT]=FUNCTIONS[OUTPUT].replace(old,new)
