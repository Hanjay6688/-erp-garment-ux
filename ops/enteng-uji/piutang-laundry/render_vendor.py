"""Print a reviewed Laundry migration for the verified active Enteng Uji profile."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from guarded_business_release import render

HERE=Path(__file__).resolve().parent
def migration(profile, *, failed_wash=False):
    manifest_name='failed-wash-input.json' if failed_wash else 'vendor-release-input.json'
    source_name='failed-wash-statements.sql' if failed_wash else 'vendor-receivable-statements.sql'
    manifest=json.loads((HERE/manifest_name).read_text())
    checksum=manifest.pop('statements_sha256')
    source=(HERE/source_name).read_text()
    if sha256(source.encode()).hexdigest()!=checksum:
        raise ValueError('Laundry statements do not match the qualified release')
    return render(profile=profile,statements=source,**manifest)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile')
    parser.add_argument('--failed-wash',action='store_true',help='Render deferred pricing for failed washes')
    args=parser.parse_args()
    print(migration(args.profile,failed_wash=args.failed_wash),end='')
