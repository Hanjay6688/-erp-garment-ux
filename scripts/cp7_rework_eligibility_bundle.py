"""RWK01 (Astra ASTRA-CP17-RWK-01, Fable FABLE-006; owner D14-11): a finished rework part is payable while the BS case
is still open.

The Native REWORK branch of erp.v_payroll_eligible_work_lines and of erp.validate_payroll_work_item_source()
requires bs_cases.status='RESOLVED'. The payable unit is one rework order line (erp.rework_component_lines): its
rework order must be COMPLETED (the contractor returned it and the good/BS split was counted) and cost_posted (the
completion was approved and credited CONTRACTOR_PAYABLE, REWORK_COMPLETION). Owner D14-11 (15 Oct 2026): "upah rework
boleh dibayar untuk bagian pekerjaan yang sudah selesai, diperiksa, dan disetujui, walaupun keseluruhan kasus BS masih
terbuka atau sebagian. Bagian yang belum selesai tetap ditahan." Forward delta on both Native objects, nothing else:
the case may be OPEN, IN_REWORK, PARTIAL, RESOLVED, SCRAPPED or WRITTEN_OFF; only a CANCELLED case stays unpayable.
Rework orders not COMPLETED or not cost_posted stay held exactly as before. The rest of the rule (completed contractor
rework, cost posted, remaining quantity per line, component/PO/contractor match, no double allocation across
non-reversed payrolls, the advisory lock) is unchanged, so a line paid while the case is open has nothing left when
the case is closed. The originals are captured by the installing probe (cp7_note_report_bundle.capture) and restored
on uninstall.
"""
SIGNATURE='erp.validate_payroll_work_item_source()'
VIEW='erp.v_payroll_eligible_work_lines'
PAYABLE=('OPEN','IN_REWORK','PARTIAL','RESOLVED','SCRAPPED','WRITTEN_OFF')
FUNCTION_ANCHOR="      and bc.status='RESOLVED';"
FUNCTION_CHANGE="      and bc.status in('OPEN','IN_REWORK','PARTIAL','RESOLVED','SCRAPPED','WRITTEN_OFF');"
# pg_get_viewdef renders the cast with or without parentheses depending on the server version.
VIEW_STATUS=r"\(?bc\.status\)?::text = 'RESOLVED'::text"
VIEW_STATUS_CHANGE="(bc.status)::text = ANY (ARRAY['OPEN'::text, 'IN_REWORK'::text, 'PARTIAL'::text, 'RESOLVED'::text, 'SCRAPPED'::text, 'WRITTEN_OFF'::text])"
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
    return """-- RWK01 + D14-11: a finished, posted rework part is payable unless its BS case is CANCELLED (cp7_rework_eligibility_bundle.py).
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
    assert all("'"+s+"'::text" in view for s in PAYABLE) and "'CANCELLED'::text" not in view and "'BS_CASE_RESOLVED'::text AS eligibility_reason" not in view,'RWK01_VIEW_NOT_PATCHED'
    assert cur.execute("select coalesce('security_invoker=true'=any(reloptions),false) from pg_class where oid=%s::regclass",(VIEW,)).fetchone()[0],'RWK01_VIEW_LOST_SECURITY_INVOKER'
    return dict(rework_wage_payable_bs_case_status=list(PAYABLE),held_bs_case_status=['CANCELLED'],rework_order_must_be_completed_and_cost_posted=True)
