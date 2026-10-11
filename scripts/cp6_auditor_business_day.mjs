// Business-day control of the browser host: the same rule as scripts/cp6_auditor_business_day.py (see there). A case run
// on another WIB date than the one its group was planned with, or whose date changes while it runs, is not a PASS: the
// row gets the three dates and business_day_rollover, a PASS becomes INCOMPLETE, other statuses stay as they are.
export const WIB_DAY = "select (statement_timestamp() at time zone 'Asia/Jakarta')::date"

export function guard(row, planned, before, after) {
  row.business_day = { planned: String(planned), before: String(before), after: String(after) }
  if (row.business_day.planned === row.business_day.before && row.business_day.before === row.business_day.after) return false
  row.business_day_rollover = true
  if (row.status === 'PASS') {
    row.status_before_rollover = 'PASS'; row.status = 'INCOMPLETE'
    if (!('error' in row)) row.error = 'AUDITOR_BUSINESS_DAY_ROLLOVER'
  }
  return true
}
