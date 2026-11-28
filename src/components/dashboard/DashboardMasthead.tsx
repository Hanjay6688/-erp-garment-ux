import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Blocks, LayoutDashboard, Pause, Play, Scissors } from 'lucide-react'
import './dashboard-masthead.css'

const viewKey = 'atelier.dashboard.view'
const motionKey = 'atelier.dashboard.motion'
const reducedMotion = '(prefers-reduced-motion: reduce)'

function preference(key: string) {
  try { return window.localStorage.getItem(key) } catch { return null }
}

function savePreference(key: string, value: string) {
  try { window.localStorage.setItem(key, value) } catch { /* Controls also work with storage disabled. */ }
}

type Props = { children: ReactNode; metrics?: ReactNode; planner?: ReactNode }

export default function DashboardMasthead({ children, metrics, planner }: Props) {
  const [pixel, setPixel] = useState(() => preference(viewKey) !== 'normal')
  function choose(next: boolean) {
    setPixel(next)
    savePreference(viewKey, next ? 'pixel' : 'normal')
  }

  return <>
    <div className="summary-cover" data-view={pixel ? 'pixel' : 'normal'}>
      <div className="summary-cover-layout">
        <div className="summary-cover-intro">
          <div className="hero-copy">{children}</div>
          <div className="summary-mode" role="group" aria-label="Tampilan ringkasan bisnis">
            <button type="button" aria-pressed={pixel} onClick={() => choose(true)}><Blocks aria-hidden="true"/>Pixel</button>
            <button type="button" aria-pressed={!pixel} onClick={() => choose(false)}><LayoutDashboard aria-hidden="true"/>Normal</button>
          </div>
        </div>
        {pixel && <AtelierScene/>}
      </div>
    </div>
    {pixel ? metrics : planner}
    {pixel ? planner : metrics}
  </>
}

function AtelierScene() {
  const frame = useRef<HTMLElement>(null)
  const [paused, setPaused] = useState(() => preference(motionKey) === 'paused' || !!window.matchMedia?.(reducedMotion).matches)
  const [visible, setVisible] = useState(false)
  const [activeTab, setActiveTab] = useState(() => !document.hidden)

  useEffect(() => {
    const element = frame.current
    const observer = typeof IntersectionObserver === 'function' ? new IntersectionObserver(([entry]) => {
      setVisible(entry.isIntersecting)
    }) : null
    if (observer && element) observer.observe(element)
    else setVisible(true)

    const media = window.matchMedia?.(reducedMotion)
    const onMotionChange = () => setPaused(!!media?.matches || preference(motionKey) === 'paused')
    const onVisibility = () => setActiveTab(!document.hidden)
    media?.addEventListener('change', onMotionChange)
    document.addEventListener('visibilitychange', onVisibility)
    return () => {
      observer?.disconnect()
      media?.removeEventListener('change', onMotionChange)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [])

  function toggleMotion() {
    setPaused(!paused)
    savePreference(motionKey, paused ? 'auto' : 'paused')
  }
  return <figure ref={frame} className="atelier-scene" aria-label="Lantai produksi" data-running={!paused && visible && activeTab}>
    <figcaption className="atelier-toolbar">
      <span><Scissors aria-hidden="true"/>Lantai produksi</span>
      <button type="button" onClick={toggleMotion}>
        {paused ? <Play aria-hidden="true"/> : <Pause aria-hidden="true"/>}
        {paused ? 'Putar animasi' : 'Jeda animasi'}
      </button>
    </figcaption>
    <div className="atelier-viewport" role="img" aria-label="Ilustrasi atelier garmen dengan penjahit, pemotong pola, petugas pemeriksa, dan pembawa kain.">
      <div className="atelier-room" aria-hidden="true">
        <span className="atelier-worker atelier-sew"/>
        <span className="atelier-worker atelier-cut"/>
        <span className="atelier-worker atelier-inspect"/>
        <span className="atelier-benches"/>
        <span className="atelier-walk-route"><span className="atelier-walk-facing"><i className="atelier-worker atelier-courier"/></span></span>
      </div>
    </div>
  </figure>
}
