"""Build the supplier receipt payment status correction for Enteng Uji."""
from argparse import ArgumentParser
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'piutang-laundry'))
from guarded_business_release import render


def migration(profile):
    return render(
        profile=profile,
        prior='enteng_uji_selisih_stok_draf',
        name='enteng_uji_status_penerimaan_belum_ditagih',
        previous_source='08f7f4d5977186ded0e7d19e2129ffe41f04114bf2ec9ef847405a69298b8008',
        migrations=166,
        profiles=14,
        counts_delta={'functions': 2, 'triggers': 1},
        statements=(HERE / 'status-pembayaran.sql').read_text(encoding='utf-8'),
    )


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('profile', help='Active, verified Enteng Uji profile')
    print(migration(parser.parse_args().profile), end='')
