import { useCallback, useLayoutEffect, useRef, type HTMLAttributes } from 'react'

type BrowsePaneProps = HTMLAttributes<HTMLElement> & {
  as?: 'aside' | 'div' | 'main' | 'section'
  embedded?: boolean
}

export function BrowsePane({ as: Element = 'aside', embedded = false, className = '', ...props }: BrowsePaneProps) {
  const ref = useRef<HTMLElement>(null)
  const setPane = useCallback((pane: HTMLElement | null) => { ref.current = pane }, [])

  useLayoutEffect(() => {
    const pane = ref.current
    const workspace = pane?.parentElement
    if (!pane || !workspace) return

    const topbar = pane.closest('.main-panel')?.querySelector(':scope > .topbar')
    const viewport = window.visualViewport
    let frame: number | null = null

    const measure = () => {
      frame = null
      const bounds = pane.getBoundingClientRect()
      const detail = pane.nextElementSibling?.getBoundingClientRect()
      const sideBySide = bounds.width > 0 && detail && detail.width > 0 && detail.left >= bounds.right - 1
      if (!sideBySide) {
        delete pane.dataset.browseLayout
        pane.removeAttribute('data-browse-scroll')
        pane.removeAttribute('data-browse-overflow')
        pane.removeAttribute('tabindex')
        return
      }

      const layout = embedded ? 'embedded' : 'split'
      const layoutChanged = pane.dataset.browseLayout !== layout
      if (layoutChanged) pane.dataset.browseLayout = layout
      const viewportTop = viewport?.offsetTop ?? 0
      const headerBottom = Math.max(viewportTop, topbar?.getBoundingClientRect().bottom ?? 0)
      const stickyTop = Math.ceil(headerBottom + 8)
      const top = layoutChanged ? pane.getBoundingClientRect().top : bounds.top
      const viewportBottom = viewportTop + (viewport?.height ?? window.innerHeight) - 12
      const bottom = embedded ? Math.min(viewportBottom, workspace.getBoundingClientRect().bottom) : viewportBottom
      const height = Math.floor(bottom - Math.max(stickyTop, top))
      // Let the page scroll past the entrance when only a sliver of Browse is visible.
      pane.style.setProperty('--browse-pane-top', `${stickyTop}px`)
      pane.style.setProperty('--browse-pane-height', `${Math.max(0, height)}px`)
      const scrollable = height >= 80
      pane.toggleAttribute('data-browse-scroll', scrollable)
      const overflowing = scrollable && pane.scrollHeight > pane.clientHeight + 1
      pane.toggleAttribute('data-browse-overflow', overflowing)
      if (overflowing) pane.tabIndex = 0
      else pane.removeAttribute('tabindex')
    }

    function schedule() {
      if (frame === null) frame = window.requestAnimationFrame(measure)
    }

    const observer = new ResizeObserver(schedule)
    observer.observe(pane)
    observer.observe(workspace)
    if (topbar) observer.observe(topbar)
    window.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', schedule)
    viewport?.addEventListener('scroll', schedule)
    viewport?.addEventListener('resize', schedule)
    measure()

    return () => {
      if (frame !== null) window.cancelAnimationFrame(frame)
      observer.disconnect()
      window.removeEventListener('scroll', schedule)
      window.removeEventListener('resize', schedule)
      viewport?.removeEventListener('scroll', schedule)
      viewport?.removeEventListener('resize', schedule)
    }
  }, [Element, embedded])

  return <Element ref={setPane} className={`browse-pane ${className}`.trim()} role={Element === 'div' ? 'region' : undefined} {...props}/>
}
