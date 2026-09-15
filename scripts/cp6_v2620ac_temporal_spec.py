#!/usr/bin/env python3
"""Resolve every open AB temporal occurrence into AC change or exclusion.

The inputs are the immutable function catalog and schema dump recovered from
Native 189 plus the lossless AB occurrence manifest.  No database is touched.
The output is a deterministic writer specification containing transformed
function/view definitions, table-default changes, and one disposition for
every previously open occurrence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


TOKEN_PATTERNS = {
    "CURRENT_DATE": re.compile(r"\bcurrent_date\b", re.I),
    "CURRENT_TIMESTAMP": re.compile(r"\bcurrent_timestamp\b", re.I),
    "NOW": re.compile(r"\bnow\s*\(\s*\)", re.I),
    "CLOCK_TIMESTAMP": re.compile(r"\bclock_timestamp\s*\(\s*\)", re.I),
    "CAST_DATE": re.compile(r"::\s*date\b", re.I),
    "TO_CHAR": re.compile(r"\bto_char\s*\(", re.I),
}

BUSINESS_DATE = (
    "((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date"
)

SAFE_EXCLUSIONS = {
    ("erp._cp3_canonical_date(date)", "TO_CHAR", 1): (
        "DATE_ONLY_CANONICAL_FORMAT",
        "The argument is already a date; timezone conversion cannot change it.",
    ),
    ("erp._cp3_parse_canonical_date(text,text)", "TO_CHAR", 1): (
        "DATE_ONLY_CANONICAL_ROUND_TRIP",
        "The parsed value is date-typed and formatting only validates YYYY-MM-DD.",
    ),
}


KEEP_ACTIONS = {
    "ABSOLUTE_WALL_CLOCK": "KEEP_TRANSACTION_ADVANCING_WALL_CLOCK",
    "DOCUMENTATION_REFERENCE": "KEEP_NON_EXECUTABLE_DOCUMENTATION",
    "EXPLICIT_JAKARTA_CONVERSION": "KEEP_EXPLICIT_JAKARTA_CONVERSION",
    "EXPLICIT_UTC_CONVERSION": "KEEP_EXPLICIT_UTC_CONVERSION",
    "DATE_SERIES_CAST": "KEEP_INTRINSIC_DATE_SERIES_CAST",
    "DATE_TYPE_LITERAL": "KEEP_DATE_TYPED_CAST",
    "EXPLICIT_JAKARTA_DATE_CAST": "KEEP_EXPLICIT_JAKARTA_DATE_CAST",
    "TEXT_TO_DATE_PARSE": "KEEP_TEXT_DATE_PARSE",
    "EXPLICIT_JAKARTA_STATEMENT_CLOCK": "KEEP_JAKARTA_STATEMENT_CLOCK",
    "STATEMENT_CLOCK": "KEEP_STATEMENT_CLOCK",
    "EXPLICIT_ZONE_TIMESTAMP_FORMAT": "KEEP_EXPLICIT_ZONE_FORMAT",
}


KEEP_RATIONALES = {
    "ABSOLUTE_WALL_CLOCK": (
        "Retain a transaction-advancing wall clock for an absolute physical, "
        "system, or audit instant. This occurrence has no implicit business-date "
        "cast or unzoned formatting, so a long transaction cannot freeze it."
    ),
    "DOCUMENTATION_REFERENCE": (
        "Non-executable comment text; changing it would not alter runtime behavior."
    ),
    "EXPLICIT_JAKARTA_CONVERSION": (
        "The timestamptz is already converted explicitly to Asia/Jakarta."
    ),
    "EXPLICIT_UTC_CONVERSION": (
        "The timestamp is intentionally converted explicitly to UTC."
    ),
    "DATE_SERIES_CAST": (
        "The source is a date-domain series value, not a session-zone timestamptz."
    ),
    "DATE_TYPE_LITERAL": (
        "The source is already date-typed; session timezone cannot change it."
    ),
    "EXPLICIT_JAKARTA_DATE_CAST": (
        "The date cast is already preceded by an explicit Asia/Jakarta conversion."
    ),
    "TEXT_TO_DATE_PARSE": (
        "The cast parses canonical text directly to date and has no timezone input."
    ),
    "EXPLICIT_JAKARTA_STATEMENT_CLOCK": (
        "The command-stable clock is already converted explicitly to Asia/Jakarta."
    ),
    "STATEMENT_CLOCK": (
        "The source already advances between commands while remaining stable inside one command."
    ),
    "EXPLICIT_ZONE_TIMESTAMP_FORMAT": (
        "Timestamp formatting already follows an explicit timezone conversion."
    ),
}


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def function_structure(definition: str) -> dict[str, list[str]]:
    patterns = {
        "returns": r"(?m)^ RETURNS .+$",
        "language": r"(?m)^ LANGUAGE .+$",
        "security": r"(?m)^ SECURITY (?:DEFINER|INVOKER)$",
        "search_path": r"(?m)^ SET search_path TO .+$",
    }
    return {name: re.findall(pattern, definition) for name, pattern in patterns.items()}


def load_catalog(path: Path) -> dict[str, dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, dict[str, Any]] = {}
    for identity, definition, acl_text, owner in rows:
        if identity in result:
            raise AssertionError(f"duplicate function identity: {identity}")
        acl = None
        if acl_text is not None:
            if not (acl_text.startswith("{") and acl_text.endswith("}")):
                raise AssertionError(f"unexpected ACL form: {identity}")
            body = acl_text[1:-1]
            acl = [] if not body else sorted(body.split(","))
        result[identity] = {
            "definition": definition,
            "owner": owner,
            "acl": acl,
        }
    return result


def view_statements(dump: str) -> dict[str, str]:
    """Return the last pg_dump CREATE/CREATE OR REPLACE statement per view."""
    starts = list(re.finditer(
        r"(?m)^CREATE(?: OR REPLACE)? VIEW erp\.([a-zA-Z_][a-zA-Z0-9_]*)\b",
        dump,
    ))
    found: dict[str, str] = {}
    for start in starts:
        end = dump.find(";\n", start.start())
        if end < 0:
            raise AssertionError(f"unterminated view statement: {start.group(1)}")
        found[start.group(1)] = dump[start.start():end + 1]
    return found


def canonical_identity(item: dict[str, Any]) -> tuple[str, str]:
    object_type = item["object_type"]
    identity = item["object_identity"]
    if object_type == "RULE" and identity.endswith(" _RETURN"):
        return "VIEW", identity.removesuffix(" _RETURN")
    return object_type, identity


def selected_occurrences(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Resolve all OPEN hits and eliminate runtime transaction-clock metadata.

    The second group is deliberate class-level hardening: a created/updated
    timestamp can later become an ordering or timeout input.  Keeping ``now``
    in those writes would retain the same long-transaction failure mode even
    if today's direct business-date call sites were fixed.
    """
    rows = [
        item for item in manifest["occurrences"]
        if item["review_status"] == "OPEN"
        or (
            item["pattern"] == "NOW"
            and item["classification"] != "DOCUMENTATION_REFERENCE"
        )
    ]
    if len(rows) != 424:
        raise AssertionError(
            f"expected 424 reviewed temporal occurrences, found {len(rows)}"
        )
    ids = [item["occurrence_id"] for item in rows]
    if len(ids) != len(set(ids)):
        raise AssertionError("duplicate occurrence_id")
    return rows


