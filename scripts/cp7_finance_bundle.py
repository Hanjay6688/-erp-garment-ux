"""P13 read-only financial source projection after the P11/P09 development stack."""
from pathlib import Path
import cp7_sales_bundle
ROOT=Path(__file__).resolve().parents[1]
GRANTS=('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)','erp.get_owner_financial_snapshot_v2(date,date,date)','erp.accounting_close_preflight_v1(date)','erp.account_id(text)')
def extension():return '\n'.join((ROOT/('scripts/cp7-src/finance/'+name)).read_text() for name in ('read.sql','analysis.sql'))
def bundle():return cp7_sales_bundle.bundle()+'\n'+extension()
