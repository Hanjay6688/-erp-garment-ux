"""A review-only projection for the disposable regression fixture."""
from hashlib import sha256
from pathlib import Path
import argparse
import json
import re


NATIVE = 'erp.compute_non_po_product_hpp_targets_v2620f(uuid)'
CREDIT = 'cp7_credit.initial_hpp_targets_v1(uuid,uuid,jsonb,boolean)'


def replace_once(source, before, after):
    if source.count(before) != 1 or after in source:
        raise ValueError('Expected exactly one pinned source expression')
    return source.replace(before, after, 1)


def prepare(input_path, output_path):
    value = json.loads(input_path.read_bytes())
    functions = value['candidate_money_definitions']
    originals = {sig: functions[sig] for sig in (NATIVE, CREDIT)}
    native = re.findall(r'round\(greatest\(s\.value\+ls\.value[^\n]+?,0\),2\)::numeric cogs', originals[NATIVE])
    if len(native) != 1:
        raise ValueError('Native rounded COGS source changed')
    previous = native[0]
    raw_cogs = previous.removeprefix('round(').removesuffix(',2)::numeric cogs')
    functions[NATIVE] = replace_once(originals[NATIVE], previous,
        f'(round(o.value+{raw_cogs},2)-round(o.value,2))::numeric cogs')
    previous = 'round(greatest(cogs,0),2)::numeric cogs from raw_values'
    functions[CREDIT] = replace_once(originals[CREDIT], previous,
        "(case when p_po is null then round(fg+greatest(cogs,0),2)-round(fg,2) "
        "else round(greatest(cogs,0),2) end)::numeric cogs from raw_values")
    value['probe_variant'] = {
        'scope': 'REVIEW_ONLY_PROPOSED_CUMULATIVE_ROUNDING',
        'original_input_sha256': sha256(input_path.read_bytes()).hexdigest(),
        'changes': {sig: {'before_sha256': sha256(originals[sig].encode()).hexdigest(),
                          'after_sha256': sha256(functions[sig].encode()).hexdigest()}
                    for sig in originals},
    }
    with output_path.open('x') as f:
        json.dump(value, f, sort_keys=True)
        f.write('\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    prepare(args.input, args.output)
