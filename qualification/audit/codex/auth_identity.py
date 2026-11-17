"""Bind retained Auth inputs to the verified public workflow run.

The retained case-plan file and its reviewed hashes remain unchanged. Only
its CI identity adapter is replaced; actor/RPC plans and business checks stay.
"""
from pathlib import Path
from types import FunctionType, ModuleType
from p21.mode import EVENT, dispatch_product

ENTRY = 'qualification/audit/codex/auth_identity.py'


def bind(retained, owner):
    runner_path = Path(owner.__file__).absolute().parents[2]
    owner.tracked_source(runner_path, ENTRY)
    owner.require(Path(retained.__file__).absolute()
                  == runner_path / 'qualification/global_fixtures/auth_case_plan.py',
                  'AUDITOR_P20_EXACT_RETAINED_AUTH_PLAN_REQUIRED')
    result = ModuleType('global_auth_case_plan_with_auditor_dispatch')
    result.__dict__.update(vars(retained))
    for name, function in vars(retained).items():
        if isinstance(function, FunctionType) and function.__globals__ is retained.__dict__:
            result.__dict__[name] = owner.clone(function, result.__dict__)

    def attempt_kwargs(source_identity):
        owner.require(type(source_identity) is dict
                      and source_identity.get('candidate_head') == retained.CANDIDATE_HEAD
                      and source_identity.get('candidate_tree') == retained.CANDIDATE_TREE
                      and source_identity.get('candidate_src') == retained.APP_TREE,
                      'AUDITOR_P20_AUTH_EXACT_BASE_CANDIDATE_REQUIRED')
        head = owner.git(runner_path, 'rev-parse', 'HEAD')
        # Bind the synthetic Auth attempt to the actual Actions push and checkout.
        github = owner.runner_ci_identity(runner_path, head)
        _, owning_raw = owner.tracked_source(runner_path, owner.RUNNER_ENTRY)
        expected = dict(entry=owner.RUNNER_ENTRY, head=head,
                        tree=owner.git(runner_path, 'rev-parse', 'HEAD^{tree}'),
                        source=owner.pin(owning_raw), github=github)
        owner.require(source_identity.get('runner') == expected
                      and head != source_identity['candidate_head']
                      and github['event'] == EVENT
                      and github['head'] == github['merge'] == head
                      and github['base'] is None and github['pr'] is None
                      and github['candidate_sha'] == dispatch_product()
                      and github['run_attempt'] == 1,
                      'AUDITOR_P20_AUTH_EXACT_DISPATCH_DECLARATION_REQUIRED')
        return dict(head=source_identity['candidate_head'],
                    attempt=f"{github['run_id']}-{github['run_attempt']}",
                    allowed_actors=retained.ACTOR_PLAN, allowed_rpcs=retained.RPC_PLAN)

    result.attempt_kwargs = attempt_kwargs
    return result
