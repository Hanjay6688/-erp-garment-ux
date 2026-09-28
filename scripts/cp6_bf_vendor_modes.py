"""Vendor-source and PR30 follow-up; writer evidence on disposable PostgreSQL."""
import cp6_bf_vendor_probe as p
import cp6_bf_supplier_probe as supplier
import cp6_bf_modes as bf_modes
import cp6_be_revision_modes as regression
INSTALL_BF=True

def cases(cur,today):
    return [('SUPPLIER:FABRIC_SPLIT_ORIGINAL_INVERSE',lambda:supplier.allocation(cur,today,True)),
      ('SUPPLIER:ACCESSORY_SPLIT_ORIGINAL_INVERSE',lambda:supplier.allocation(cur,today)),
      ('SUPPLIER:CASH_REALLOCATION_FINANCIAL_TRUTH',lambda:supplier.cash_and_reallocation(cur,today)),
      ('SUPPLIER:EXACT_CENT_FOREIGN_PARTY_REFUSAL',lambda:supplier.exact_cent_and_party(cur,today)),
      ('PR30:D03_HISTORICAL_WORKSPACE',lambda:p.historical_workspace(cur,today)),
      ('PR30:D02_UNUSED_STALE_BINDING',lambda:p.stale_wave(cur,today)),
      ('PR30:D02_PRIOR_VALID_PIN',lambda:p.stale_wave(cur,today,True)),
      ('VENDOR:AUTHORITY_WITH_LEGACY_SKU_OVERRIDE',lambda:p.vendor_authority(cur,today)),
      ('VENDOR:EMPTY_DETAILS_INVOICE_HPP_SALE_REVERSAL',lambda:p.pending_invoice(cur,today)),
      ('VENDOR:UNKNOWN_COMPONENT_INVOICE_HPP_SALE_REVERSAL',lambda:p.pending_invoice(cur,today,True)),
      ]+[
        ('VENDOR_REG:'+k,lambda f=f:f(cur,p.b.case_day(today))) for k,_,f in p.b.PLAN if k.startswith('D12:')]+regression.cases(cur,today)

def races(tools,today):return [('SUPPLIER_RACE:FIRST_COMMITS',lambda:supplier.race(tools,today,True)),('SUPPLIER_RACE:FIRST_ABORTS',lambda:supplier.race(tools,today,False))]+bf_modes.races(tools,today)
def http_cases(http,today):return supplier.http_cases(http,today)+bf_modes.http_cases(http,today)
