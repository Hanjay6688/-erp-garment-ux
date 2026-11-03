"""Fetch both exact accepted canonical archives; every gate precedes GET.

Reuse the complete retained fetcher through reversible binding routes only.
This preparation has no accepted receipts and cannot issue a network request.
"""
from hashlib import sha256
from pathlib import Path
from types import ModuleType,SimpleNamespace
import importlib.util,json
from money_execution_bindings import admission
import money_current_parent_runtime as runtime

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PIN=dict(bytes=4764,sha256='28dc2c71b9bb88fa72b5049de75561edf2856a4c2b216dedc6c1da9683412153')
KINDS={
    'MANDOR':dict(file='MANDOR17_PARENT_ROOT_ACTUAL_INTAKE.json',main='CP7_FG_MANDOR_NATIVE9.json',
        label='SKU_CURRENT_MANDOR17',folder='sku-current-mandor17',archive='QUALIFIED_MANDOR17.zip',
        output='SKU_CURRENT_MANDOR17_ORIGINAL_ADMISSION.json',sources='qualified_current_Mandor_sources'),
    'SKU':dict(file='SKU_MONEY19_CHILD_ROOT_ACTUAL_INTAKE.json',main='CP7_SKU_COST_MONEY_QUALIFICATION.json',
        label='SKU_CURRENT_MONEY19',folder='sku-current-money19',archive='QUALIFIED_MONEY19.zip',
        output='SKU_CURRENT_MONEY19_ORIGINAL_ADMISSION.json',sources='qualified_SKU_cost_money_sources'),
}


def derive(kind):
    spec=importlib.util.spec_from_file_location('sku_exact_original_canonical_fetcher',
        ROOT/'scripts/current-mandor-shop-native-qualification/fetch_parent.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    text,_=old.derive();original=text
    if admission.pin(text.encode())!=PIN:raise ValueError('SKU_COMPOSITE_EXACT_RETAINED_FETCHER')
    item=KINDS[kind]
    routes=[
        ("required=load('permanent_closed_actual_parent_before_any_fetch',HERE/'admission.py')",'required=_ACTUAL_ROOT_BINDING'),
        ("MAIN='CP7_AFUI_GOOD_NONPAYABLE_FULL15.json'","MAIN="+repr(item['main'])),
        ("HERE/'AFUI15_PARENT_ROOT_ACTUAL_INTAKE.json'","HERE/"+repr(item['file'])),
        ("'mandor-afui15-parent'",repr(item['folder'])),
        ("'QUALIFIED_AFUI15.zip'",repr(item['archive'])),
        ("'cp6-proof/t3/AFUI15_PARENT_ORIGINAL_ADMISSION.json'",repr('cp6-proof/t3/'+item['output'])),
        ("receipt['qualified_Afui_good_nonpayable_sources']","receipt["+repr(item['sources'])+"]"),
        ('entire_qualified_Afui_good_nonpayable_sources=','entire_'+item['sources']+'='),
    ]
    import re
    labels=sorted(set(re.findall(r"'([^'\n]*(?:MANDOR_PARENT|EXACT_TERMINAL_AFUI15)[^'\n]*)'",text)))
    for label in labels:
        replacement=label.replace('MANDOR_PARENT',item['label']).replace('AFUI15',kind+'_'+('17'if kind=='MANDOR'else'19'))
        routes.append((repr(label),repr(replacement)))
    for before,after in routes:
        if text.count(before)!=1 or after in text:raise ValueError('SKU_COMPOSITE_EXACT_FETCH_ROUTE:'+before)
        text=text.replace(before,after,1)
    recovered=text
    for before,after in reversed(routes):
        if recovered.count(after)!=1:raise ValueError('SKU_COMPOSITE_EXACT_FETCH_INVERSE')
        recovered=recovered.replace(after,before,1)
    if recovered!=original:raise ValueError('SKU_COMPOSITE_COMPLETE_FETCHER_NOT_RECOVERED')
    compile(text,'current_parent_exact_'+kind+'_fetch','exec')
    return text,dict(original=PIN,derived_sha256=sha256(text.encode()).hexdigest(),exact_routes=len(routes),
        complete_original_recovered=True,terminal_run_job_attempt_head_archive_SHA_size_CRC_and_paths_unchanged=True,
        actual_GitHub_GETs=0,actual_composite_cases=0,production_go=False)


def main():
    parent_raw,sku_raw,_=runtime.actual_inputs()
    for kind,raw,head,reference in (
        ('MANDOR',parent_raw,admission.PARENT_HEAD,admission.PARENT_ROOT_PIN),
        ('SKU',sku_raw,admission.SKU_HEAD,admission.SKU_ROOT_PIN)):
        receipt=json.loads(raw)
        def exact(data,accepted=raw,value=receipt):
            runtime.actual_inputs()
            if data!=accepted:raise ValueError('SKU_COMPOSITE_ROOT_BYTES_CHANGED_BEFORE_FETCH')
            return value
        text,_=derive(kind)
        module=ModuleType('sku_canonical_actual_'+kind);module.__file__=str(HERE/'derived_'+kind+'_fetch.py')
        module._ACTUAL_ROOT_BINDING=SimpleNamespace(PARENT_HEAD=head,PARENT_ROOT_PIN=reference,parent=exact)
        exec(compile(text,module.__file__,'exec'),module.__dict__);module.main()


if __name__=='__main__':main()
