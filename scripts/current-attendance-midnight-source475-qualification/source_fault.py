"""Exact final24b restoration helper; local source controls only."""
from pathlib import Path
from hashlib import sha256
import contextlib

def snapshot(path):
    """Actual regular bytes/modes; never follow a leaf or descendant link."""
    if path.is_symlink():raise AssertionError('S03_LAWFUL_RESTORE_STILL_A_LINK:'+str(path))
    paths=[path]if path.is_file()else[path,*sorted(path.rglob('*'))]
    result={}
    for entry in paths:
        if entry.is_symlink():raise AssertionError('S03_LAWFUL_RESTORE_DESCENDANT_LINK:'+str(entry))
        name='.'if entry==path else str(entry.relative_to(path))
        row=dict(mode=entry.stat().st_mode&0o7777,kind='file'if entry.is_file()else'directory')
        if entry.is_file():
            raw=entry.read_bytes();row.update(bytes=len(raw),sha256=sha256(raw).hexdigest())
        result[name]=row
    return result


@contextlib.contextmanager
def source_link_fault(target,held):
    """Restore even when unlink/rename/symlink construction or caller raises."""
    before=snapshot(target);directory=target.is_dir();saved=None if directory else target.read_bytes()
    if held.exists()or held.is_symlink():raise AssertionError('S03_LAWFUL_HELD_PATH_EXISTS')
    if not directory:held.write_bytes(saved)
    try:
        # Held originals survive an unexpected restore error; automatic temp
        # cleanup must never erase the sole moved source.
        if directory:target.rename(held)
        else:target.unlink()
        target.symlink_to(held,target_is_directory=directory)
        if not target.is_symlink():raise AssertionError('S03_LAWFUL_LINK_FAULT_NOT_MATERIALIZED')
        yield before
    finally:
        if target.is_symlink():target.unlink()
        if target.exists():
            if snapshot(target)!=before:raise AssertionError('S03_LAWFUL_UNEXPECTED_EXISTING_RESTORE_TARGET')
        elif directory:held.rename(target)
        else:
            target.write_bytes(saved);target.chmod(before['.']['mode'])
        if snapshot(target)!=before:raise AssertionError('S03_LAWFUL_SOURCE_BYTES_MODES_NOT_RESTORED')

