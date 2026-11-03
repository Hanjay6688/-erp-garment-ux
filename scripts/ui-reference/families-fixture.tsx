/* Isolated UI fixture only; no Auth client, database, writer or monetary effects. */
import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import '../../src/theme.css'
import '../../src/styles.css'
import '../../src/auth/auth.css'
import '../../src/brand-books.css'
import '../../src/movement-book.css'
import '../../src/global-readability.css'
import '../../src/procurement.css'
import '../../src/laundry.css'
import '../../src/workspace-refinements.css'
import '../../src/ux-corrections.css'
import '../../src/wip-control.css'
import '../../src/layout-resilience.css'
import '../../src/cutting-reminders.css'
import '../../src/quick-ui-layout-fixes.css'
import '../../src/wip-roll-operational.css'
import MandorShopCards from '../../src/MandorShopCards'
import { parseMandorShopWorkspace } from '../../src/mandorShopContract'
import { shopWorkspace, shopPayroll, shopMandor } from '../../tests/fixtures/mandorShop'

function Fixture() {
 const mode=new URLSearchParams(location.search).get('state')??'ready'
 const [open,setOpen]=useState(true),[calls,setCalls]=useState(0)
 const wire=shopWorkspace(mode==='approved')
 if(mode==='empty')wire.cards=[]
 if(mode==='long')wire.cards[0].number='INV-EPİ-2026-000123456789 — pesanan garment ukuran lengkap dengan keterangan panjang'
 if(mode==='approved'){wire.status='APPROVED';wire.can_change=false}
 const data=parseMandorShopWorkspace(wire,shopPayroll,shopMandor)
 const busy=mode==='loading',ready=!['loading','stale','error'].includes(mode)
 return <main className="page-wrap"><p role="note">FIXTURE UI TERISOLASI — data contoh, tanpa transaksi atau backend.</p>
  <button onClick={()=>setOpen(true)}>Buka kartu tagihan</button><output aria-label="Jumlah panggilan fixture">{calls}</output>
  <MandorShopCards open={open} payrollId={shopPayroll} payrollNumber="PAY-EPI-W2 · FIXTURE UI"
   contractorId={shopMandor} contractorName="Epi · data contoh" workspace={data} ready={ready} busy={busy}
   error={mode==='error'?'Pembacaan tagihan gagal. Muat ulang sumber sebelum melanjutkan.':undefined}
   onClose={()=>setOpen(false)} onReload={async()=>true} onNext={async()=>true}
   onReserve={async()=>{setCalls(n=>n+1);await new Promise(()=>{})}}
   onRelease={async()=>{setCalls(n=>n+1);await new Promise(()=>{})}}/>
 </main>
}
createRoot(document.getElementById('root')!).render(<Fixture/> )
