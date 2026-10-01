"""Exact CP7 admission deltas; all accepted credit/accounting logic is retained."""
from pathlib import Path
import gzip,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
SIGNATURES=('public.erp_save_supplier_credit_v1(jsonb,uuid)','erp.bf_supplier_credit_allocate_v1(jsonb,uuid)')
CHECK=" perform erp.require_owner_admin();perform erp.require_permission('finance.ap.pay');\n"

def accepted(signature):
 schema,name=signature.split('(')[0].split('.')
 row=next(f for f in json.loads(gzip.decompress((ROOT/'docs/cp7/evidence/p00/CP7_P00_CATALOGUE.json.gz').read_bytes()))['functions']if f['schema']==schema and f['name']==name)
 definition=row['definition'];assert hashlib.sha256(definition.encode()).hexdigest()==row['definition_sha256']
 return definition

def patched(signature):
 definition=accepted(signature)
 if signature==SIGNATURES[0]:
  replacements=[
   ('begin\n',"begin\n if current_setting('transaction_isolation')<>'read committed' then raise exception using errcode='25000',message='CP7_SUPPLIER_CREDIT_READ_COMMITTED_REQUIRED';end if;\n"),
   (" perform pg_advisory_xact_lock(hashtextextended('BF:REQUEST:'||p_client_request_id,0));\n",None),
   (' return result;\n',CHECK+' return result;\n')]
 else:
  replacements=[
   (" select * into h from erp.material_supplier_returns where id=erp.bd_uuid_v1(p_payload,'return_id',true) for update;\n",None),
   (' perform 1 from erp.material_purchase_headers where id=any(affected) order by id for update;\n',None)]
 for anchor,delta in replacements:
  assert definition.count(anchor)==1,('CP7_CREDIT_GUARD_ANCHOR_CHANGED',signature,anchor)
  definition=definition.replace(anchor,anchor+CHECK if delta is None else delta,1)
 return definition

def extension():
 path=ROOT/'scripts/cp7-src/procurement/supplier-credit-authority.sql'
 expected='''-- CP7 current-authority admission only. The accepted release files retain
-- their bytes; Native balances, credit moves, journals, stock, HPP, actors,
-- UUID replay payloads, owners and ACLs retain their original rules.
-- Recheck after request/source/target waits and after all Native writes so a
-- later accounting lock cannot commit under a permission revoked meanwhile.
do $credit_guard$ begin
'''
 for signature in SIGNATURES:
  digest=hashlib.sha256(accepted(signature).encode()).hexdigest()
  expected+=f" if encode(extensions.digest(pg_get_functiondef('{signature}'::regprocedure),'sha256'),'hex')<>'{digest}' then raise exception 'CP7_SUPPLIER_CREDIT_PREDECESSOR_CHANGED';end if;\n"
 expected+='end $credit_guard$;\n\n'+'\n\n'.join(patched(s)+';'for s in SIGNATURES)+'\n'
 assert path.read_text()==expected,'CP7_CREDIT_ADMISSION_SQL_DIFFERS_FROM_EXACT_DECLARED_DELTAS'
 return expected
