"""Run the reviewed single-batch reversal and pending Laundry workflow in Enteng Uji."""

from hashlib import sha256

from cp7_enteng_managed_identity import require
from cp7_enteng_managed_wip_batch import install as install_batch


MIGRATION_NAME = 'enteng_uji_cp7_managed_wip_laundry'
REVIEWED_SOURCE_COMMIT = '0a0b4f6f8e091507c9f9e1f96b1ef97036d9832a'
PENDING_SOURCE_PINS = {
    '__init__.py':'f01eabfe6608d2f1c4cda0b81ecdee51f0fb5201746e3f6f3725bb23516cf701',
    'columns.sql':'5f0d7088a4ea953d2b16555c154b6483db4e50b13f4b8b2794de51d4618027e0',
}
DYEING_SOURCE_PINS = {
    '__init__.py':'9683597c308e483a9bc0b8f6b0721283cb720a025e8462aea656178e012f1f77',
    'master.sql':'3b7c57bfcce5fd02358ca3df94389976be373bd039ea3417bba45c913b45e62b',
}


def install(cur,batch,pending,dyeing):
    require(cur.execute("select current_user,session_user,current_setting('is_superuser')").fetchone()
            ==('postgres','postgres','off'),'Managed workflow installer requires the project role')
    for module,pins in ((pending,PENDING_SOURCE_PINS),(dyeing,DYEING_SOURCE_PINS)):
        for name,wanted in pins.items():
            require(sha256((module.HERE/name).read_bytes()).hexdigest()==wanted,
                    'Reviewed Laundry source changed: '+module.__name__+'/'+name)
    cur.execute('select cp7_global_release_guard.enter_release(),cp7_credit.assert_source_native_trigger_census_v1()')
    laundry = pending.install(cur)
    recipes = dyeing.install(cur)
    wip = install_batch(cur,batch)
    cur.execute('select cp7_global_release_guard.assert_ddl_fence(),cp7_credit.assert_source_native_trigger_census_v1()')
    return dict(source_commit=REVIEWED_SOURCE_COMMIT,laundry=laundry,dyeing=recipes,wip=wip)
