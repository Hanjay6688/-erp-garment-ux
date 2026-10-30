"""Writer-only finite source census; never a live lock/permission qualification.

Native dump is a pinned read-only evidence input supplied by root. This tool
is not required or run by CI/source admission; its exact receipt is retained.
"""
from pathlib import Path
from hashlib import sha256
import argparse
import json
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def functions(text):
    for match in re.finditer(r'(?im)^create\s+(?:or\s+replace\s+)?function\s+([\w.]+)\s*\(',text):
        marker=re.search(r'(?i)\bas\s+(\$[a-z0-9_]*\$)',text[match.start():])
        if marker is None:
            continue
        begin=match.start()+marker.end()
        end=text.find(marker.group(1),begin)
        if end<0:
            raise ValueError('CENSUS_UNCLOSED_SOURCE_FUNCTION:'+match[1])
        yield match[1],text[match.start():end+len(marker.group(1))+1],text[:match.start()].count('\n')+1


def run(native_dump,output):
    cfg=json.loads((ROOT/'scripts/cp7_global_nonpo_native_graph_adapter/AUTHORITY.json').read_bytes())
    data=Path(native_dump).read_bytes()
    if (len(data),sha256(data).hexdigest())!=(cfg['retained_Native_dump']['bytes'],cfg['retained_Native_dump']['sha256']):
        raise ValueError('EXACT_ROOT_RETAINED_NATIVE_DUMP_REQUIRED')
    inputs=[(str(native_dump),data)]
    for path in sorted((ROOT/'scripts/cp7_customer_credit').rglob('*.sql')):
        inputs.append((str(path.relative_to(ROOT)),path.read_bytes()))
    for path in sorted((ROOT/'scripts/cp7_credit_correction_de').rglob('*.sql')):
        inputs.append((str(path.relative_to(ROOT)),path.read_bytes()))
    be='supabase/release/cp6-t3/20260926050000_erp_v2_6_20be_cp6_conversion_redye_pocket.sql'
    inputs.append((be,(ROOT/be).read_bytes()))
    bc='supabase/release/cp6-t3/20260925030000_erp_v2_6_20bc_cp6_accessory_service_returns.sql'
    inputs.append((bc,(ROOT/bc).read_bytes()))
    reader_sources='\n'.join(p.read_text()for p in (ROOT/'scripts/cp7_global_nonpo_native_graph_adapter').glob('*.sql'))
    targets=set(re.findall(r'\b(?:erp|cp7_credit|cp7_note)\.([a-z][a-z0-9_]*)\b',reader_sources))
    # Explicit relation inventory includes direct Native pure-reader inputs.
    relations=set('fg_lots hpp_versions hpp_version_components product_conversions product_conversion_allocations be_conversion_sources_v1 be_conversion_cost_sources_v1 be_conversion_cost_events_v1 be_nonpo_transfer_events_v1 be_conversion_returns_v1 bc_outstanding_returns_v1 bc_return_lots_v1 bc_documents_v1 bc_document_links_v1 bc_adjustment_purposes_v1 bc_lot_events_v1 material_adjustments fg_stock_movements fg_inventory_balances sales_headers sales_items sale_stock_allocations sales_returns sales_return_items journal_entries journal_lines non_po_hpp_gl_sync_events_v2620f opening_lot_hpp_gl_state opening_hpp_corrections po_hpp_gl_state accounting_account_mappings chart_accounts accounting_period_control be_execution_context_v1 revisions return_families cohorts consumption_events'.split())
    writers=[];input_pins={}
    for path,raw in inputs:
        input_pins[path]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
        text=raw.decode()
        for name,definition,line in functions(text):
            writes=[]
            for m in re.finditer(r'(?i)\b(insert\s+into|update|delete\s+from)\s+(?:(erp|cp7_credit|cp7_note)\.)?([a-z][a-z0-9_]*)',definition):
                if m[3].lower() in relations:
                    writes.append(dict(operation=' '.join(m[1].upper().split()),schema=m[2],relation=m[3].lower(),source_offset=m.start()))
            if writes:
                writers.append(dict(function=name,path=path,line=line,source_definition_sha256=sha256(definition.encode()).hexdigest(),writes=writes,
                    literal_FG_HPP_SALES_lock_present='FG_HPP_SALES_V2620C'in definition,
                    literal_FGBOOK_lock_present='FGBOOK|GLOBAL'in definition,
                    pocket_try_source_present='pocket_period_lock_v1'in definition,
                    dynamic_EXECUTE_tokens_present=bool(re.search(r'(?i)\bexecute\b',definition))))
    answer=dict(classification='EXACT_FINITE_SOURCE_TEXT_WRITER_CANDIDATES_NOT_LIVE_INSTALLED_CENSUS',source_base=cfg['source_base'],
        inputs=input_pins,input_files=len(inputs),relation_names=sorted(relations),writer_candidates=writers,
        count=len(writers),has_non_FG_literal_writers=any(not w['literal_FG_HPP_SALES_lock_present']for w in writers),
        critical_examples=[w for w in writers if w['function']in('erp.post_journal','erp.save_product_conversion_action_v1','erp.post_product_conversion','erp.reverse_product_conversion')],
        not_closed=['Some SQL files are source assembly inputs/proposals, not independent installed functions.',
          'A missing literal advisory lock does not prove caller lacks it; complete exact caller/trigger/RI/context/privilege routes remain required.',
          'Dynamic SQL and later current E/SKU/composition source routing are not inferred from token search.',
          'Current source authority/OWNER permissions and actual function/trigger/FK census must be rebound to final composite parent.',
          'No two-session exclusion, phantom prevention or permission-after-wait was executed.'],
        writer_or_phantom_lock_closed=False,runtime_entry=None,actual_Native=0,production_go=False,independent_acceptance=False)
    Path(output).write_text(json.dumps(answer,indent=2)+'\n')
    return dict(status='SOURCE_CENSUS_RETAINED_NOT_LOCK_QUALIFIED',source_files=len(inputs),writer_candidates=len(writers))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-dump',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();print(json.dumps(run(args.native_dump,args.output)))