def matching_left_paren(text: str, closing: int) -> int:
    depth = 0
    in_quote = False
    index = closing
    while index >= 0:
        char = text[index]
        if char == "'":
            if index > 0 and text[index - 1] == "'":
                index -= 2
                continue
            in_quote = not in_quote
        elif not in_quote:
            if char == ")":
                depth += 1
            elif char == "(":
                depth -= 1
                if depth == 0:
                    return index
        index -= 1
    raise AssertionError("unbalanced expression before ::date")


def left_expression_span(text: str, cast_start: int) -> tuple[int, int]:
    end = cast_start
    index = end - 1
    while index >= 0 and text[index].isspace():
        index -= 1
    if index < 0:
        raise AssertionError("missing expression before ::date")
    if text[index] == ")":
        start = matching_left_paren(text, index)
        # Include an immediately preceding function identifier, e.g. COALESCE(...).
        prefix_end = start
        prefix = start - 1
        while prefix >= 0 and text[prefix].isspace():
            prefix -= 1
        ident_end = prefix + 1
        while prefix >= 0 and (text[prefix].isalnum() or text[prefix] in "_."):
            prefix -= 1
        if ident_end > prefix + 1:
            start = prefix + 1
        return start, end
    start = index
    while start >= 0 and (text[start].isalnum() or text[start] in "_."):
        start -= 1
    start += 1
    if start == end:
        raise AssertionError("unsupported expression before ::date")
    return start, end


