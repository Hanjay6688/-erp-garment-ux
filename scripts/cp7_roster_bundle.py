"""P12 current-authority roster/rate writes through unchanged native functions."""
import cp7_attendance_read_bundle as attendance
ROOT=attendance.ROOT
def extension():return (ROOT/'scripts/cp7-src/payroll/roster-write.sql').read_text()
def bundle():return attendance.bundle()+'\n'+extension()
RULES={**attendance.RULES,'roster_access':('cp7_attendance_read',True,'s'),'apply_roster':('postgres',True,'v'),'roster_command':('cp7_roster_write',False,'v')}
