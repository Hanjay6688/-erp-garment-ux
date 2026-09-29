"""P12 finance payroll review candidate; no settlement writer or UI implied."""
import cp7_nota_bundle as nota
ROOT=nota.ROOT
def extension():return (ROOT/'scripts/cp7-src/payroll/settlement-read.sql').read_text()
def bundle():return nota.bundle()+'\n'+extension()
RULES={name:('cp7_payroll_read',False,'s') for name in ('settlement_token','settlement_document','settlement_rows','settlement_workspace')}
