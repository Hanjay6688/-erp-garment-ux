"""R5-01 (Sol SOL-R4-001, S1): the payroll wrong-contractor checker knows the FG_REPAIR source.

erp.run_v263a_payroll_integrity_checks() (v2.6.15, unchanged since) finds the contractor of a Nota work line through its
source: PRODUCTION through the work completion event, REWORK through the rework order. AX (owner 24 Sep 2026, repair
wage of a found BS repaired to GOOD, `scripts/cp6_ax_build.py`) added the third source FG_REPAIR to the eligible-lines
view, the source CHECK, the work-item validator and the merge RPC, but not to this checker, so a valid FG_REPAIR line
compared the Nota contractor with NULL and was counted as `payroll_work_wrong_contractor` (CRITICAL). Sol proved it with
two valid repair wages (2 and 1 pcs at 2,000) on one posted Nota: 2 false alarms, the 6,000 itself right.

Forward delta on that one Native function: the check resolves an FG_REPAIR line through its repair wage, like the
validator does (`fg_unsourced_repair_wages_v1.contractor_id`). Nothing is filtered: a line whose wage belongs to another
contractor, or whose wage is missing, still compares with a different contractor or NULL and still counts; PRODUCTION
and REWORK lines resolve as before. Install patches the captured definition (anchor checked, like HPP01); uninstall
restores it through the same `originals` every F03 installer already replays.
"""
SIGNATURE = 'erp.run_v263a_payroll_integrity_checks()'
CHECK = 'payroll_work_wrong_contractor'
ANCHOR = """  left join erp.rework_orders ro on ro.id = rcl.rework_order_id
  where ps.status <> 'REVERSED'
    and ps.contractor_id is distinct from coalesce(wce.contractor_id, ro.contractor_id);"""
CHANGE = """  left join erp.rework_orders ro on ro.id = rcl.rework_order_id
  -- R5-01 (Sol SOL-R4-001, scripts/cp7_payroll_checks_bundle.py): an FG_REPAIR line belongs to the contractor of its
  -- repair wage; a line whose wage is missing or another contractor's still counts.
  left join erp.fg_unsourced_repair_wages_v1 fgw
    on pwi.source_type = 'FG_REPAIR'
   and fgw.id = pwi.source_id
  where ps.status <> 'REVERSED'
    and ps.contractor_id is distinct from coalesce(wce.contractor_id, ro.contractor_id, fgw.contractor_id);"""


def patched(definition):
    assert definition.count(ANCHOR) == 1, ('R5_01_NATIVE_PAYROLL_CHECK_SOURCE_CHANGED', ANCHOR)
    return definition.replace(ANCHOR, CHANGE, 1)


def unpatched(definition):
    """The installed checker as it was before this delta (the CP17 case runs both side by side)."""
    assert definition.count(CHANGE) == 1, 'R5_01_PAYROLL_CHECK_NOT_PATCHED'
    return definition.replace(CHANGE, ANCHOR, 1)


def capture(cur, originals):
    assert SIGNATURE not in originals, 'R5_01_NATIVE_ALREADY_CAPTURED'
    originals[SIGNATURE] = cur.execute('select pg_get_functiondef(%s::regprocedure)', (SIGNATURE,)).fetchone()[0]
    patched(originals[SIGNATURE])


def expected_definitions(originals):
    return {SIGNATURE: patched(originals[SIGNATURE])}


def extension():
    return """-- R5-01: the payroll wrong-contractor checker knows the FG_REPAIR source (cp7_payroll_checks_bundle.py).
do $r5_01$
declare definition text;
begin
 definition:=pg_get_functiondef('""" + SIGNATURE + """'::regprocedure);
 if (length(definition)-length(replace(definition,$anchor$""" + ANCHOR + """$anchor$,'')))<>length($anchor$""" + ANCHOR + """$anchor$) then
  raise exception 'CP7_R5_01_NATIVE_PAYROLL_CHECK_SOURCE_CHANGED';end if;
 execute replace(definition,$anchor$""" + ANCHOR + """$anchor$,$changed$""" + CHANGE + """$changed$);
end $r5_01$;
"""


def verify(cur):
    definition = cur.execute('select pg_get_functiondef(%s::regprocedure)', (SIGNATURE,)).fetchone()[0]
    assert definition.count(CHANGE) == 1 and definition.count('fgw.contractor_id') == 1, 'R5_01_PAYROLL_CHECK_NOT_PATCHED'
    return dict(stage='R5_01_PAYROLL_CHECK_KNOWS_FG_REPAIR')
