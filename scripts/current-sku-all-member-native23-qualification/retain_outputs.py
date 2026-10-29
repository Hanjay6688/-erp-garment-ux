"""Retain exact relative-CWD cost census bytes; no report/result rewriting."""
from pathlib import Path
from hashlib import sha256
import argparse
import json


def retain(workspace):
    workspace = Path(workspace).resolve()
    destination = workspace / 'auditor/cp6-proof/t3'
    destination.mkdir(parents=True, exist_ok=True)
    retained = []
    for checkout in ('writer', 'base', 'auditor'):
        folder = workspace / checkout / 'cp6-proof/t3'
        for source in sorted(folder.glob('SKU_COST_*.json')):
            if source.name == 'SKU_COST_ARTIFACT_COPY_RECEIPT.json':
                continue
            value = source.read_bytes()
            target = destination / source.name
            if target.exists() and target.read_bytes() != value:
                raise ValueError('SKU23_COST_ARTIFACT_NAME_COLLISION:' + source.name)
            if target != source:
                target.write_bytes(value)
            assert target.read_bytes() == value
            retained.append(dict(source=str(source.relative_to(workspace)),
                artifact_path=str(target.relative_to(workspace)), bytes=len(value), sha256=sha256(value).hexdigest(),
                byte_exact=True))
    proof = dict(status='EXACT_GENERATED_COST_OUTPUTS_RETAINED', files=retained,
        runtime_working_directory='writer', source_result_fields_rewritten=False,
        output_absence_is_not_PASS=True, actual_new_case_credit=0)
    (destination / 'SKU_COST_ARTIFACT_COPY_RECEIPT.json').write_text(json.dumps(proof, indent=2)+'\n')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True)
    args = parser.parse_args()
    print(json.dumps(retain(args.workspace), sort_keys=True))
