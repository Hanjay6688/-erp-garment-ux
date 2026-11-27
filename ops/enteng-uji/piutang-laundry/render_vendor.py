"""Print the reviewed vendor receivable migration for the verified active Uji profile."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from guarded_business_release import render

HERE=Path(__file__).resolve().parent
def migration(profile):
    manifest=json.loads((HERE/'vendor-release-input.json').read_text())
    checksum=manifest.pop('statements_sha256')
    source=(HERE/'vendor-receivable-statements.sql').read_text()
    if sha256(source.encode()).hexdigest()!=checksum:
        raise ValueError('Vendor receivable statements do not match the qualified release')
    return render(profile=profile,statements=source,**manifest)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile')
    print(migration(parser.parse_args().profile),end='')
