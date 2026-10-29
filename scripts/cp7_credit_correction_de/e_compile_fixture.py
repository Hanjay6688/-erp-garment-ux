"""Structural column/signature doubles for E SQL compilation only."""
from pathlib import Path
from cp7_credit_correction_de import local_compile_fixture as base
ROOT=Path(__file__).resolve().parents[2]

def build(dump):
    source=(ROOT/'scripts/cp7-src/sales/correction.sql').read_text()+'\n'+(ROOT/'scripts/cp7-src/sales/correction-lines.sql').read_text()
    table_source=source.replace('cp7_note.','cp7_sales_return_correction.')
    tables=base.tables(table_source)
    statements=''.join(value.replace('cp7_sales_return_correction.','cp7_note.')for value in tables.values())
    return base.build(dump)+'create role cp7_capture;create role cp7_sales_read;create role cp7_sales_write;create role cp7_credit_write;create schema cp7_note;'+statements+'''
create function cp7_credit.current_leaf_assignment(uuid)returns table(root_sale_id uuid,current_leaf_id uuid,customer_id uuid,requested_status text)language sql stable as $$select $1,$1,null::uuid,'POSTED'::text$$;
create function cp7_credit.consumer_incoming_funding_v1(uuid)returns jsonb language sql stable as $$select '[]'::jsonb$$;
alter table erp.sales_headers add column if not exists row_version bigint;
'''
if __name__=='__main__':
 import sys
 print(build(sys.argv[1]))
