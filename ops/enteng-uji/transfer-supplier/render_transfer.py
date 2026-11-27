"""Print the supplier-transfer migration for a verified Enteng Uji Global profile."""
from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'piutang-laundry'))
from guarded_business_release import render


def migration(profile):
    manifest = json.loads((HERE / 'supplier-transfer-input.json').read_text())
    checksum = manifest.pop('statements_sha256')
    statements = (HERE / 'supplier-transfer-statements.sql').read_text()
    if sha256(statements.encode()).hexdigest() != checksum:
        raise ValueError('Supplier transfer statements differ from the qualified source')
    return render(profile=profile, statements=statements, **manifest)


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('profile')
    print(migration(parser.parse_args().profile), end='')
