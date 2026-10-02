"""Exact, read-only Native owner report delta; no economic writer relaxation."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SIGNATURE='erp.get_owner_financial_snapshot_v2(date,date,date)'

def changes():
 for kind in ('SALE','SALES_RETURN'):
  anchor=("      and original.source_type='"+kind+"'\n"
   "    where reversal.source_type='JOURNAL_REVERSAL' and reversal.status='POSTED'\n"
   "      and reversal.transaction_date between p_from and p_to\n  )")
  addition=("\n    union all\n    select source_id,event_sign\n"
   "    from cp7_note.report_lifecycle(p_from,p_to,'"+kind+"')")
  yield anchor,anchor[:-4]+addition+'\n  )'

def patched_report(definition):
 assert 'perform erp.require_owner_admin();'in definition
 for anchor,replacement in changes():
  assert definition.count(anchor)==1,('NOTE_NATIVE_REPORT_SOURCE_CHANGED',anchor)
  definition=definition.replace(anchor,replacement,1)
 return definition

def capture(cur,originals):
 assert SIGNATURE not in originals,'NOTE_NATIVE_REPORT_ALREADY_CAPTURED'
 originals[SIGNATURE]=cur.execute('select pg_get_functiondef(%s::regprocedure)',(SIGNATURE,)).fetchone()[0]
 patched_report(originals[SIGNATURE])

def expected_definitions(internal_before,originals,internal_patch,owner_patch):
 return {'erp.require_internal()':internal_patch(internal_before),
  'erp.require_owner_admin()':owner_patch(originals['erp.require_owner_admin()']),
  SIGNATURE:patched_report(originals[SIGNATURE])}

def extension():
 sql=(ROOT/'scripts/cp7-src/sales/report.sql').read_text()
 replacements='\n'.join(" if length(definition)-length(replace(definition,$anchor$"+a+
  "$anchor$,''))<>length($anchor$"+a+"$anchor$)then raise exception 'CP7_NOTE_NATIVE_REPORT_SOURCE_CHANGED';end if;\n"
  " definition:=replace(definition,$anchor$"+a+"$anchor$,$changed$"+z+"$changed$);"
  for a,z in changes())
 return sql+"\ndo $report$\ndeclare definition text;original text;signature text:='"+SIGNATURE+"';\nbegin\n"+\
  " original:=pg_get_functiondef(signature::regprocedure);definition:=original;\n"+replacements+\
  "\n execute definition;\n insert into cp7_note.report_sources values(signature,original,\n"+\
  " encode(pg_catalog.sha256(convert_to(original,'UTF8')),'hex'),\n"+\
  " encode(pg_catalog.sha256(convert_to(definition,'UTF8')),'hex'));\nend $report$;\n"
