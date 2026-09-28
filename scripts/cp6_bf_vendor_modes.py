"""Vendor-source and PR30 follow-up; writer evidence on disposable PostgreSQL."""
import cp6_bf_vendor_probe as p
import cp6_bf_modes as bf_modes
import cp6_be_revision_modes as regression
INSTALL_BF=True

def cases(cur,today):
    return [('PR30:D03_HISTORICAL_WORKSPACE',lambda:p.historical_workspace(cur,today)),
      ('PR30:D02_UNUSED_STALE_BINDING',lambda:p.stale_wave(cur,today)),
      ('PR30:D02_PRIOR_VALID_PIN',lambda:p.stale_wave(cur,today,True)),
      ('VENDOR:AUTHORITY_WITH_LEGACY_SKU_OVERRIDE',lambda:p.vendor_authority(cur,today)),
      ('VENDOR:EMPTY_DETAILS_INVOICE_HPP_SALE_REVERSAL',lambda:p.pending_invoice(cur,today)),
      ('VENDOR:UNKNOWN_COMPONENT_INVOICE_HPP_SALE_REVERSAL',lambda:p.pending_invoice(cur,today,True)),
      ('BF:UNUSED_ROLLBACK_EXACT',lambda:p.bf.recovery_unused(cur,today)),
      ('BF:SHARED_MASTER_PHYSICAL_ROOTS_REPLAY',lambda:p.bf.foundation(cur,today))]+[
        ('VENDOR_REG:'+k,lambda f=f:f(cur,p.b.case_day(today))) for k,_,f in p.b.PLAN if k.startswith(('T02:','T03:','T04:','T05:','T06:','T07:','T12:','D12:'))]+regression.cases(cur,today)

def races(tools,today):return bf_modes.races(tools,today)
def http_cases(http,today):return bf_modes.http_cases(http,today)
