#!/usr/bin/env python3
"""Deterministic source/structure qualification for the generated AC patch."""
from __future__ import annotations

import collections
import hashlib
import json
import re
from pathlib import Path

import cp6_v2620ac_build_sql as builder
import cp6_v2620ac_runtime as runtime


REPORT = Path("cp6-proof/CP6_V2620AC_STATIC_QUALIFICATION.json")


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def lexical_balance(source: str, label: str) -> dict[str, int]:
    """Reject unterminated SQL quoting/comments and unbalanced outer parens."""
    index = 0
    state = "normal"
    dollar = ""
    block_depth = 0
    parens = 0
    dollar_blocks = 0
    while index < len(source):
        char = source[index]
        pair = source[index:index + 2]
        if state == "line":
            if char == "\n":
                state = "normal"
            index += 1
            continue
        if state == "block":
            if pair == "/*":
                block_depth += 1
                index += 2
            elif pair == "*/":
                block_depth -= 1
                index += 2
                if block_depth == 0:
                    state = "normal"
            else:
                index += 1
            continue
        if state == "single":
            if char == "'" and source[index:index + 2] == "''":
                index += 2
            elif char == "'":
                state = "normal"
                index += 1
            elif char == "\\":
                index += 2
            else:
                index += 1
            continue
        if state == "double":
            if char == '"' and source[index:index + 2] == '""':
                index += 2
            elif char == '"':
                state = "normal"
                index += 1
            else:
                index += 1
            continue
        if state == "dollar":
            if source.startswith(dollar, index):
                index += len(dollar)
                state = "normal"
            else:
                index += 1
            continue

        if pair == "--":
            state = "line"
            index += 2
        elif pair == "/*":
            state = "block"
            block_depth = 1
            index += 2
        elif char == "'":
            state = "single"
            index += 1
        elif char == '"':
            state = "double"
            index += 1
        elif char == "$":
            match = re.match(r"\$[A-Za-z_][A-Za-z_0-9]*\$|\$\$", source[index:])
            if match:
                dollar = match.group(0)
                dollar_blocks += 1
                state = "dollar"
                index += len(dollar)
            else:
                index += 1
        elif char == "(":
            parens += 1
            index += 1
        elif char == ")":
            parens -= 1
            if parens < 0:
                raise AssertionError(f"{label}:unexpected closing parenthesis")
            index += 1
        else:
            index += 1
    if state not in ("normal", "line") or block_depth or parens:
        raise AssertionError(
            f"{label}:lexical imbalance state={state} block={block_depth} parens={parens}"
        )
    return {"dollar_blocks": dollar_blocks, "outer_parenthesis_balance": parens}


def record_alias_qualification(
    migration: str, rollback: str, functions: list[str]
) -> dict[str, int]:
    """Reject PL/pgSQL record variables reused as SQL relation aliases."""
    blocks: list[tuple[str, str]] = []
    do_pattern = re.compile(
        r"(?ms)^do \$(?P<tag>[A-Za-z_][A-Za-z_0-9]*)\$"
        r"(?P<body>.*?)^\$(?P=tag)\$;"
    )
    for source_name, source in (("migration", migration), ("rollback", rollback)):
        blocks.extend(
            (f"{source_name}:{match.group('tag')}", match.group("body"))
            for match in do_pattern.finditer(source)
        )
    blocks.extend((f"function:{index}", definition)
                  for index, definition in enumerate(functions, start=1))

    alias_pattern = re.compile(
        r"\b(?:from|join)\s+"
        r"(?:[A-Za-z_][A-Za-z_0-9]*\.)?[A-Za-z_][A-Za-z_0-9]*"
        r"(?:\s*\([^;\n]*?\))?\s+(?:as\s+)?"
        r"([A-Za-z_][A-Za-z_0-9]*)",
        re.I,
    )
    record_count = 0
    for label, body in blocks:
        declaration = re.search(r"\bdeclare\b(.*?)\bbegin\b", body, re.S | re.I)
        if declaration is None:
            continue
        records = set(re.findall(
            r"\b([A-Za-z_][A-Za-z_0-9]*)\s+record\b",
            declaration.group(1),
            re.I,
        ))
        aliases = set(alias_pattern.findall(body))
        collisions = sorted(records & aliases)
        if collisions:
            raise AssertionError(
                f"AC_PLPGSQL_RECORD_RELATION_ALIAS_COLLISION:{label}:{collisions}"
            )
        record_count += len(records)
    return {
        "blocks_checked": len(blocks),
        "record_variables_checked": record_count,
        "collisions": 0,
    }


