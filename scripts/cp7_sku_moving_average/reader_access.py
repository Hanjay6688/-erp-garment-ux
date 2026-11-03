"""One private read capability; no application role receives private DML."""
ROLE='cp7_fg_read'
SCHEMA='cp7_sku_conversion'
FUNCTION=SCHEMA+'.position_value_v2(uuid,uuid,text,numeric)'
ORIGINAL_SCHEMA=['postgres',[
    ['postgres','postgres','CREATE',False],
    ['postgres','postgres','USAGE',False],
]]
EXPECTED_SCHEMA=['postgres',[
    [ROLE,'postgres','USAGE',False],
    *ORIGINAL_SCHEMA[1],
]]


def schema_transition(before,after):
    return before==ORIGINAL_SCHEMA and after==EXPECTED_SCHEMA


def may_execute(role,signature):
    return role==ROLE and signature==FUNCTION


def grant(cur):
    # Fixed trusted identifiers only. The callee separately checks the live
    # actor's existing finance.hpp.view permission before observing any pool.
    cur.execute('grant usage on schema '+SCHEMA+' to '+ROLE)
    cur.execute('grant execute on function '+FUNCTION+' to '+ROLE)


def revoke_schema(cur):
    cur.execute('revoke usage on schema '+SCHEMA+' from '+ROLE)
