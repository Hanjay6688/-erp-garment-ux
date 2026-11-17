"""Read the minimized receipt verified from the accepted originals before publication."""
from hashlib import sha256
import json
from pathlib import Path
import sys

from .mode import PRODUCT as PRODUCT_HEAD, PRODUCT_TREE


PRODUCT = dict(head=PRODUCT_HEAD, tree=PRODUCT_TREE)
EVIDENCE_PATH = 'qualification/p21/PREVIOUS_PROOFS.json'
EVIDENCE = Path(__file__).with_name('PREVIOUS_PROOFS.json')
EVIDENCE_DIGEST = 'e904768e63ebc3331f6e4ac7bfa3508e03e2a42a9d1dd762874ada669080b619'


def checked(raw):
    if sha256(raw).hexdigest() != EVIDENCE_DIGEST:
        raise ValueError('P21_PUBLIC_PREVIOUS_PROOFS_CHANGED')
    data = json.loads(raw)
    p20 = data['p20']
    p21 = data['p21']
    access = p21['prior_e14_and_compute_role']
    if not (p20['status'] == 'VERIFIED_EXISTING_EVIDENCE' and p20['candidate'] == PRODUCT
            and len(set(p20['accepted_p20_cases'])) == 13 and p20['actual_P20_cases_rerun'] == 0
            and p21['status'] == 'PASS' and p21['previous_full_restore_verified'] is True
            and p21['switch_roll_saves_rerun'] == 0 and p21['reuse_p20_cases'] == 13
            and access['status'] == 'PASS' and access['real_gotrue'] is True
            and access['full_restore'] is access['cp7_capture_writer_denied'] is True
            and access['e14_cases_rerun'] == 0):
        raise ValueError('P21_PUBLIC_PREVIOUS_PROOFS_INCOMPLETE')
    return data


def admitted(raw):
    return checked(raw)['p20']


def write(path, receipt):
    with Path(path).open('x', encoding='ascii') as output:
        json.dump(receipt, output, indent=2, sort_keys=True)
        output.write('\n')


if __name__ == '__main__':
    write(sys.argv[1], admitted(EVIDENCE.read_bytes()))
