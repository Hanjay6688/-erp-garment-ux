"""Unqualified opt-in PG17 binary reference; never replaces the v1 helper."""
from hashlib import sha256
import json

SCHEMA='cp7_history_reference_binary_v2'
PARENT_SHA256='fe4c1b7c930fe73b7a6cc79b21edaff592490d52818f925c6a2b3930033fe89f'
CONTRACT='cp7.native-stock-row-digest.v2'
ENCODING='POSTGRES17_RECORD_SEND_TEXT_AS_UTF8_BYTEA_V1'
# Native projection/order is unchanged. Only four textual fields receive an
# explicit UTF8 bytea encoding, avoiding client-encoding and custom-enum OIDs.
LAYOUT=(('id','uuid'),('root_id','uuid'),('size_id','uuid'),('product_id','uuid'),
 ('lot_id','uuid'),('location_id','uuid'),('quality_grade','UTF8_bytea'),
 ('qty_signed','UTF8_bytea'),('physical_at','timestamptz'),('system_created_at','timestamptz'),
 ('movement_type','UTF8_bytea'),('source_type','UTF8_bytea'),('source_id','uuid'),
 ('reversal_of_id','uuid'),('book_order','int8'))
LAYOUT_SHA256=sha256(json.dumps(LAYOUT,separators=(',',':')).encode()).hexdigest()


def once(text,old,new):
 assert text.count(old)==1,('STOCK_REFERENCE_V2_DERIVATION_CHANGED',old)
 return text.replace(old,new)


def render(parent_sql):
 assert sha256(parent_sql.encode()).hexdigest()==PARENT_SHA256,'STOCK_REFERENCE_V2_PARENT_CHANGED'
 assert len(LAYOUT)==15 and len({name for name,_ in LAYOUT})==15
 sql=parent_sql.replace('cp7_history_reference',SCHEMA)
 sql=sql.replace('CP7_HISTORY_REFERENCE_SCOPE','CP7_HISTORY_REFERENCE_V2_SCOPE').replace('CP7_HISTORY_REFERENCE_ROOTS','CP7_HISTORY_REFERENCE_V2_ROOTS')
 sql=once(sql,'begin\n',"""begin
 if current_setting('server_version_num')::integer/10000<>17
  or current_setting('server_encoding')is distinct from'UTF8'then
  raise exception 'CP7_HISTORY_REFERENCE_V2_SERVER_CONTRACT';end if;
 if array['uuid'::regtype::oid,'bytea'::regtype::oid,'timestamptz'::regtype::oid,'int8'::regtype::oid]
  is distinct from array[2950,17,1184,20]::oid[]then
  raise exception 'CP7_HISTORY_REFERENCE_V2_BUILTIN_TYPES';end if;
""")
 fields=["pg_catalog.convert_to(m."+name+"::text,'UTF8')"if kind=='UTF8_bytea'else'm.'+name+'::pg_catalog.'+kind for name,kind in LAYOUT]
 wire='pg_catalog.record_send(row('+','.join(fields)+'))'
 sql=once(sql,"convert_to(to_jsonb(m)::text,'UTF8')",wire)
 assert sql.count('cp7.native-stock-row-digest.v1')==2
 sql=sql.replace('cp7.native-stock-row-digest.v1',CONTRACT)
 sql=once(sql,"'scope','ALL_NATIVE_STOCK_FIELDS_AND_BOTH_VISIBILITY_CLOCKS',", "'encoding','"+ENCODING+"','layout_sha256','"+LAYOUT_SHA256+"',\n  'scope','ALL_NATIVE_STOCK_FIELDS_AND_BOTH_VISIBILITY_CLOCKS',")
 sql=once(sql,"E'"+CONTRACT+"\\n'||n::text", "E'"+CONTRACT+"\\n"+ENCODING+'\\n'+LAYOUT_SHA256+"\\n'||n::text")
 assert 'to_jsonb(m)'not in sql and 'pg_catalog.record_send(row('in sql
 return sql
