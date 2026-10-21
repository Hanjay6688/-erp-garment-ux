from pathlib import Path
import ast, hashlib,json,re
from sqlsplit import split_sql,clean_start
ROOT=Path('/workspace/scratch/9442228ed2dc/ow04-reconciliation-writer')
OUT=Path(__file__).resolve().parent
native=(OUT/'clone_native_schema_0.sql').read_text()
# This is a type scaffold, not a restoration/installation. Only actual column
# types and actual unique/primary keys are used; Native business defaults,
# checks, data, triggers and policies are intentionally not reproduced.
def table_scaffold(stmt):
 s=clean_start(stmt)
 head=s[:s.index('(')+1]; tail=s[s.rfind(')'):]
 fields=[];start=0;depth=0;quoted=None;text=s[s.index('(')+1:s.rfind(')')];i=0
 while i<len(text):
  c=text[i]
  if quoted:
   if c==quoted:
    if i+1<len(text)and text[i+1]==quoted:i+=1
    else:quoted=None
  elif c in("'",'"'):quoted=c
  elif c=='(':depth+=1
  elif c==')':depth-=1
  elif c==','and depth==0:fields.append(text[start:i]);start=i+1
  i+=1
 fields.append(text[start:]);kept=[]
 for field in fields:
  f=field.strip()
  if not f:continue
  if re.match(r'(CONSTRAINT|CHECK|FOREIGN KEY|PRIMARY KEY|UNIQUE)\b',f,re.I):continue
  f=re.split(r'\s+(?:DEFAULT|GENERATED|CONSTRAINT|CHECK|REFERENCES)\s+',f,maxsplit=1,flags=re.I)[0].strip()
  kept.append(f)
 return head+'\n '+',\n '.join(kept)+'\n'+tail

def function_prototype(stmt):
 s=clean_start(stmt)
 m=re.search(r'\bAS\s+(\$[\w]*\$)',s,re.I)
 if not m:return None
 tag=m.group(1);end=s.find(tag,m.end())
 if end<0:return None
 header=s[:m.start()]
 header=re.sub(r'\bLANGUAGE\s+\w+','LANGUAGE plpgsql',header,flags=re.I)
 # Fresh schema has no installed prototype bodies. Every invocation refuses;
 # signatures are present solely for SQL-language compile type resolution.
 return header+" AS $compile_only$ BEGIN RAISE EXCEPTION 'COMPILE_ONLY_STANDIN_NEVER_NATIVE_OR_BUSINESS_PROOF'; END $compile_only$;"

native_parts=[];native_protos=[];seen_tables=set();extra_files=[]
for source_name,source_text in [('clone_native_schema_0.sql',native)]+[(str(p.relative_to(ROOT)),p.read_text())for p in [ROOT/'supabase/release/cp6-t3/20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql',ROOT/'supabase/release/cp6-t3/20260926050000_erp_v2_6_20be_cp6_conversion_redye_pocket.sql']]:
 for i,s in enumerate(split_sql(source_text)):
  c=clean_start(s)
  mt=re.match(r'CREATE TABLE (?:IF NOT EXISTS )?(erp\.\w+)',c,re.I)
  if mt and mt.group(1)not in seen_tables:
   seen_tables.add(mt.group(1));native_parts.append({'id':f'{source_name}:native-table:{i}','sql':table_scaffold(c),'kind':'native_table_actual_types_only'})
  elif source_name=='clone_native_schema_0.sql'and re.match(r'CREATE SEQUENCE\s+erp\.',c,re.I):native_parts.append({'id':f'native-sequence:{i}','sql':c,'kind':'native_sequence'})
  elif source_name=='clone_native_schema_0.sql'and re.match(r'ALTER TABLE (?:ONLY )?erp\.',c,re.I)and('PRIMARY KEY'in c or'UNIQUE ('in c):native_parts.append({'id':f'native-key:{i}','sql':c,'kind':'native_actual_unique_key'})
  elif re.match(r'CREATE (?:OR REPLACE )?FUNCTION\s+erp\.',c,re.I):
   proto=function_prototype(c)
   if proto:
    proto=re.sub(r'^CREATE (?:OR REPLACE )?FUNCTION','CREATE OR REPLACE FUNCTION',proto,flags=re.I)
    native_protos.append({'id':f'{source_name}:native-signature:{i}','sql':proto,'kind':'RAISING_COMPILE_ONLY_STANDIN','source_sha256':hashlib.sha256(c.encode()).hexdigest()})

# Actual prior CP7 table types and function signatures. Bodies are raising
# stand-ins here; these features are not exercised as business behavior.
prior=[]
for rel in ['scripts/cp7-src/sales/commands.sql','scripts/cp7-src/sales/correction.sql','scripts/cp7-src/sales/return-correction.sql','scripts/cp7-src/sales/payment-correction.sql']:
 for i,s in enumerate(split_sql((ROOT/rel).read_text())):
  c=clean_start(s)
  if re.match(r'create table ',c,re.I):prior.append({'id':f'{rel}:{i}','sql':c,'kind':'prior_actual_table'})
  elif re.match(r'create (?:or replace )?function ',c,re.I):
   proto=function_prototype(c)
   if proto:prior.append({'id':f'{rel}:{i}','sql':proto,'kind':'RAISING_COMPILE_ONLY_STANDIN'})

module=ast.parse((ROOT/'scripts/cp7_customer_credit/integration/owning_bundle.py').read_text())
base=[]
for n in module.body:
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name)and t.id=='SQL_FILES'for t in n.targets):base=list(ast.literal_eval(n.value))
base += ['native-empty/01_native_empty_facts.sql','native-empty/02_native_empty_callbacks.sql']
# Types are installed separately; functions are then validator-compiled with
# check_function_bodies=on to a fixed point. This is NOT assembler-order proof.
base += [str(p.relative_to(ROOT/'scripts/cp7_customer_credit')) for p in sorted((ROOT/'scripts/cp7_customer_credit/reconciliation').glob('*.sql'))]
base=list(dict.fromkeys(base))
parts=[];files={}
for rel in base:
 path=ROOT/'scripts/cp7_customer_credit'/rel
 data=path.read_bytes();files[rel]=hashlib.sha256(data).hexdigest()
 dest=OUT/'compile_snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 for i,s in enumerate(split_sql(data.decode())):
  c=clean_start(s)
  if not c:continue
  if re.match(r'do\s+\$not_an_installer\$',c,re.I):continue
  kind='other'
  if re.match(r'create (?:or replace )?function ',c,re.I):kind='actual_product_function'
  elif re.match(r'create (?:schema|domain|type|table) ',c,re.I):kind='actual_product_type'
  elif re.match(r'alter table ',c,re.I):kind='actual_product_alter_table'
  elif re.match(r'do ',c,re.I):kind='actual_product_do'
  parts.append({'id':f'{rel}:{i}','sql':c,'kind':kind})
report={'classification':'COMPILE_ONLY_ACTUAL_TYPES_WITH_RAISING_EXTERNAL_SIGNATURE_STANDINS','files':files,'native_parts':native_parts,'native_prototypes':native_protos,'prior':prior,'parts':parts}
(OUT/'compile_input.json').write_text(json.dumps(report))
print(json.dumps({'native_types_keys':len(native_parts),'native_signature_standins':len(native_protos),'prior_parts':len(prior),'actual_product_statements':len(parts),'files':len(files)}))
