// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import NativeFrozenProgress from './NativeFrozenProgress'
import type {StagedJob} from '../../../src/nativeStagedJob'

let root:Root,container:HTMLDivElement
const job=(extra:Partial<StagedJob>={}):StagedJob=>({requestId:'job',state:'RUNNING',stage:'HIST_ROWS',stageIndex:3,stageCount:9,unitsDone:12,unitCount:55,planFinal:false,targetsTotal:3600,targetsDoneInStage:1200,reference:{capturedAt:'2026-10-26T01:00:00Z',sourceHash:'a'.repeat(64)},lastProgressAt:'2026-10-26T01:00:10Z',unitAttempts:0,runId:null,failure:null,workerActive:false,serverRunner:{active:true,lastTickAt:'2026-10-26T01:00:10Z'},retention:null,...extra})
const render=async(j:StagedJob|null,busy=true,interrupted=false,blocked=false,financeSelected=false)=>act(async()=>{root.render(<NativeFrozenProgress job={j} busy={busy} interrupted={interrupted} blocked={blocked} financeSelected={financeSelected}/>)})
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});vi.useFakeTimers();vi.setSystemTime(new Date('2026-10-26T01:00:10Z'));container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();expect(vi.getTimerCount()).toBe(0);vi.useRealTimers()})
it('updates elapsed duration without inventing completed units or a percentage',async()=>{
 await render(job());expect(container.textContent).toContain('Menghitung riwayat per produk');expect(container.textContent).toContain('12 dari 55');expect(container.querySelector('progress')).toBeNull()
 await act(async()=>vi.advanceTimersByTimeAsync(10_000))
 expect(container.textContent).toContain('20 detik');expect(container.textContent).toContain('12 dari 55');expect(container.textContent).toContain('1.200 dari 3.600');expect(container.querySelector('progress')).toBeNull()
 await render(job({unitsDone:13,planFinal:true}));expect(container.querySelector('progress')?.value).toBe(13);expect(container.textContent).toContain('23% langkah produksi')
})
it('keeps completed production separate from financial completeness and never runs a success animation timer',async()=>{
 await render(job({state:'DONE',unitsDone:55,planFinal:true,stage:null}),false,false,false,true)
 expect(container.textContent).toContain('Perhitungan produksi selesai');expect(container.textContent).toContain('belum berarti analisis gabungan lengkap');expect(container.textContent).toContain('tidak mencakup keuangan/HPP');expect(vi.getTimerCount()).toBe(0)
})
it('distinguishes unknown start, blocked data, interrupted monitoring and confirmed server failure',async()=>{
 await render(null);expect(container.textContent).toContain('jumlah pekerjaan belum diketahui');expect(container.querySelector('progress')).toBeNull()
 await render(null,false,true,true);expect(container.textContent).toContain('Analisis tertahan')
 await render(job(),false,true);expect(container.textContent).toContain('Pemantauan terhenti');expect(container.textContent).not.toContain('Analisis produksi gagal')
 await render(job({state:'FAILED'}),false,true);expect(container.textContent).toContain('Analisis produksi gagal')
})
it('warns on stale observed progress and does not promise background work without an active server runner',async()=>{
 await render(job({serverRunner:null}));expect(container.textContent).toContain('Pekerja server belum terkonfirmasi aktif')
 await act(async()=>vi.advanceTimersByTimeAsync(120_000));expect(container.textContent).toContain('ini belum berarti pekerjaan gagal');expect(container.textContent).toContain('12 dari 55')
})