def applied_segment(migration: str) -> str:
    start_marker = "-- Generated only from the 709/709 reviewed disposition; do not hand-edit.\n"
    end_marker = "\ndo $installed_v2620ac$\n"
    if migration.count(start_marker) != 1 or migration.count(end_marker) != 1:
        raise AssertionError("AC_APPLY_SEGMENT_MARKERS")
    return migration.split(start_marker, 1)[1].split(end_marker, 1)[0]


def function_definitions(segment: str) -> list[str]:
    starts = list(re.finditer(r"(?m)^CREATE OR REPLACE FUNCTION erp\.", segment))
    first_view = segment.find("CREATE OR REPLACE VIEW erp.")
    statements = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else first_view
        statement = segment[start.start():end].rstrip()
        if not statement.endswith("$function$;"):
            raise AssertionError("AC_FUNCTION_TERMINATOR")
        statements.append(statement + "\n")
    # pg_get_functiondef ends in a newline and does not include the SQL command
    # terminator added by the migration builder.
    return [statement[:-2] + "\n" for statement in statements]


def view_statements(segment: str) -> list[str]:
    start = segment.find("CREATE OR REPLACE VIEW erp.")
    if start < 0:
        return []
    view_and_defaults = segment[start:]
    defaults = view_and_defaults.find("\nalter table erp.")
    view_source = view_and_defaults if defaults < 0 else view_and_defaults[:defaults]
    return re.findall(
        r"(?ms)^CREATE OR REPLACE VIEW erp\..*?;\n(?=\n|$)",
        view_source,
    )


def pre_admission_verifier_qualification() -> dict[str, object]:
    """Prove pre-admission verification cannot enter relation deparsing."""
    original_state = runtime._verify_installation_state
    original_pins = runtime.pins
    original_functions = runtime._verify_functions
    original_views = runtime._verify_views
    original_defaults = runtime._verify_defaults
    relation_verifier_calls = 0
    cardinality_negative_control_rejected = False

    def forbidden_relation_verifier(*_args: object, **_kwargs: object) -> dict:
        nonlocal relation_verifier_calls
        relation_verifier_calls += 1
        raise AssertionError("AC_PRE_ADMISSION_ENTERED_RELATION_VERIFIER")

    runtime._verify_installation_state = lambda _cur: True
    runtime.pins = lambda: {"functions": []}
    runtime._verify_views = forbidden_relation_verifier
    runtime._verify_defaults = forbidden_relation_verifier
    try:
        runtime._verify_functions = lambda _cur, _payload: {
            f"FUNCTION:probe_{index}": {"kind": "FUNCTION"}
            for index in range(115)
        }
        observations = runtime.verified_pre_admission_successor(object())
        if len(observations) != 115 or relation_verifier_calls:
            raise AssertionError("AC_PRE_ADMISSION_VERIFIER_SCOPE_MISMATCH")
        pre_admission_relation_calls = relation_verifier_calls

        runtime._verify_functions = lambda _cur, _payload: {}
        try:
            runtime.verified_pre_admission_successor(object())
        except AssertionError as exc:
            if str(exc) != "AC_PRE_ADMISSION_FUNCTION_CARDINALITY":
                raise
            cardinality_negative_control_rejected = True
        else:
            raise AssertionError("AC_PRE_ADMISSION_CARDINALITY_ACCEPTED")

        runtime._verify_functions = lambda _cur, _payload: {
            f"FUNCTION:probe_{index}": {"kind": "FUNCTION"}
            for index in range(115)
        }

        def full_views(_cur: object, _payload: object) -> dict:
            nonlocal relation_verifier_calls
            relation_verifier_calls += 1
            return {
                f"VIEW:probe_{index}": {"kind": "VIEW"}
                for index in range(13)
            }

        def full_defaults(_cur: object, _payload: object) -> dict:
            nonlocal relation_verifier_calls
            relation_verifier_calls += 1
            return {
                f"COLUMN_DEFAULT:probe_{index}": {"kind": "COLUMN_DEFAULT"}
                for index in range(144)
            }

        runtime._verify_views = full_views
        runtime._verify_defaults = full_defaults
        full_observations = runtime.verified_successor(object())
        if (
            len(full_observations) != 272
            or relation_verifier_calls - pre_admission_relation_calls != 2
        ):
            raise AssertionError("AC_FULL_RELATION_VERIFIER_SCOPE_MISMATCH")
    finally:
        runtime._verify_installation_state = original_state
        runtime.pins = original_pins
        runtime._verify_functions = original_functions
        runtime._verify_views = original_views
        runtime._verify_defaults = original_defaults

    return {
        "function_count": len(observations),
        "relation_deparsing_skipped": pre_admission_relation_calls == 0,
        "cardinality_negative_control_rejected": (
            cardinality_negative_control_rejected
        ),
        "full_relation_verifier_count": (
            relation_verifier_calls - pre_admission_relation_calls
        ),
    }


