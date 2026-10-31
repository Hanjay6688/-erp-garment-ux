"""Reverse exactly two current read-driver edits before older source proofs."""
from hashlib import sha256
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent
IMPORT_BEFORE="import {observeResponseWaits} from './response_waits.mjs'"
IMPORT_AFTER=IMPORT_BEFORE+"\nimport {freshRead} from './fresh_read.mjs'"
READ_BEFORE=" async function poolReload(){const before=state('BEFORE_POOL_READ'),pending=page.waitForResponse(isRpc(RPC.poolRead));await pools().getByRole('button',{name:'Muat ulang daftar pool',exact:true}).click();const workspace=await success(pending);equalCensus(before.census,state('AFTER_POOL_READ').census);return workspace}"
READ_AFTER=""" async function poolReload(){
  const before=state('BEFORE_POOL_READ')
  const current=await freshRead(page,RPC.poolRead,()=>pools().getByRole('button',{name:'Muat ulang daftar pool',exact:true}).click())
  const workspace=await success(current.response)
  ;(progress.pool_reads??=[]).push({request_started_at:current.request_started_at,refresh_registered_at:current.refresh_registered_at,actual_workspace:workspace})
  equalCensus(before.census,state('AFTER_POOL_READ').census);return workspace
 }"""
EDITS=((IMPORT_BEFORE,IMPORT_AFTER),(READ_BEFORE,READ_AFTER))


def previous(raw,here=HERE):
    retained=(here/'retained-a209/cases.mjs.txt').read_bytes()
    pin=json.loads((here/'retained-a209/SOURCE.json').read_bytes())['files']['cases.mjs']
    if len(retained)!=pin['bytes'] or sha256(retained).hexdigest()!=pin['sha256']:
        raise ValueError('S03_REFRESH_EXACT_A209_PREIMAGE_REQUIRED')
    text=retained.decode()
    for before,after in EDITS:
        if text.count(before)!=1 or after in text:raise ValueError('S03_REFRESH_EXACT_FORWARD_ANCHOR_REQUIRED')
        text=text.replace(before,after,1)
    if text.encode()!=raw:raise ValueError('S03_REFRESH_ONLY_DECLARED_READ_DRIVER_EDITS_ALLOWED')
    for before,after in reversed(EDITS):
        if text.count(after)!=1:raise ValueError('S03_REFRESH_EXACT_REVERSE_ANCHOR_REQUIRED')
        text=text.replace(after,before,1)
    if text.encode()!=retained:raise ValueError('S03_REFRESH_COMPLETE_A209_BYTES_REQUIRED')
    return retained
