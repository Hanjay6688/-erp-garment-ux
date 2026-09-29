"""P12 authoritative attendance source reads; no source mutation/UI claim."""
import cp7_settlement_bundle as settlement
ROOT=settlement.ROOT
def extension():return (ROOT/'scripts/cp7-src/payroll/attendance-read.sql').read_text()
def bundle():return settlement.bundle()+'\n'+extension()
RULES={name:('cp7_attendance_read',False,'s') for name in ('access_now','source_token','worker_document','period_document','workspace')}
