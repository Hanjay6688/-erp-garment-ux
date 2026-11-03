"""Observe the immutable money candidate and actual retained parent Originals.

This is source admission for a candidate awaiting its first financial run.
It is never a Root financial acceptance, never installs, and grants zero case
credit. The currently published actual-parent gates are not changed here.
"""
from contextlib import chdir
from pathlib import Path
import argparse
import importlib.util
import json
import os
import subprocess
import sys

HERE=Path(__file__).resolve().parent


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],
        env=dict(os.environ,GIT_NO_LAZY_FETCH='1')).decode().strip()


def observe(candidate):
    candidate=Path(candidate).resolve()
    reference=json.loads((HERE/'SOURCE_REFERENCE.json').read_bytes())
    tree=git(candidate,'rev-parse','HEAD^{tree}');head=git(candidate,'rev-parse','HEAD')
    if tree!=reference['candidate_tree']or git(candidate,'status','--porcelain','--untracked-files=no'):
        raise ValueError('CURRENT_MONEY_EXACT_CLEAN_CANDIDATE_SOURCE_TREE_REQUIRED')
    scripts=candidate/'scripts';qualifier=scripts/'current-sku-cost-money-qualification'
    original_path=list(sys.path)
    try:
        cli=load('direct_money_candidate_exact_cli_scope',qualifier/'check.py')
        fence=load('direct_money_candidate_original_DB_network_fence',
            scripts/'current-sku-managed-recovery-native27-qualification/source_context.py')
        sys.path.insert(0,str(scripts))
        with chdir(candidate),cli.retained_arguments(),fence.fenced_source_read()as guard:
            probe=load('direct_money_candidate_original_owning_probe',qualifier/'probe.py')
            proof=probe.runtime().admitted()
    finally:sys.path[:]=original_path
    if proof['status']!='EXACT_NATIVE27_MOVING6_AND_MONEY19_GRAPH_ADMITTED' or proof['actual_ERP_cases']!=0:
        raise ValueError('CURRENT_MONEY_EXACT_SOURCE_ONLY_ADMISSION_REQUIRED')
    if proof['case_ids']!=reference['native_case_ids']or proof['actual_Native_case_ids']!=reference['native_case_ids']:
        raise ValueError('CURRENT_MONEY_COMPLETE_NINETEEN_CANDIDATE_CASE_PLAN_REQUIRED')
    if guard['attempts']or guard['network_nonGit_attempts']:
        raise ValueError('CURRENT_MONEY_SOURCE_ADMISSION_ATTEMPTED_DATABASE_OR_NETWORK')
    if git(candidate,'rev-parse','HEAD^{tree}')!=tree or git(candidate,'rev-parse','HEAD')!=head\
        or git(candidate,'status','--porcelain','--untracked-files=no'):
        raise ValueError('CURRENT_MONEY_CANDIDATE_CHANGED_DURING_SOURCE_ADMISSION')
    value=dict(status='EXACT_PREPARED_MONEY19_SOURCE_NO_RUNTIME_CREDIT',
        declared_candidate_head=reference['candidate_head'],candidate_tree=tree,
        identity_basis='IMMUTABLE_TREE_AND_COMPLETE_SOURCE_GRAPH_NOT_EXECUTED_PUBLIC_COMMIT',
        complete_candidate_source_admission=proof,network_database_guard=guard,
        accepted_parent_requirements_preserved=['actual Native27 and all five gates','actual moving Native6 and all five gates'],
        candidate_money_financially_qualified=False,actual_ERP_cases=0,actual_Native_cases=0,actual_Auth_HTTP_cases=0,
        actual_browser_cases=0,production_go=False,independent_acceptance=False)
    observation=dict(observed_git_head=head,observed_tree=tree,declared_candidate_head=reference['candidate_head'],
        declared_and_observed_tree_equal=True,actual_ERP_cases=0,public_commit_execution_claim=False)
    return value,observation


def check_frozen(candidate_path=None):
    import money_current_parent_runtime as runtime
    _,original,_=runtime.actual_inputs()  # All gates precede source inspection.
    candidate=runtime.FROZEN_SKU
    if candidate_path is not None and Path(candidate_path).resolve()!=candidate.resolve():
        raise ValueError('CURRENT_MONEY_FIXED_FROZEN_SOURCE_CHECKOUT_REQUIRED')
    runtime.frozen(candidate,runtime.admission.SKU_HEAD,runtime.admission.SKU_TREE)
    value,observation=observe(candidate)
    raw=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    if raw!=original:raise ValueError('CURRENT_MONEY_COMPLETE_CANDIDATE_SOURCE_PREFLIGHT_CHANGED')
    return value,observation,raw


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--candidate')
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--report');mode.add_argument('--check',action='store_true');args=parser.parse_args()
    if args.check:
        value,observation,raw=check_frozen(args.candidate)
    else:
        if not args.candidate:parser.error('--report requires --candidate')
        candidate=Path(args.candidate)
        value,observation=observe(candidate)
        raw=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
        path=Path(args.report)
        with path.open('xb')as out:out.write(raw)
        with path.with_suffix('.observation.json').open('x')as out:json.dump(observation,out,indent=2);out.write('\n')
    print(json.dumps(dict(status=value['status'],actual_ERP_cases=0,declared_candidate_head=value['declared_candidate_head'],
        tree=value['candidate_tree'],source_report_bytes=len(raw),complete_candidate_rechecked=args.check)))
