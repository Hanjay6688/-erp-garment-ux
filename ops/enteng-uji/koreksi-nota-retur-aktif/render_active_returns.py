"""Render the owned cash-and-return note correction for the reviewed Enteng Uji parent."""
from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'piutang-laundry'))
from guarded_business_release import render


def migration(profile):
    manifest = json.loads((HERE / 'manifest.json').read_text())
    expected = manifest.pop('statements_sha256')
    code = (HERE / 'retur-aktif.sql').read_text()
    if sha256(code.encode()).hexdigest() != expected:
        raise ValueError('The active-return SQL differs from the qualified statements')
    return render(profile=profile, statements=code, **manifest)


if __name__ == '__main__':
    cli = ArgumentParser(description=__doc__)
    cli.add_argument('profile')
    print(migration(cli.parse_args().profile), end='')
