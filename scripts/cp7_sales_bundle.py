"""P11 bounded sales reader on the explicit P09 development stack."""
from pathlib import Path
import cp7_procurement_bundle
ROOT=Path(__file__).resolve().parents[1]
GRANTS=('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)','erp.bf_commercial_sku_at_v1(uuid,timestamptz)')
def extension():return '\n'.join((ROOT/'scripts/cp7-src/sales'/p).read_text() for p in ('read.sql','drafts.sql','commands.sql','form.sql'))
def bundle():return cp7_procurement_bundle.bundle()+'\n'+extension()
