"""Extract ONLY metadata from a hash-pinned private actual evidence archive."""
import argparse
from hashlib import sha256
from pathlib import Path
import json
import zipfile
import census


def pointer(document, path):
    census.require(path.startswith('/'), 'CENSUS_JSON_POINTER_REQUIRED')
    for part in path[1:].split('/'):
        part = part.replace('~1', '/').replace('~0', '~')
        census.require(type(document) is dict and part in document, 'CENSUS_JSON_POINTER_MISSING:' + path)
        document = document[part]
    return document


def read_archive(path, *, expected_bytes, expected_sha256, member):
    raw = Path(path).read_bytes()
    census.require(len(raw) == expected_bytes and sha256(raw).hexdigest() == expected_sha256,
                   'CENSUS_EXACT_PRIVATE_ARCHIVE_REQUIRED')
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        census.require(len(names) == len(set(names)), 'CENSUS_DUPLICATE_ARCHIVE_MEMBER')
        census.require(member in names, 'CENSUS_EXACT_REPORT_MEMBER_REQUIRED')
        data = archive.read(member)
    return json.loads(data, object_pairs_hook=census.unique_pairs), dict(name=member, bytes=len(data), sha256=sha256(data).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--archive-bytes', type=int, required=True)
    parser.add_argument('--archive-sha256', required=True)
    parser.add_argument('--member', required=True)
    parser.add_argument('--catalogue-pointer', required=True)
    parser.add_argument('--comparison-pointer', required=True)
    parser.add_argument('--raw-authority-pointer')
    parser.add_argument('--supplement')
    parser.add_argument('--expected-contexts', default=str(census.HERE / 'EXPECTED_CONTEXTS.json'))
    parser.add_argument('--source-head', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--summary', required=True)
    args = parser.parse_args()
    census.require(len(args.source_head) == 40 and all(c in '0123456789abcdef' for c in args.source_head),
                   'CENSUS_EXACT_SOURCE_HEAD_REQUIRED')
    census.require(args.run_id.isdecimal(), 'CENSUS_EXACT_RUN_ID_REQUIRED')
    document, report_pin = read_archive(args.archive, expected_bytes=args.archive_bytes,
        expected_sha256=args.archive_sha256, member=args.member)
    catalog = pointer(document, args.catalogue_pointer)
    comparison = pointer(document, args.comparison_pointer)
    census.validate_catalog(comparison)
    census.require(catalog == comparison, 'CENSUS_ACTUAL_COMPARISON_CATALOGUE_DRIFT')
    raw = pointer(document, args.raw_authority_pointer) if args.raw_authority_pointer else None
    profile = census.read_json(args.expected_contexts)
    supplement = census.read_json(args.supplement) if args.supplement else None
    provenance = dict(source_head=args.source_head, run_id=args.run_id,
        archive=dict(name=Path(args.archive).name, bytes=args.archive_bytes, sha256=args.archive_sha256),
        report=report_pin, catalogue_pointer=args.catalogue_pointer, comparison_pointer=args.comparison_pointer,
        equal_actual_observations=2, source_identity_is_caller_pinned=True,
        actual_business_execution_inferred=False)
    answer = census.analyze(catalog, expected_contexts=profile['names'], raw_authority=raw,
                            supplement=supplement, provenance=provenance)
    result = census.summary(answer)
    Path(args.output).write_text(json.dumps(answer, indent=2, ensure_ascii=False) + '\n')
    Path(args.summary).write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({key: result[key] for key in ('classification', 'contexts',
        'function_candidates', 'relation_candidates', 'dynamic_sql_candidates',
        'runtime_entry', 'actual_Native_credit', 'production_go')}, sort_keys=True))


if __name__ == '__main__':
    main()
