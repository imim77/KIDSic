import { useEffect, useRef, useState, type ReactNode } from 'react'
import './fullscreen.css'

type DisplayMode = 'inline' | 'native' | 'fallback'

export interface HostFullscreen {
  expanded: boolean
  request: (mode: 'inline' | 'fullscreen') => Promise<void>
}

// FullscreenFrame expands the existing explorer without replacing its map.
export function FullscreenFrame({ children, className = '', hostFullscreen }: { children: ReactNode; className?: string; hostFullscreen?: HostFullscreen }) {
  const frameRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const previousFocus = useRef<HTMLElement | null>(null)
  const modeRef = useRef<DisplayMode>('inline')
  const mounted = useRef(false)
  const pendingRef = useRef(false)
  const [mode, setMode] = useState<DisplayMode>('inline')
  const [pending, setPending] = useState(false)
  const expanded = hostFullscreen?.expanded ?? mode !== 'inline'

  const changeMode = (next: DisplayMode) => {
    modeRef.current = next
    setMode(next)
  }
  const finishRequest = () => {
    pendingRef.current = false
    if (mounted.current) setPending(false)
  }
  const restoreFocus = () => {
    if (previousFocus.current?.isConnected) previousFocus.current.focus({ preventScroll: true })
    previousFocus.current = null
  }
  const exitNative = async () => {
    if (pendingRef.current || document.fullscreenElement !== frameRef.current) return
    pendingRef.current = true
    setPending(true)
    try {
      await document.exitFullscreen()
    } catch {
      // Keep the actual native state when the browser refuses an exit.
    } finally {
      finishRequest()
    }
  }

  useEffect(() => {
    mounted.current = true
    const frame = frameRef.current
    const synchronize = () => {
      const isNative = document.fullscreenElement === frame
      if (isNative) {
        modeRef.current = 'native'
        setMode('native')
      } else if (modeRef.current === 'native') {
        modeRef.current = 'inline'
        setMode('inline')
        restoreFocus()
      }
      pendingRef.current = false
      setPending(false)
    }
    document.addEventListener('fullscreenchange', synchronize)
    return () => {
      mounted.current = false
      document.removeEventListener('fullscreenchange', synchronize)
      if (document.fullscreenElement === frame) void document.exitFullscreen().catch(() => {})
      // Fallback cleanup restores focus after it removes inert from the page.
      if (modeRef.current !== 'fallback') restoreFocus()
    }
  }, [])

  useEffect(() => {
    if (mode !== 'fallback') return
    const frame = frameRef.current!
    const previousOverflow = document.body.style.getPropertyValue('overflow')
    const previousOverflowPriority = document.body.style.getPropertyPriority('overflow')
    const outside: Array<{ element: HTMLElement; inert: boolean }> = []
    // Only siblings become inert: an inert ancestor would disable the map too.
    for (let branch: HTMLElement = frame; branch.parentElement; branch = branch.parentElement) {
      for (const sibling of branch.parentElement.children) {
        if (sibling !== branch && sibling instanceof HTMLElement) {
          outside.push({ element: sibling, inert: sibling.hasAttribute('inert') })
          sibling.setAttribute('inert', '')
        }
      }
      if (branch.parentElement === document.body) break
    }
    document.body.style.overflow = 'hidden'
    if (!frame.contains(document.activeElement)) buttonRef.current?.focus({ preventScroll: true })
    const keepFocusInside = (event: FocusEvent) => {
      if (!frame.contains(event.target as Node)) buttonRef.current?.focus({ preventScroll: true })
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented) return
      if (event.key === 'Escape') {
        event.preventDefault()
        modeRef.current = 'inline'
        setMode('inline')
      } else if (event.key === 'Tab') {
        const controls = Array.from(frame.querySelectorAll<HTMLElement>(
          'a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]',
        )).filter((element) => element.tabIndex >= 0 && !element.closest('[hidden], [inert], [aria-hidden="true"]')
          && getComputedStyle(element).display !== 'none' && getComputedStyle(element).visibility !== 'hidden')
        const first = controls[0] ?? frame
        const last = controls.at(-1) ?? frame
        if (!frame.contains(document.activeElement) || (event.shiftKey && document.activeElement === first)
          || (!event.shiftKey && document.activeElement === last)) {
          event.preventDefault()
          const target = event.shiftKey ? last : first
          target.focus({ preventScroll: true })
        }
      }
    }
    document.addEventListener('focusin', keepFocusInside)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('focusin', keepFocusInside)
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.setProperty('overflow', previousOverflow, previousOverflowPriority)
      for (const { element, inert } of outside) {
        if (!inert) element.removeAttribute('inert')
      }
      restoreFocus()
    }
  }, [mode])

  const toggle = async () => {
    const frame = frameRef.current
    if (!frame || pendingRef.current) return
    if (hostFullscreen) {
      pendingRef.current = true
      setPending(true)
      try {
        await hostFullscreen.request(hostFullscreen.expanded ? 'inline' : 'fullscreen')
      } catch {
        // Host state remains authoritative when it refuses a display change.
      } finally {
        finishRequest()
      }
      return
    }
    if (document.fullscreenElement === frame) {
      await exitNative()
      return
    }
    if (modeRef.current === 'fallback') {
      changeMode('inline')
      return
    }
    previousFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    if (!frame.requestFullscreen || document.fullscreenEnabled === false) {
      changeMode('fallback')
      return
    }
    pendingRef.current = true
    setPending(true)
    try {
      // This must run in the click, while browser user activation is available.
      await frame.requestFullscreen()
      if (!mounted.current) {
        if (document.fullscreenElement === frame) await document.exitFullscreen()
      } else if (document.fullscreenElement === frame) {
        changeMode('native')
      }
    } catch {
      if (mounted.current && modeRef.current === 'inline') changeMode('fallback')
    } finally {
      finishRequest()
    }
  }

  return (
    <div
      ref={frameRef}
      className={`explorer-frame ${expanded ? 'explorer-frame--expanded' : ''} ${mode === 'fallback' ? 'explorer-frame--fallback' : ''} ${className}`}
      role={mode === 'fallback' ? 'dialog' : undefined}
      aria-modal={mode === 'fallback' ? true : undefined}
      aria-label={mode === 'fallback' ? 'Karta i vrtići preko cijelog prozora' : undefined}
      tabIndex={-1}
      onKeyDown={(event) => {
        if (event.key === 'Escape' && !event.defaultPrevented && mode === 'native') void exitNative()
      }}
    >
      {children}
      <button
        ref={buttonRef}
        className="fullscreen-toggle"
        type="button"
        aria-label={expanded ? 'Vrati prikaz' : 'Prikaži preko cijelog ekrana'}
        title={expanded ? 'Vrati prikaz' : 'Prikaži preko cijelog ekrana'}
        aria-pressed={expanded}
        aria-disabled={pending}
        aria-busy={pending}
        onClick={() => { void toggle() }}
      >
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d={expanded ? 'M9 3v6H3m12-6v6h6M9 21v-6H3m12 6v-6h6' : 'M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5'} />
        </svg>
      </button>
    </div>
  )
}
