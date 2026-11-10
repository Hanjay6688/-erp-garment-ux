"""Explicit cumulative parent decision, separate from historical source proof.

The old Root remains source-only and immutable. A separate decision replays
the original evidence and the complete observed graph before it may bind the
five owning qualification gates. Neither document is CP7 acceptance.
"""
from collections import Counter
from pathlib import Path
import base64
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OBSERVATION = 'CURRENT_MONEY_SOURCE_OBSERVATION.json'
ORIGINALS = 'CUMULATIVE_ORIGINAL_ARCHIVES.json'
DECISION = 'CUMULATIVE_RUNTIME_BINDING.json'
ENTRY = 'scripts/current-sku-automatic-composite-preparation/qualification.py'
OBSERVED_COMMIT = '1601415d974d5e2fc9d627e35b976e38d6daee8c'
OBSERVATION_PIN = dict(bytes=29362, sha256='c8f937eb0c5e50295ce342179182ecbaf85295039cc9d798f8b8837e2b30731c')
REVIEW_PATH = 'docs/cp7/sku-cumulative-source-20261110/prepare_cumulative_parent.py'
REVIEW_HELPER_PIN = dict(bytes=7489, sha256='4b0f3b258da319196ee8a8ed15da3c61cba35473f30ba77ff4109773b49e2969')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


parent = load('sku_runtime_cumulative_parent', HERE / 'cumulative_parent.py')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def regular(path):
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
            'SKU_CUMULATIVE_REGULAR_ORIGINAL_REQUIRED:' + str(path))
    return path.read_bytes()


def originals(raw):
    value = json.loads(raw)
    require(set(value) == {'MANDOR17_COMBINED_EVIDENCE_20261110.zip',
                           'SKU_MONEY_SOURCE_CLOSED_RECEIPT_20261110.zip'},
            'SKU_CUMULATIVE_EXACT_ORIGINAL_ARCHIVES_REQUIRED')
    return {name: base64.b64decode(data, validate=True) for name, data in value.items()}


def prepare(parent_raw, observation_raw, originals_raw, money_raw, plan_raw):
    root = parent.verify(parent_raw)
    require(parent.pin(observation_raw) == OBSERVATION_PIN,
            'SKU_CUMULATIVE_EXACT_COMPLETE_GRAPH_OBSERVATION_REQUIRED')
    observation = json.loads(observation_raw)
    archives = originals(originals_raw)
    require(parent.pin(regular(ROOT / REVIEW_PATH)) == REVIEW_HELPER_PIN,
            'SKU_CUMULATIVE_IMMUTABLE_ORIGINAL_REVIEWER_REQUIRED')
    review = load('sku_runtime_original_evidence_replay', ROOT / REVIEW_PATH)
    replay = review.prepare(archives['MANDOR17_COMBINED_EVIDENCE_20261110.zip'],
                            archives['SKU_MONEY_SOURCE_CLOSED_RECEIPT_20261110.zip'])
    require(replay == root['cumulative_evidence'], 'SKU_CUMULATIVE_ORIGINAL_REPLAY_CHANGED')
    require(observation['parent_root'] == parent.pin(parent_raw)
            and observation['immutable_money_source'] == parent.pin(money_raw)
            and observation['complete_parent_source_admission']['complete_sources']
                == root['qualified_current_Mandor_sources']
            and observation['proposed_CURRENT_MONEY_GRAPH_PIN']
                == parent.pin(parent.canonical(observation['complete_current_money_graph']))
            and observation['database_network_guard']['attempts'] == []
            and observation['database_network_guard']['network_nonGit_attempts'] == []
            and observation['financial_runtime_activated'] is False
            and observation['all_five_financial_gates_still_closed'] is True
            and observation['actual_ERP_cases'] == 0,
            'SKU_CUMULATIVE_GENUINE_CLOSED_GRAPH_REQUIRED')
    require(Counter(row['group'] for row in replay['cases'])
            == dict(Native9=9, Session4=4, HTTP2=2, BrowserPair=2)
            and replay['original_run']['conclusion'] == 'failure'
            and replay['paired_browser_run']['conclusion'] == 'success'
            and root['runtime_admission'] is False,
            'SKU_CUMULATIVE_KEEP_ORIGINAL_OUTCOMES_AND_SOURCE_ROOT')
    bindings = dict(MANDOR_ROOT_PIN=parent.pin(parent_raw),
                    MONEY_SOURCE_PREFLIGHT_PIN=parent.pin(money_raw),
                    CURRENT_MONEY_GRAPH_PIN=observation['proposed_CURRENT_MONEY_GRAPH_PIN'],
                    COMBINED_NATIVE_PLAN_PIN=parent.pin(plan_raw), OWNING_RUNTIME_ENTRY=ENTRY)
    return dict(status='VERIFIED_CUMULATIVE_PARENT_FOR_SKU_QUALIFICATION_NOT_CP7_ACCEPTANCE',
                mode='CUMULATIVE_15_PLUS_2', historical_source_root_unchanged=True,
                source_observation=OBSERVATION_PIN, source_observed_commit=OBSERVED_COMMIT,
                original_archives={name: parent.pin(raw) for name, raw in archives.items()},
                parent_review=parent.REVIEW_PIN, bindings=bindings,
                backend_source=replay['backend_source'], browser_source=replay['tested_browser_app'],
                original_run=replay['original_run'], paired_browser_run=replay['paired_browser_run'],
                archive_verification=replay['archive_verification'], cases=replay['cases'],
                scope='ONE_DISPOSABLE_SKU_NATIVE25_AND_BROWSER2_QUALIFICATION',
                source_only_root_alone_can_admit_runtime=False,
                independent_acceptance=False, production_go=False, actual_SKU_cases=0)


def review_files(parent_raw, money_raw, plan_raw):
    expected = prepare(parent_raw, regular(HERE / OBSERVATION), regular(HERE / ORIGINALS),
                       money_raw, plan_raw)
    require(regular(HERE / DECISION) == parent.canonical(expected),
            'SKU_CUMULATIVE_EXPLICIT_QUALIFICATION_DECISION_REQUIRED')
    return expected


def validate_actual(gates, parent_raw, money_raw, plan_raw):
    gates.require_ready()  # Never inspect evidence or sources with closed gates.
    receipt = gates.inputs(parent_raw, money_raw, plan_raw)
    value = review_files(parent_raw, money_raw, plan_raw)
    require(set(value['bindings']) == set(gates.GATES)
            and all(getattr(gates, name) == binding for name, binding in value['bindings'].items()),
            'SKU_CUMULATIVE_ALL_FIVE_ACTUAL_BINDINGS_REQUIRED')
    return dict(decision=parent.pin(parent.canonical(value)),
                parent_root=receipt['parent_root'], mode=value['mode'],
                historical_source_root_unchanged=True, independent_acceptance=False,
                production_go=False, actual_SKU_cases=0)
