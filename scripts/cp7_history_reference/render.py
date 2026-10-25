"""Lossless digest of all Native stock rows; never a truncated raw prefix."""
from pathlib import Path
from hashlib import sha256
import json
import re

ROOT = Path(__file__).resolve().parent
NATIVE = ROOT.parent/'cp7-src'/'planning'
SCHEMA = 'cp7_history_reference'


def dependencies():
    raw = (NATIVE/'bootstrap.sql').read_text()
    block = re.search(r'create function cp7_planning.utc\(.*?\$\$;',raw,re.S)[0]
    body = re.search(r'as \$\$(.*?)\$\$;',block,re.S)[1]
    return {'cp7_planning.utc(timestamp with time zone)':dict(body_sha256=sha256(body.encode()).hexdigest(),owner='cp7_capture')}


def render():
    m = json.loads((ROOT/'MANIFEST.json').read_text())
    for name,digest in m['native_file_sha256'].items():
        if sha256((NATIVE/name).read_bytes()).hexdigest() != digest:
            raise ValueError('HISTORY_REFERENCE_NATIVE_SOURCE_CHANGED: '+name)
    if m['dependencies'] != dependencies():
        raise ValueError('HISTORY_REFERENCE_DEPENDENCY_CHANGED')
    raw = (NATIVE/'history-source.sql').read_text()
    projection = re.search(r'stock as materialized\(\n(.*?)\n\),\nsales as materialized',raw,re.S)[1]
    end = ' order by m.id limit 50001'
    if projection.count(end) != 1:
        raise ValueError('HISTORY_REFERENCE_NATIVE_STOCK_QUERY_CHANGED')
    projection = projection.replace(end,'')
    # The same typed projection and BOTH visibility clocks as Native capture.
    # Only the raw JSON prefix limit is removed, because no raw array is built.
    return r"""create schema cp7_history_reference authorization cp7_capture;
revoke all on schema cp7_history_reference from public,anon,authenticated,service_role;
create function cp7_history_reference.stock_digest(p_products jsonb,p_at timestamptz)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare answer jsonb;
begin
 if p_at is null or not pg_catalog.isfinite(p_at) or jsonb_typeof(p_products)is distinct from'array'
  or jsonb_array_length(p_products)>5000 then raise exception 'CP7_HISTORY_REFERENCE_SCOPE';end if;
 if exists(select 1 from jsonb_array_elements(p_products)p where p->>'root_id'is null)
  or jsonb_array_length(p_products)<>(select count(distinct(p->>'root_id')::uuid)from jsonb_array_elements(p_products)p)then
  raise exception 'CP7_HISTORY_REFERENCE_ROOTS';end if;
 with clock as materialized(select p_at at),
 products as materialized(select(p->>'root_id')::uuid root_id from jsonb_array_elements(p_products)p),
 -- One consumer: retain the exact Native projection without a temporary copy.
 stock as not materialized(
"""+projection+r"""
 ),
 framed as(select count(*)n,coalesce(string_agg(encode(extensions.digest(convert_to(to_jsonb(m)::text,'UTF8'),'sha256'),'hex'),
  E'\n'order by m.id),'')frames from stock m)
 select jsonb_build_object('contract_version','cp7.native-stock-row-digest.v1',
  'scope','ALL_NATIVE_STOCK_FIELDS_AND_BOTH_VISIBILITY_CLOCKS','captured_at',cp7_planning.utc(p_at),
  'row_count',n::text,'rows_sha256',encode(extensions.digest(convert_to(
   E'cp7.native-stock-row-digest.v1\n'||n::text||E'\n'||frames,'UTF8'),'sha256'),'hex'),
  'raw_rows_truncated',false,'raw_rows_materialized_as_JSON_array',false,
  'raw_native_capture_status_overridden',false,'apply_enabled',false,'production_go',false)
 into answer from framed;
 return answer;
end $$;
alter function cp7_history_reference.stock_digest(jsonb,timestamptz)owner to cp7_capture;
revoke all on function cp7_history_reference.stock_digest(jsonb,timestamptz)from public,anon,authenticated,service_role;
"""
