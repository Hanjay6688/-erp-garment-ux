"""The qualified product owning installer, shared by transport entries only."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import cp7_full_owning_install as product
import cp7_ow04_probe as core

STATE=None


def install(cur,report):
    global STATE
    STATE=product.install(cur)
    core.STATE=STATE['credit']
    report['predecessor_installation']=STATE['predecessor_installation']
    report['full_owning_source_manifest']=STATE['sources']
    return STATE


def verify(cur):
    if STATE is None:
        raise ValueError('OW04_TRANSPORT_COMPLETE_OWNING_INSTALLATION_REQUIRED')
    return product.verify(cur,STATE)


def uninstall(cur,state):
    if state is not STATE:
        raise ValueError('OW04_TRANSPORT_OWNING_INSTALLATION_CHANGED')
    # Test cases use copied databases. The installation database must still be
    # exactly unused, including all private row hashes, before removing it.
    product.rollback_preuse(cur,state)
