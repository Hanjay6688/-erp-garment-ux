"""Static exact-anchor check; source-format stand-ins, NOT installed captures.

The installed assembler MUST independently capture/verify the complete parent.
This check combines existing Native dump bodies with retained transformations
only to find broken anchors early. It never installs or proves money behavior.
"""
from pathlib import Path
import importlib.util,json,re,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cp7_credit_correction_de import native_delta as d
ROOT=Path(__file__).resolve().parents[2];CREDIT=ROOT/'scripts/cp7_customer_credit'

def load(name,file):
    spec=importlib.util.spec_from_file_location(name,file);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def statement(file,name):
    text=Path(file).read_text();start=re.search(r'create (?:or replace )?function '+re.escape(name)+r'\(',text,re.I)
    if not start:raise ValueError('STATIC_FUNCTION_NOT_FOUND:'+name)
    tail=text[start.start():];dollar=re.search(r'\$(?:[a-zA-Z_0-9]*)\$',tail);end=tail.index(dollar[0],dollar.end())+len(dollar[0])+1
    return re.sub(r'^create (?:or replace )?function','CREATE OR REPLACE FUNCTION',tail[:end],flags=re.I)

def body(definition):
    q=re.search(r'\$(?:[a-zA-Z_0-9]*)\$',definition);return definition[q.end():definition.index(q[0],q.end())]

def captures(dump):
    a=load('de_admission',CREDIT/'admission/03_native_admission_transform.py')
    l=load('de_native_ledger',CREDIT/'ledger/03_native_copy_transform.py')
    post=statement(dump,'erp.post_sales_return');post=post.replace(body(post),a.post_return(body(post)),1)
    rev=statement(dump,'erp.reverse_sales_return');b=body(rev)
    b=re.sub(r'\bbegin\b','begin\n perform cp7_sales_return_correction.require_context();',b,count=1,flags=re.I)
    b=b.replace('erp.reverse_fg_movement(','cp7_sales_return_correction.reverse_fg_movement(').replace('erp.reverse_journal(','cp7_sales_return_correction.reverse_journal(')
    b=b.replace("((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date","((h.physical_at AT TIME ZONE 'Asia/Jakarta'::text))::date")
    rev=rev.replace(body(rev),a.reverse_return(b),1).replace('FUNCTION erp.reverse_sales_return(','FUNCTION cp7_sales_return_correction.reverse_sales_return(',1)
    journal=statement(dump,'erp.post_journal');journal=journal.replace(body(journal),l.post_body(body(journal)),1).replace('FUNCTION erp.post_journal(','FUNCTION cp7_credit._post_journal_bound(',1)
    result={d.POST:post,d.REVERSE:rev,d.JOURNAL:journal}
    for sig,file,name in (
      (d.COMMAND,'../cp7-src/sales/return-correction.sql','cp7_sales_return_correction.command'),
      (d.BASE,'coordinator/05_factual_profile.sql','cp7_credit.assert_simple_native_base_v1'),
      (d.EVENTS,'coordinator/01_coordinator_facts.sql','cp7_credit.initial_base_events_v1'),
      (d.ORDINAL,'coordinator/05_factual_profile.sql','cp7_credit.initial_ordinal_input_v1'),
      (d.PROFILE,'coordinator/05_factual_profile.sql','cp7_credit.assert_current_source_plan_profile'),
      (d.PROVENANCE,'coordinator/05_factual_profile.sql','cp7_credit.assert_financial_materialization_provenance'),
      (d.CLOSURE,'coordinator/06_finish_and_closed_routes.sql','cp7_credit.enforce_initial_return_closure_v1'),
      (d.PUBLIC_COMMAND,'../cp7-src/sales/return-correction.sql','public.erp_cp7_correct_sales_return_v1'),
      (d.PUBLIC_WORKSPACE,'../cp7-src/sales/return-correction.sql','public.erp_cp7_get_sales_return_correction_v1')):
        result[sig]=statement(CREDIT/file,name)
    result[d.BASE]=result[d.BASE].replace("\n  or exists(select 1 from cp7_payment_correction.links l join erp.sales_payments p0 on p0.id in(l.original_id,l.replacement_id)where p0.sale_id=p_sale)",'')
    result[d.PROFILE]=result[d.PROFILE].replace('FUNCTION cp7_credit.assert_current_source_plan_profile(','FUNCTION cp7_credit._consumer_root_source_profile_v1(',1)
    return result

def main(dump):
    original=captures(dump);derived=d.derive(original);refused=[]
    for key in d.CAPTURES:
        mutated=dict(original);mutated[key]=original[key]+original[key]
        try:d.derive(mutated)
        except ValueError:refused.append(key)
        else:raise AssertionError('DUPLICATED_PREDECESSOR_ACCEPTED:'+key)
    # The actual Native financial/physical bodies are identical after reversing
    # ONLY the declared callback/schema substitutions in their private copies.
    for key in(d.POST,d.REVERSE,d.JOURNAL):
        assert len(derived[d.COPIES[key]].splitlines())==len(original[key].splitlines()),key
    return dict(status='PASS',scope='STATIC_SOURCE_FORMAT_STANDINS_ONLY',declared_derivations=len(derived),duplicated_predecessors_refused=refused,Native_execution=False,installed_parent_verified=False)
if __name__=='__main__':print(json.dumps(main(sys.argv[1]),indent=2))
