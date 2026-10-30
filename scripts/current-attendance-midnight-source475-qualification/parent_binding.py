"""Exact public candidate/source; future successful Originals remain unbound."""
from midnight_common import ROOT, document, regular, exact

HEAD = '3c0c5defe55e48cf6f221c868594dd6676d17170'
TREE = 'ca20c918201b455ad09df489829b83b9e6afea95'
RUN = '40983410165'
JOB = '123828634300'
WORKFLOW = 'CP7 A S03 lawful fixture successor Native11 then Reader3'
SOURCE = 'scripts/current-s03-lawful-fixture-successor-qualification/SOURCE.json'
SOURCE_PIN = dict(bytes=106705, sha256='ba59dee4ae71c62df2b2e35c558cb23a7c66254a974c554cc3d17d63b936c555')
COUNT = 475


def source(root=ROOT):
    raw = regular(root, SOURCE).read_bytes()
    exact(raw, SOURCE_PIN)
    current = document(raw)
    if (current.get('contract') != 'cp7.s03.lawful-fixture-successor-native14.v1'
            or len(current.get('files', {})) != COUNT):
        raise ValueError('MIDNIGHT_EXACT_CURRENT_SOURCE475_CONTRACT_REQUIRED')
    return raw, current['files']


def checked(parent, backend, root=ROOT):
    # This is reached only after the unchanged NULL-first gate. It grants no
    # success on its own: six real raw/gzip Originals are still mandatory.
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