def find_argument_comma(text: str, opening: int) -> int:
    depth = 1
    in_quote = False
    index = opening + 1
    while index < len(text):
        char = text[index]
        if char == "'":
            if in_quote and index + 1 < len(text) and text[index + 1] == "'":
                index += 2
                continue
            in_quote = not in_quote
        elif not in_quote:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    raise AssertionError("to_char has no format argument")
            elif char == "," and depth == 1:
                return index
        index += 1
    raise AssertionError("unterminated to_char call")


def replace_casts(text: str, ordinals: set[int]) -> tuple[str, list[dict[str, Any]]]:
    matches = list(TOKEN_PATTERNS["CAST_DATE"].finditer(text))
    if not ordinals.issubset(set(range(1, len(matches) + 1))):
        raise AssertionError("CAST_DATE ordinal is outside source")
    edits: list[tuple[int, int, str, dict[str, Any]]] = []
    for ordinal in sorted(ordinals):
        match = matches[ordinal - 1]
        start, end = left_expression_span(text, match.start())
        expression = text[start:end].rstrip()
        replacement = (
            f"({expression} AT TIME ZONE 'Asia/Jakarta')::date"
        )
        edits.append((
            start,
            match.end(),
            replacement,
            {"pattern": "CAST_DATE", "ordinal": ordinal,
             "anchor": text[start:match.end()], "replacement": replacement},
        ))
    for start, end, replacement, _ in reversed(edits):
        text = text[:start] + replacement + text[end:]
    return text, [item[3] for item in edits]


def replace_to_char(text: str, ordinals: set[int]) -> tuple[str, list[dict[str, Any]]]:
    matches = list(TOKEN_PATTERNS["TO_CHAR"].finditer(text))
    if not ordinals.issubset(set(range(1, len(matches) + 1))):
        raise AssertionError("TO_CHAR ordinal is outside source")
    edits: list[tuple[int, int, str, dict[str, Any]]] = []
    for ordinal in sorted(ordinals):
        match = matches[ordinal - 1]
        opening = text.find("(", match.start(), match.end() + 1)
        comma = find_argument_comma(text, opening)
        argument = text[opening + 1:comma].strip()
        replacement = f"({argument} AT TIME ZONE 'Asia/Jakarta')"
        edits.append((
            opening + 1,
            comma,
            replacement,
            {"pattern": "TO_CHAR", "ordinal": ordinal,
             "anchor": text[opening + 1:comma], "replacement": replacement},
        ))
    for start, end, replacement, _ in reversed(edits):
        text = text[:start] + replacement + text[end:]
    return text, [item[3] for item in edits]


def replace_tokens(
    text: str,
    pattern_name: str,
    ordinals: set[int],
    replacement: str,
) -> tuple[str, list[dict[str, Any]]]:
    regex = TOKEN_PATTERNS[pattern_name]
    matches = list(regex.finditer(text))
    if not ordinals.issubset(set(range(1, len(matches) + 1))):
        raise AssertionError(f"{pattern_name} ordinal is outside source")
    edits = []
    for ordinal in sorted(ordinals):
        match = matches[ordinal - 1]
        edits.append({
            "pattern": pattern_name,
            "ordinal": ordinal,
            "anchor": match.group(0),
            "replacement": replacement,
            "start": match.start(),
            "end": match.end(),
        })
    for edit in reversed(edits):
        text = text[:edit["start"]] + replacement + text[edit["end"]:]
    for edit in edits:
        edit.pop("start")
        edit.pop("end")
    return text, edits


