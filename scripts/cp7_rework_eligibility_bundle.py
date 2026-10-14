"""RWK01 (Astra ASTRA-CP17-RWK-01, Fable FABLE-006): an accrued rework wage stays payable whatever the goods outcome.

The Native REWORK branch of erp.v_payroll_eligible_work_lines and of erp.validate_payroll_work_item_source()
requires bs_cases.status='RESOLVED'. A rework whose whole output is then scrapped closes its BS case as SCRAPPED
(or WRITTEN_OFF), while the completion has already credited CONTRACTOR_PAYABLE (REWORK_COMPLETION), so that
payable could never be put on a Nota or paid. Forward delta on both Native objects, nothing else: a BS case with a
final outcome RESOLVED, SCRAPPED or WRITTEN_OFF is payable; OPEN, IN_REWORK, PARTIAL, ON_HOLD and CANCELLED stay
unpayable as before. The rest of the rule (completed contractor rework, cost posted, remaining quantity, component/
PO/contractor match, no double allocation, the advisory lock) is unchanged. The originals are captured by the
installing probe (cp7_note_report_bundle.capture) and restored on uninstall.
"""
SIGNATURE='erp.validate_payroll_work_item_source()'
VIEW='erp.v_payroll_eligible_work_lines'
FINAL=('RESOLVED','SCRAPPED','WRITTEN_OFF')
FUNCTION_ANCHOR="      and bc.status='RESOLVED';"
FUNCTION_CHANGE="      and bc.status in('RESOLVED','SCRAPPED','WRITTEN_OFF');"
# pg_get_viewdef renders the cast with or without parentheses depending on the server version.
VIEW_STATUS=r"\(?bc\.status\)?::text = 'RESOLVED'::text"
VIEW_STATUS_CHANGE="(bc.status)::text = ANY (ARRAY['RESOLVED'::text, 'SCRAPPED'::text, 'WRITTEN_OFF'::text])"
VIEW_REASON="'BS_CASE_RESOLVED'::text AS eligibility_reason"
VIEW_REASON_CHANGE="('BS_CASE_'::text || (bc.status)::text) AS eligibility_reason"


def patched(definition):
    assert definition.count(FUNCTION_ANCHOR)==1,('RWK01_NATIVE_VALIDATOR_SOURCE_CHANGED',FUNCTION_ANCHOR)
    return definition.replace(FUNCTION_ANCHOR,FUNCTION_CHANGE,1)


def capture(cur,originals):
    assert SIGNATURE not in originals and VIEW not in originals,'RWK01_NATIVE_ALREADY_CAPTURED'
    originals[SIGNATURE]=cur.execute('select pg_get_functiondef(%s::regprocedure)',(SIGNATURE,)).fetchone()[0]
    patched(originals[SIGNATURE])
    originals[VIEW]='create or replace view '+VIEW+' with (security_invoker=true) as '+cur.execute('select pg_get_viewdef(%s::regclass)',(VIEW,)).fetchone()[0]


def expected_definitions(originals):
    return {SIGNATURE:patched(originals[SIGNATURE])}


def extension():
    return """-- RWK01: accrued rework wages stay payable whatever the goods outcome (cp7_rework_eligibility_bundle.py).
do $rwk01$
declare definition text;view_definition text;
begin
 definition:=pg_get_functiondef('"""+SIGNATURE+"""'::regprocedure);
 if (length(definition)-length(replace(definition,$anchor$"""+FUNCTION_ANCHOR+"""$anchor$,'')))<>length($anchor$"""+FUNCTION_ANCHOR+"""$anchor$) then
  raise exception 'CP7_RWK01_NATIVE_VALIDATOR_SOURCE_CHANGED';end if;
 execute replace(definition,$anchor$"""+FUNCTION_ANCHOR+"""$anchor$,$changed$"""+FUNCTION_CHANGE+"""$changed$);
 view_definition:=pg_get_viewdef('"""+VIEW+"""'::regclass);
 if (select count(*) from regexp_matches(view_definition,$re$"""+VIEW_STATUS+"""$re$,'g'))<>1
  or (length(view_definition)-length(replace(view_definition,$anchor$"""+VIEW_REASON+"""$anchor$,'')))<>length($anchor$"""+VIEW_REASON+"""$anchor$) then
  raise exception 'CP7_RWK01_NATIVE_VIEW_SOURCE_CHANGED';end if;
 view_definition:=replace(regexp_replace(view_definition,$re$"""+VIEW_STATUS+"""$re$,$changed$"""+VIEW_STATUS_CHANGE+"""$changed$),
  $anchor$"""+VIEW_REASON+"""$anchor$,$changed$"""+VIEW_REASON_CHANGE+"""$changed$);
 execute 'create or replace view """+VIEW+""" with (security_invoker=true) as '||view_definition;
end $rwk01$;
"""


def verify(cur):
    definition=cur.execute('select pg_get_functiondef(%s::regprocedure)',(SIGNATURE,)).fetchone()[0]
    assert FUNCTION_CHANGE in definition and FUNCTION_ANCHOR not in definition,'RWK01_VALIDATOR_NOT_PATCHED'
    view=cur.execute('select pg_get_viewdef(%s::regclass)',(VIEW,)).fetchone()[0]
    assert all("'"+s+"'::text" in view for s in FINAL) and "'BS_CASE_RESOLVED'::text AS eligibility_reason" not in view,'RWK01_VIEW_NOT_PATCHED'
    assert cur.execute("select coalesce('security_invoker=true'=any(reloptions),false) from pg_class where oid=%s::regclass",(VIEW,)).fetchone()[0],'RWK01_VIEW_LOST_SECURITY_INVOKER'
    return dict(rework_wage_payable_for_final_outcomes=list(FINAL),unfinished_cases_unchanged=True)
