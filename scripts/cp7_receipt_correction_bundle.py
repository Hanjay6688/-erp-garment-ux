"""Owning receipt correction ("Benerin penerimaan"), installed after the complete F03 extension.

Only new CP7 objects are created: schema cp7_receipt_fix, its private
metadata, the owning command, the effective material card reader, the
material-name typo command and five public wrappers. Declared composition grants are listed in GRANTS/TABLE_GRANTS;
no Native definition, owner or ACL is changed.
"""
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[1]
FILES=('scripts/cp7-src/procurement/correction.sql','scripts/cp7-src/procurement/material-name.sql')
# Function EXECUTE grants this extension adds to predecessor CP7 functions.
GRANTS={'cp7_procurement.decimal(jsonb,boolean)':{('postgres','EXECUTE',False)}}
# Table privileges added to predecessor CP7 tables (postgres-owned command writes its own transaction's admission row).
TABLE_GRANTS={'cp7_procurement.execution_context':('SELECT','INSERT','DELETE')}
PUBLIC=('public.erp_cp7_get_receipt_correction_v1(uuid)','public.erp_cp7_correct_receipt_v1(jsonb,uuid,text)','public.erp_cp7_get_material_ledger_v2(uuid,uuid,uuid,integer,integer)',
 'public.erp_cp7_get_material_name_v1(uuid)','public.erp_cp7_rename_material_v1(jsonb,uuid,text)')
def sql():return '\n'.join((ROOT/f).read_text() for f in FILES)
def sha256():return hashlib.sha256(sql().encode()).hexdigest()