def transform_source(
    source: str,
    occurrences: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    wanted: dict[str, set[int]] = defaultdict(set)
    for item in occurrences:
        key = (
            item["object_identity"], item["pattern"], item["pattern_ordinal"]
        )
        if key in SAFE_EXCLUSIONS:
            continue
        wanted[item["pattern"]].add(item["pattern_ordinal"])

    edits: list[dict[str, Any]] = []
    # Structural wrappers run first; later token substitutions preserve ordinals.
    if wanted["CAST_DATE"]:
        source, made = replace_casts(source, wanted["CAST_DATE"])
        edits.extend(made)
    if wanted["TO_CHAR"]:
        source, made = replace_to_char(source, wanted["TO_CHAR"])
        edits.extend(made)

    replacements = {
        "CURRENT_DATE": BUSINESS_DATE,
        "CURRENT_TIMESTAMP": "statement_timestamp()",
        "NOW": "statement_timestamp()",
    }
    for pattern_name, replacement in replacements.items():
        if wanted[pattern_name]:
            source, made = replace_tokens(
                source, pattern_name, wanted[pattern_name], replacement
            )
            edits.extend(made)

    wall_ordinals = {
        item["pattern_ordinal"] for item in occurrences
        if item["pattern"] == "CLOCK_TIMESTAMP"
        and item["classification"] == "CURRENT_VIEW_WALL_CLOCK"
    }
    if wall_ordinals:
        source, made = replace_tokens(
            source, "CLOCK_TIMESTAMP", wall_ordinals, "statement_timestamp()"
        )
        edits.extend(made)
    return source, edits


def table_default(item: dict[str, Any]) -> dict[str, str]:
    line = item["line"].strip()
    match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s+", line)
    if match is None:
        raise AssertionError(f"cannot read default column: {line}")
    column = match.group(1)
    if item["pattern"] == "CURRENT_DATE":
        before = "CURRENT_DATE"
        after = BUSINESS_DATE
    elif item["classification"] == "ELAPSED_TIME_THRESHOLD":
        before = "(now() + '30 days'::interval)"
        after = "(statement_timestamp() + '30 days'::interval)"
    else:
        before = "now()"
        after = "statement_timestamp()"
    return {"column": column, "before": before, "after": after}


def run(args: argparse.Namespace) -> dict[str, Any]:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    catalog = load_catalog(args.catalog)
    dump = args.schema_dump.read_text(encoding="utf-8")
    views = view_statements(dump)
    selected_rows = selected_occurrences(manifest)
    selected_ids = {item["occurrence_id"] for item in selected_rows}

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in selected_rows:
        grouped[canonical_identity(item)].append(item)

    objects: list[dict[str, Any]] = []
    dispositions: list[dict[str, Any]] = []
    transformed_functions: list[list[Any]] = []
    transformed_views: list[list[Any]] = []
    defaults: list[dict[str, Any]] = []

    # The evidence ledger covers the whole lossless source inventory, not only
    # rows that require an AC edit. This prevents an inherited CLOSED label from
    # silently falling outside the successor review boundary.
    for item in manifest["occurrences"]:
        if item["occurrence_id"] in selected_ids:
            continue
        classification = item["classification"]
        if classification not in KEEP_ACTIONS:
            raise AssertionError(
                f"unreviewed retained classification: {classification}"
            )
        object_type, identity = canonical_identity(item)
        dispositions.append({
            "occurrence_id": item["occurrence_id"],
            "object_type": object_type,
            "object_identity": identity,
            "pattern": item["pattern"],
            "pattern_ordinal": item["pattern_ordinal"],
            "classification": classification,
            "incoming_review_status": item["review_status"],
            "decision": "KEEP",
            "action": KEEP_ACTIONS[classification],
            "rationale": KEEP_RATIONALES[classification],
        })

    for (object_type, identity), occurrences in sorted(grouped.items()):
        exclusions = [
            item for item in occurrences
            if (item["object_identity"], item["pattern"], item["pattern_ordinal"])
            in SAFE_EXCLUSIONS
        ]
        changes = [item for item in occurrences if item not in exclusions]
        for item in occurrences:
            exclusion = SAFE_EXCLUSIONS.get((
                item["object_identity"], item["pattern"], item["pattern_ordinal"]
            ))
            if exclusion:
                action = exclusion[0]
            elif (
                item["pattern"] == "CLOCK_TIMESTAMP"
                and item["classification"] == "WALL_CLOCK_IDENTIFIER_FORMAT"
            ):
                action = "EXPLICIT_JAKARTA_WALL_CLOCK_FORMAT"
            else:
                action = {
                    "CAST_DATE": "EXPLICIT_JAKARTA_DATE_CAST",
                    "TO_CHAR": "EXPLICIT_JAKARTA_FORMAT",
                    "CURRENT_DATE": "JAKARTA_STATEMENT_DATE",
                    "CURRENT_TIMESTAMP": "STATEMENT_TIMESTAMP",
                    "NOW": "STATEMENT_TIMESTAMP",
                    "CLOCK_TIMESTAMP": "STATEMENT_STABLE_VIEW_CLOCK",
                }[item["pattern"]]
            dispositions.append({
                "occurrence_id": item["occurrence_id"],
                "object_type": object_type,
                "object_identity": identity,
                "pattern": item["pattern"],
                "pattern_ordinal": item["pattern_ordinal"],
                "classification": item["classification"],
                "incoming_review_status": item["review_status"],
                "decision": "EXCLUDE" if exclusion else "CHANGE",
                "action": action,
                "rationale": exclusion[1] if exclusion else (
                    "Retain wall-clock entropy for the identifier; the paired "
                    "TO_CHAR argument is made explicitly Asia/Jakarta."
                    if (
                        item["pattern"] == "CLOCK_TIMESTAMP"
                        and item["classification"] == "WALL_CLOCK_IDENTIFIER_FORMAT"
                    )
                    else "Use one command-stable clock that advances between commands; "
                    "derive business dates/formats explicitly in Asia/Jakarta."
                ),
            })

        if object_type == "FUNCTION":
            source = catalog[identity]["definition"]
            transformed, edits = transform_source(source, occurrences)
            if changes and transformed == source:
                raise AssertionError(f"function was not transformed: {identity}")
            before_structure = function_structure(source)
            after_structure = function_structure(transformed)
            if before_structure != after_structure:
                raise AssertionError(f"function structure changed: {identity}")
            objects.append({
                "object_type": object_type,
                "object_identity": identity,
                "before_sha256": digest_text(source),
                "after_sha256": digest_text(transformed),
                "owner": catalog[identity]["owner"],
                "acl": catalog[identity]["acl"],
                "structural_contract": before_structure,
                "structural_contract_preserved": True,
                "changed_occurrences": len(changes),
                "excluded_occurrences": len(exclusions),
                "edits": edits,
            })
            if changes:
                transformed_functions.append([
                    identity, source, transformed, catalog[identity]["acl"],
                    catalog[identity]["owner"],
                ])
        elif object_type == "VIEW":
            source = views[identity]
            transformed, edits = transform_source(source, occurrences)
            if transformed == source:
                raise AssertionError(f"view was not transformed: {identity}")
            objects.append({
                "object_type": object_type,
                "object_identity": f"erp.{identity}",
                "before_sha256": digest_text(source),
                "after_sha256": digest_text(transformed),
                "changed_occurrences": len(changes),
                "excluded_occurrences": 0,
                "edits": edits,
            })
            transformed_views.append([identity, source, transformed])
        elif object_type == "TABLE":
            for occurrence in occurrences:
                default = table_default(occurrence)
                default.update(table=identity, changed_occurrences=1)
                defaults.append(default)
                objects.append({
                    "object_type": "TABLE_DEFAULT",
                    "object_identity": f"erp.{identity}.{default['column']}",
                    "before_sha256": digest_text(default["before"]),
                    "after_sha256": digest_text(default["after"]),
                    "changed_occurrences": 1,
                    "excluded_occurrences": 0,
                    "edits": [{
                        "pattern": occurrence["pattern"],
                        "ordinal": occurrence["pattern_ordinal"],
                        "anchor": default["before"],
                        "replacement": default["after"],
                    }],
                })
        else:
            raise AssertionError(f"unexpected object type: {object_type}")

    decisions = Counter(item["decision"] for item in dispositions)
    types = Counter(item["object_type"] for item in objects)
    if decisions != {"CHANGE": 422, "KEEP": 285, "EXCLUDE": 2}:
        raise AssertionError(f"unexpected disposition counts: {decisions}")
    if types != {"FUNCTION": 117, "VIEW": 13, "TABLE_DEFAULT": 144}:
        # The two exclusion-only functions are recorded but not transformed.
        raise AssertionError(f"unexpected object counts: {types}")
    if len(transformed_functions) != 115:
        raise AssertionError("expected 115 transformed functions")

    result = {
        "format": "CP6_V2620AC_TEMPORAL_DISPOSITION_V1",
        "source": {
            "catalog_sha256": hashlib.sha256(args.catalog.read_bytes()).hexdigest(),
            "schema_dump_sha256": hashlib.sha256(args.schema_dump.read_bytes()).hexdigest(),
            "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        },
        "contract": {
            "business_timezone": "Asia/Jakarta",
            "command_clock": "statement_timestamp()",
            "transaction_metadata_clock": "statement_timestamp(); no runtime now() remains",
            "absolute_audit_clock": "clock_timestamp() remains unchanged outside identifiers/current views",
            "production_go": False,
        },
        "summary": {
            "source_inventory_occurrences": len(manifest["occurrences"]),
            "incoming_open_occurrences": 208,
            "additional_transaction_clock_hardening_occurrences": 216,
            "reviewed_occurrences": len(dispositions),
            "retained_occurrences": decisions["KEEP"],
            "change_occurrences": decisions["CHANGE"],
            "source_edits": sum(len(item["edits"]) for item in objects),
            "paired_occurrences_covered_by_format_edits": 3,
            "explicit_exclusions": decisions["EXCLUDE"],
            "transformed_functions": len(transformed_functions),
            "transformed_views": len(transformed_views),
            "transformed_table_defaults": len(defaults),
            "unresolved_occurrences": 0,
            "completeness_gate": "PASS_SPEC",
        },
        "dispositions": sorted(dispositions, key=lambda item: item["occurrence_id"]),
        "objects": objects,
        "generated_payload": {
            "functions": transformed_functions,
            "views": transformed_views,
            "table_defaults": defaults,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if args.evidence_output is not None:
        evidence = {key: value for key, value in result.items()
                    if key != "generated_payload"}
        args.evidence_output.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_output.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.transformed_catalog is not None:
        transformed_by_identity = {
            row[0]: row[2] for row in transformed_functions
        }
        catalog_rows = json.loads(args.catalog.read_text(encoding="utf-8"))
        for row in catalog_rows:
            if row[0] in transformed_by_identity:
                row[1] = transformed_by_identity[row[0]]
        args.transformed_catalog.parent.mkdir(parents=True, exist_ok=True)
        args.transformed_catalog.write_text(
            json.dumps(catalog_rows, indent=2) + "\n", encoding="utf-8"
        )
    if args.transformed_schema is not None:
        transformed_dump = dump
        for _, before, after in transformed_views:
            if transformed_dump.count(before) != 1:
                raise AssertionError("view source is not unique in schema dump")
            transformed_dump = transformed_dump.replace(before, after, 1)
        for item in defaults:
            table_start = transformed_dump.find(f"CREATE TABLE erp.{item['table']} (")
            if table_start < 0:
                raise AssertionError(f"table not found in dump: {item['table']}")
            table_end = transformed_dump.find("\n);", table_start)
            block = transformed_dump[table_start:table_end]
            pattern = re.compile(
                rf"(?m)^(\s*{re.escape(item['column'])}\s+.*?\bDEFAULT\s+)"
                + re.escape(item["before"])
            )
            changed, count = pattern.subn(
                lambda match: match.group(1) + item["after"], block, count=1
            )
            if count != 1:
                raise AssertionError(
                    f"default source is not unique: {item['table']}.{item['column']}"
                )
            transformed_dump = (
                transformed_dump[:table_start] + changed
                + transformed_dump[table_end:]
            )
        args.transformed_schema.parent.mkdir(parents=True, exist_ok=True)
        args.transformed_schema.write_text(transformed_dump, encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--schema-dump", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence-output", type=Path)
    parser.add_argument("--transformed-catalog", type=Path)
    parser.add_argument("--transformed-schema", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    outcome = run(parse_args())
    print(json.dumps(outcome["summary"], sort_keys=True))
