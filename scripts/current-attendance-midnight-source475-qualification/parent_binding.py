"""Exact public qualified14/source and Root's immutable six-Original binding."""
from midnight_common import ROOT, NS, canonical, document, regular, exact

HEAD = '3c0c5defe55e48cf6f221c868594dd6676d17170'
TREE = 'ca20c918201b455ad09df489829b83b9e6afea95'
RUN = '40983410165'
JOB = '123828634300'
WORKFLOW = 'CP7 A S03 lawful fixture successor Native11 then Reader3'
SOURCE = 'scripts/current-s03-lawful-fixture-successor-qualification/SOURCE.json'
SOURCE_PIN = dict(bytes=106705, sha256='ba59dee4ae71c62df2b2e35c558cb23a7c66254a974c554cc3d17d63b936c555')
COUNT = 475
ROOT_RECEIPT = NS + 'ROOT_QUALIFIED_PARENT14.json'
ROOT_RECEIPT_PIN = dict(bytes=6012, sha256='9f0270cf44291ae7cd4b16bddf3fc258e9faf8cdac5a4ab619b3044f81ac66c8')
PRODUCT_SOURCES_SHA256 = '67567ce692a513954235c93f0659ed0d6297a62002a69ab67d62d26c57c1dc8b'
RAW_NAMES = dict(strict11='CP7_S03_ATTENDANCE_CHOICE_NATIVE11_CASES.json',
    reader3='CP7_S03_ATTENDANCE_CHOICE_READER_NATIVE3_CASES.json',
    outer14='CP7_S03_ATTENDANCE_CHOICE_NATIVE14.json', package='T3_PACKAGE_INSTALL.json',
    files='T3_PACKAGE_FILES_INSTALL.json', drill='T3_BACKUP_RESTORE_DRILL.json')


def root_receipt(root=ROOT):
    raw = regular(root, ROOT_RECEIPT).read_bytes()
    exact(raw, ROOT_RECEIPT_PIN)
    receipt = document(raw)
    if (receipt['head'] != HEAD or receipt['tree'] != TREE
            or str(receipt['run_id']) != RUN or str(receipt['job_id']) != JOB
            or receipt['status'] != 'QUALIFIED_NARROW_ACTUAL_NATIVE11_THEN3_FULL_RESTORE_ALL5'
            or receipt['actual_Native_cases'] != 14 or receipt['all14_PASS'] is not True):
        raise ValueError('MIDNIGHT_EXACT_ROOT_QUALIFIED14_RECEIPT_REQUIRED')
    return receipt


def original_descriptors(root=ROOT):
    rows = {row['path']: row for row in root_receipt(root)['accepted_six_originals']}
    if set(rows) != set(RAW_NAMES.values()):
        raise ValueError('MIDNIGHT_EXACT_ROOT_SIX_RAW_NAMES_REQUIRED')
    return {key: dict(path=NS + 'accepted-parent14/' + name, encoding='raw',
        stored={field: rows[name][field] for field in ('bytes', 'sha256')},
        raw={field: rows[name][field] for field in ('bytes', 'sha256')})
        for key, name in RAW_NAMES.items()}


def source(root=ROOT):
    raw = regular(root, SOURCE).read_bytes()
    exact(raw, SOURCE_PIN)
    current = document(raw)
    if (current.get('contract') != 'cp7.s03.lawful-fixture-successor-native14.v1'
            or len(current.get('files', {})) != COUNT):
        raise ValueError('MIDNIGHT_EXACT_CURRENT_SOURCE475_CONTRACT_REQUIRED')
    return raw, current['files']


def checked(parent, backend, root=ROOT):
    # Metadata alone never admits an Original or opens an ERP execution route.
    if (parent.get('head') != HEAD or parent.get('tree') != TREE
            or parent.get('run_id') != RUN or parent.get('job_id') != JOB
            or parent.get('workflow') != WORKFLOW
            or backend.get('head') != HEAD or backend.get('tree') != TREE):
        raise ValueError('MIDNIGHT_EXACT_PUBLIC3C0_RUN40983410165_JOB123828634300_REQUIRED')
    expected = dict(path=SOURCE, **SOURCE_PIN)
    if backend.get('source_manifest') != expected:
        raise ValueError('MIDNIGHT_CURRENT_SOURCE475_PIN_REQUIRED_NOT_HISTORICAL425')
    _, files = source(root)
    if backend.get('files') != files:
        raise ValueError('MIDNIGHT_COMPLETE_CURRENT_SOURCE475_MAP_REQUIRED')
    if (canonical(parent.get('originals')) != canonical(original_descriptors(root))
            or backend.get('product_sources_sha256') != PRODUCT_SOURCES_SHA256):
        raise ValueError('MIDNIGHT_EXACT_ROOT_QUALIFIED14_SIX_RAW_AND_PRODUCT_SOURCES_REQUIRED')
    return files


def current_declaration(root, cfg):
    raw, files = source(root)
    if cfg.get('backend_binding') is not None:
        # Require both bindings; an accidental half-bound config never falls
        # back to historical source. gate.selected checks raw-pin classes too.
        import midnight_gate
        parent, backend = midnight_gate.selected(cfg)
        checked(parent, backend, root)
    elif cfg.get('accepted_parent14') is not None:
        raise ValueError('MIDNIGHT_CLOSED_BINDINGS_MUST_BOTH_BE_NULL')
    # Pin the parent declaration itself as well as every one of its475 members.
    return HEAD, TREE, dict(files, **{SOURCE: SOURCE_PIN})
