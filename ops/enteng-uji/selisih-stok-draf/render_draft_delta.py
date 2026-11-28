"""Build the draft reservation receipt correction for the qualified Uji release."""
from argparse import ArgumentParser
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'piutang-laundry'))
from guarded_business_release import render


def migration(profile):
    return render(
        profile=profile,
        prior='enteng_uji_impor_gudang_bahan',
        name='enteng_uji_selisih_stok_draf',
        previous_source='c036b16c84d1b489e843ba01a8e80cde4e3c0f79b55fa0b2b1b8bd74686c4de9',
        migrations=165,
        profiles=13,
        counts_delta={},
        statements=(HERE / 'selisih-stok.sql').read_text(encoding='utf-8'),
    )


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('profile', help='Active, verified Enteng Uji profile')
    print(migration(parser.parse_args().profile), end='')