def run() -> dict[str, object]:
    source_hashes = runtime.verify_source_files()
    source_head, source_tree = runtime.verify_audit_source()
    disposition = json.loads(runtime.DISPOSITION.read_text(encoding="utf-8"))
    pins = runtime.pins()
    migration = runtime.MIGRATION.read_text(encoding="utf-8")
    rollback = runtime.ROLLBACK.read_text(encoding="utf-8")
    if migration.count("\nbegin;\n") != 1 or not migration.endswith("commit;\n"):
        raise AssertionError("AC_MIGRATION_TRANSACTION_SHAPE")
    if rollback.count("\nbegin;\n") != 1 or not rollback.endswith("commit;\n"):
        raise AssertionError("AC_ROLLBACK_TRANSACTION_SHAPE")
    if "\n+" in migration or "\n+" in rollback:
        raise AssertionError("AC_GENERATOR_PATCH_PREFIX_LEAK")
    evidence_header = f"-- Evidence SHA-256: {runtime.DISPOSITION_SHA256}\n"
    if migration.count(evidence_header) != 1:
        raise AssertionError("AC_EVIDENCE_HEADER_MISMATCH")
    if runtime.MIGRATION_SHA256 not in rollback:
        raise AssertionError("AC_ROLLBACK_MIGRATION_SOURCE_PIN_MISSING")

    decisions = collections.Counter(
        item["decision"] for item in disposition["dispositions"]
    )
    occurrence_ids = [
        item["occurrence_id"] for item in disposition["dispositions"]
    ]
    if decisions != {"CHANGE": 422, "KEEP": 285, "EXCLUDE": 2}:
        raise AssertionError("AC_DISPOSITION_COUNTS")
    if not occurrence_ids or len(occurrence_ids) != len(set(occurrence_ids)):
        raise AssertionError("AC_DISPOSITION_IDENTITIES")
    exclusions = {
        (item["object_identity"], item["action"])
        for item in disposition["dispositions"]
        if item["decision"] == "EXCLUDE"
    }
    if exclusions != {
        ("erp._cp3_canonical_date(date)", "DATE_ONLY_CANONICAL_FORMAT"),
        (
            "erp._cp3_parse_canonical_date(text,text)",
            "DATE_ONLY_CANONICAL_ROUND_TRIP",
        ),
    }:
        raise AssertionError("AC_EXCLUSION_SET")
    absolute = [
        item for item in disposition["dispositions"]
        if item["classification"] == "ABSOLUTE_WALL_CLOCK"
    ]
    if len(absolute) != 212 or any(item["decision"] != "KEEP" for item in absolute):
        raise AssertionError("AC_ABSOLUTE_WALL_CLOCK_DISPOSITION")

    segment = applied_segment(migration)
    functions = function_definitions(segment)
    alias_qualification = record_alias_qualification(
        migration, rollback, functions
    )
    view_probe_token = "pg_temp.cp6_ac_normalized_view_sha256("
    for label, source in (("migration", migration), ("rollback", rollback)):
        if (
            source.count(
                "create or replace function "
                "pg_temp.cp6_ac_normalized_view_sha256(p_body text)"
            ) != 1
            or source.count(view_probe_token) != 3
        ):
            raise AssertionError(f"AC_ENGINE_NORMALIZED_VIEW_GUARD:{label}")
    if "r.before_sha256 not in(v_false,v_pretty)" in migration + rollback:
        raise AssertionError("AC_RAW_VIEW_DUMP_HASH_GUARD_REINTRODUCED")
    acl_control = builder.relation_acl(
        "GRANT SELECT ON TABLE erp.ac_acl_probe TO authenticated;\n"
        "GRANT SELECT,MAINTAIN ON TABLE erp.ac_acl_probe TO anon;\n"
        "GRANT ALL ON TABLE erp.ac_acl_probe TO service_role;\n",
        "ac_acl_probe",
    )
    if acl_control != [
        "anon=rm/postgres",
        "authenticated=r/postgres",
        "postgres=arwdDxtm/postgres",
        "service_role=arwdDxtm/postgres",
    ]:
        raise AssertionError("AC_POSTGRES17_MAINTAIN_ACL_PIN")
    if builder.relation_acl("", "ac_owner_only_probe") != [
        "postgres=arwdDxtm/postgres"
    ]:
        raise AssertionError("AC_OWNER_ONLY_EFFECTIVE_ACL_PIN")
    effective_acl_counts = {
        "migration_catalog": migration.count(
            "acldefault('r',catalog_rel.relowner)"
        ),
        "migration_capsule": migration.count("acldefault('r',c.relowner)"),
        "rollback_live": rollback.count("acldefault('r',v.relowner)"),
    }
    if effective_acl_counts != {
        "migration_catalog": 2,
        "migration_capsule": 1,
        "rollback_live": 1,
    }:
        raise AssertionError(
            f"AC_EFFECTIVE_VIEW_ACL_GUARDS:{effective_acl_counts}"
        )
    expected_functions = {item["after_sha"]: item for item in pins["functions"]}
    observed_function_hashes = [sha(definition) for definition in functions]
    if (
        len(functions) != 115
        or len(expected_functions) != 115
        or set(observed_function_hashes) != set(expected_functions)
    ):
        raise AssertionError("AC_APPLIED_FUNCTION_SET")

    structural_by_hash = {
        item["after_sha256"]: item["structural_contract"]
        for item in disposition["objects"]
        if item["object_type"] == "FUNCTION" and item["changed_occurrences"]
    }
    structural_patterns = {
        "returns": r"(?m)^ RETURNS .+$",
        "language": r"(?m)^ LANGUAGE .+$",
        "security": r"(?m)^ SECURITY (?:DEFINER|INVOKER)$",
        "search_path": r"(?m)^ SET search_path TO .+$",
    }
    for definition, digest in zip(functions, observed_function_hashes, strict=True):
        expected = structural_by_hash.get(digest)
        if expected is None:
            raise AssertionError("AC_FUNCTION_STRUCTURE_PIN_MISSING")
        observed = {
            key: re.findall(pattern, definition)
            for key, pattern in structural_patterns.items()
        }
        if observed != expected:
            raise AssertionError(
                "AC_FUNCTION_SECURITY_OR_SIGNATURE_STRUCTURE_CHANGED:"
                + expected_functions[digest]["identity"]
            )

    views = view_statements(segment)
    expected_view_hashes = {item["after_body_sha"] for item in pins["views"]}
    observed_view_hashes = set()
    for statement in views:
        match = re.match(r"CREATE OR REPLACE VIEW erp\.([A-Za-z_][A-Za-z0-9_]*)", statement)
        if match is None:
            raise AssertionError("AC_VIEW_NAME_PARSE")
        body, _ = builder.parse_view(statement.rstrip(), match.group(1))
        observed_view_hashes.add(sha(body))
    if len(views) != 13 or observed_view_hashes != expected_view_hashes:
        raise AssertionError("AC_APPLIED_VIEW_SET")

    default_lines = set(re.findall(
        r"(?m)^alter table erp\.[a-zA-Z_][a-zA-Z0-9_]* alter column "
        r"[a-zA-Z_][a-zA-Z0-9_]* set default .*;$",
        segment,
    ))
    expected_defaults = {
        f"alter table erp.{item['table']} alter column {item['column']} "
        f"set default {item['after']};"
        for item in pins["table_defaults"]
    }
    if len(default_lines) != 144 or default_lines != expected_defaults:
        raise AssertionError("AC_APPLIED_DEFAULT_SET")

    executable = re.sub(r"(?m)--.*$", "", segment)
    stale = {
        "now": len(re.findall(r"\bnow\s*\(", executable, re.I)),
        "current_date": len(re.findall(r"\bcurrent_date\b", executable, re.I)),
        "current_timestamp": len(re.findall(r"\bcurrent_timestamp\b", executable, re.I)),
        "transaction_timestamp": len(re.findall(
            r"\btransaction_timestamp\s*\(", executable, re.I
        )),
    }
    if any(stale.values()):
        raise AssertionError("AC_STALE_TRANSACTION_CLOCK_IN_APPLIED_SURFACE:" + str(stale))

    pre_admission_verifier = pre_admission_verifier_qualification()
    if not pre_admission_verifier["relation_deparsing_skipped"]:
        raise AssertionError("AC_PRE_ADMISSION_RELATION_DEPARSE_MISMATCH")

    result: dict[str, object] = {
        "format": "CP6_V2620AC_STATIC_QUALIFICATION_V1",
        "status": "PASS",
        "head": source_head,
        "tree": source_tree,
        "source_hashes": source_hashes,
        "decisions": dict(decisions),
        "occurrence_count": len(occurrence_ids),
        "function_count": len(functions),
        "view_count": len(views),
        "table_default_count": len(default_lines),
        "function_structural_contracts_preserved": True,
        "plpgsql_record_alias_qualification": alias_qualification,
        "engine_normalized_view_guards": {
            "migration": 2,
            "rollback": 2,
            "source_hashes_retained": True,
        },
        "postgres17_maintain_acl_pinned": True,
        "effective_view_acl_guards": effective_acl_counts,
        "pre_admission_verifier": pre_admission_verifier,
        "stale_transaction_clock_tokens": stale,
        "migration_lexical": lexical_balance(migration, "migration"),
        "rollback_lexical": lexical_balance(rollback, "rollback"),
        "production_go": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    outcome = run()
    print(json.dumps(outcome, sort_keys=True))
