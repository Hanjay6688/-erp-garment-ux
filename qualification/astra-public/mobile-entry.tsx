import React from 'react'
import {createRoot} from 'react-dom/client'
import NativeAnalysisPanel from './src/NativeAnalysisPanel'
import ConnectedRemindersPage from './src/ConnectedRemindersPage'
import fixture from './tests/fixtures/nativeAnalysisStandin.json'
import {recoveryIdentity} from './tests/fixtures/productionRecovery'
const auth=structuredClone(recoveryIdentity) as any
auth.runtime.mode='DISPOSABLE_TEST'
auth.runtime.projectRef='astra-simulator'
auth.identity.profile.authUserId=fixture.analysis.scope.actor_scope_id
auth.identity.permissions=[...new Set([...auth.identity.permissions,'master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view','settings.reminder.view','settings.reminder.manage'])]
Object.assign(window,{auditAuth:auth})
const noop=()=>{}
const root=createRoot(document.getElementById('erp')!)
if(new URLSearchParams(location.search).has('reminders')) root.render(<ConnectedRemindersPage/>)
else root.render(<NativeAnalysisPanel query={fixture.query as any} onSourceReadStart={noop} onSourceReadEnd={noop} onClose={noop}/>)
