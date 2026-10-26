// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,expect,it,vi} from 'vitest'
import CombinedProgress from './CombinedProgress'
import {readProgressTelemetry} from '../cp7_current_analysis_progress/telemetry'
import {progressFixture} from './progressFixture'
let root:Root,container:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.useRealTimers()})
const render=async(value:ReturnType<typeof readProgressTelemetry>)=>act(async()=>{root.render(<CombinedProgress value={value}/>)})
it('keeps production complete separate from finance with an unknown total',async()=>{
 const f=await progressFixture(),value=readProgressTelemetry(f.wire,f.request)
 await render(value)
 expect(container.querySelector('[role=status]')?.textContent).toContain('masih menunggu laporan keuangan resmi')
 expect(container.querySelectorAll('progress')).toHaveLength(1)
 expect(container.textContent).toContain('jumlah akhir belum diketahui')
})
it('does not invent elapsed time or progress when only the client clock moves',async()=>{
 const f=await progressFixture();vi.useFakeTimers();await render(readProgressTelemetry(f.wire,f.request));const before=container.textContent
 vi.advanceTimersByTime(3600000);expect(container.textContent).toBe(before)
 expect(before).toContain('5 menit 0 detik')
})
it('keeps completed duration fixed on a later reopening',async()=>{
 const f=await progressFixture(true);await render(readProgressTelemetry(f.wire,f.request))
 expect(container.textContent).toContain('Waktu pemrosesan: 4 menit 0 detik')
 f.wire.observed_at='2026-10-08T10:05:00Z';await render(readProgressTelemetry(f.wire,f.request))
 expect(container.textContent).toContain('Waktu pemrosesan: 4 menit 0 detik')
})
it('explains old financial activity from server evidence without declaring the job failed',async()=>{
 const f=await progressFixture();f.wire.observed_at='2026-10-07T10:06:00Z'
 await render(readProgressTelemetry(f.wire,f.request))
 expect(container.querySelector('[role=alert]')?.textContent).toContain('Belum ada aktivitas keuangan baru yang tercatat selama 2 menit 0 detik')
 expect(container.textContent).toContain('Tidak ada proses keuangan aktif yang teramati saat pemeriksaan ini')
 expect(container.querySelector('[data-combined-state]')?.getAttribute('data-combined-state')).toBe('RUNNING')
 expect(container.querySelectorAll('progress')).toHaveLength(1)
})
it('keeps an observed active worker distinct from a stored advance',async()=>{
 const f=await progressFixture();f.wire.observed_at='2026-10-07T10:06:00Z';f.wire.finance.worker_observation='LOCK_HELD'
 await render(readProgressTelemetry(f.wire,f.request))
 expect(container.textContent).toContain('Proses keuangan teramati aktif saat pemeriksaan ini')
 expect(container.querySelector('[role=alert]')?.textContent).toContain('Pekerjaan belum dinyatakan gagal')
})
it('clears the activity notice only when newer server activity is read',async()=>{
 const f=await progressFixture();f.wire.observed_at='2026-10-07T10:06:00Z'
 await render(readProgressTelemetry(f.wire,f.request));expect(container.querySelector('[role=alert]')).not.toBeNull()
 f.wire.finance.last_activity_at='2026-10-07T10:05:00Z'
 await render(readProgressTelemetry(f.wire,f.request));expect(container.querySelector('[role=alert]')).toBeNull()
})
it('does not turn an old completed report into an activity warning',async()=>{
 const f=await progressFixture(true);f.wire.observed_at='2026-10-08T10:06:00Z'
 await render(readProgressTelemetry(f.wire,f.request))
 expect(container.querySelector('[role=alert]')).toBeNull()
 expect(container.textContent).not.toContain('teramati aktif')
})
