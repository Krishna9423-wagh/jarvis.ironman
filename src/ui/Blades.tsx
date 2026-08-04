import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion, useDragControls } from 'framer-motion'
import { useStore, type Blade } from '../store'
import { BRIDGE_HTTP_URL } from '../config'
import { sanitisePanelHtml } from './sanitise'

/**
 * The blades.
 *
 * This file used to be six slivers of light raking across the frame while a
 * tool ran — pure atmosphere, nothing you could read. That effect is still
 * here, at the bottom, because it is still the right answer to "something is
 * happening". But the name now belongs to the surface it was decorating.
 *
 * A panel is a card you glance at while listening: a figure, three headlines, a
 * status line. A blade is the thing you actually look at. The distinction is
 * not styling, it is geometry — an article you are meant to READ needs a column
 * of a particular width and a height you can scroll, and no amount of care
 * makes that work inside a 320px card stacked beside the reactor. So blades own
 * their size, they stack instead of replacing one another, and the user can
 * pull an older one forward or throw one to full screen.
 *
 * The hard problem a blade solves is that most of the web refuses to be shown.
 * X-Frame-Options and frame-ancestors stop an article being framed, CORS stops
 * the page fetching it, and hotlink protection stops even its images loading.
 * All three are rules the origin server enforces against the *browser*, so the
 * bridge takes the browser out of it: it fetches server-side and serves the
 * result from localhost, and at that point the document in the iframe is ours.
 *
 * Nothing in this file is a special case for a particular site, and nothing
 * here sniffs a file extension. The model asks `probe_url` what a thing is and
 * says what it wants shown; this only knows how to show it.
 */

/* ------------------------------------------------------------------ sources */

/**
 * Paths that are genuinely on this machine's disk, as opposed to app-relative
 * URLs that happen to start with a slash. Mirrors the test in sanitise.ts and
 * Orbits.tsx — the list of root directories is the sort of thing that should be
 * changed in each place deliberately.
 */
const DISK_PATH =
  /^\/(Users|home|root|Volumes|Applications|System|Library|private|tmp|var|opt|mnt|media|srv|data)\//

/** Route a source through the bridge, which is the only origin that can
 *  actually fetch it — and the only one the page CSP will load from. */
function viaBridge(raw: string, route: 'img' | 'media'): string {
  const src = String(raw ?? '').trim()
  if (!src) return ''
  const path = src.replace(/^file:\/\//, '')
  if (DISK_PATH.test(path)) {
    return `${BRIDGE_HTTP_URL}/file?path=${encodeURIComponent(path)}`
  }
  if (!/^https?:\/\//i.test(src)) return src
  if (src.startsWith(`${BRIDGE_HTTP_URL}/`)) return src
  return `${BRIDGE_HTTP_URL}/${route}?url=${encodeURIComponent(src)}`
}

/** A whole document, rendered by the bridge so it can be framed at all. */
const pageUrl = (url: string, mode: 'reader' | 'live') =>
  `${BRIDGE_HTTP_URL}/page?mode=${mode}&url=${encodeURIComponent(url)}`

/**
 * The three embed hosts, and only these.
 *
 * Same closed list as the panel sanitiser, for the same reason: YouTube and
 * Vimeo will not hand over the media file, so an iframe is the only way to play
 * a result inline, and the trade for that is that the host list does not grow.
 */
function embedUrl(raw: string): string | null {
  let url: URL
  try {
    url = new URL(raw)
  } catch {
    return null
  }
  const host = url.hostname.toLowerCase().replace(/^(?:www|m|music)\./, '')
  const id = (s: string) => (/^[\w-]{6,20}$/.test(s) ? s : null)

  if (host === 'youtube.com' && url.pathname === '/watch') {
    const v = id(url.searchParams.get('v') ?? '')
    return v && `https://www.youtube-nocookie.com/embed/${v}`
  }
  if (host === 'youtu.be') {
    const v = id(url.pathname.slice(1))
    return v && `https://www.youtube-nocookie.com/embed/${v}`
  }
  if (host === 'youtube-nocookie.com' && /^\/embed\/[\w-]+/.test(url.pathname)) return url.href
  if (host === 'vimeo.com') {
    const v = url.pathname.split('/').filter(Boolean)[0] ?? ''
    return /^\d+$/.test(v) ? `https://player.vimeo.com/video/${v}` : null
  }
  if (host === 'player.vimeo.com' && /^\/video\/\d+/.test(url.pathname)) return url.href
  return null
}

/* --------------------------------------------------------------------- body */

/**
 * What goes inside a blade.
 *
 * Every iframe is sandboxed. `allow-same-origin` is deliberately absent from
 * the proxied-page case: that document is served from the bridge's own origin —
 * the one origin permitted to open the agent socket — so granting it
 * same-origin would let a page JARVIS found on the web reach that socket. It
 * does not need it. It is being read, not run.
 */
const Body = memo(function Body({ blade }: { blade: Blade }) {
  if (blade.kind === 'article' && blade.url) {
    return (
      <iframe
        className="bl-frame"
        src={pageUrl(blade.url, blade.mode ?? 'reader')}
        sandbox=""
        referrerPolicy="no-referrer"
        title={blade.title}
      />
    )
  }

  if (blade.kind === 'embed' && blade.url) {
    const embed = embedUrl(blade.url)
    if (!embed) return <p className="bl-note">That video link could not be played.</p>
    return (
      <iframe
        className="bl-frame"
        src={embed}
        // A player genuinely needs scripts and its own origin. Nothing that
        // reaches the room the user is sitting in is granted.
        sandbox="allow-scripts allow-same-origin allow-presentation"
        allow="accelerometer; encrypted-media; picture-in-picture; fullscreen"
        referrerPolicy="no-referrer"
        allowFullScreen
        title={blade.title}
      />
    )
  }

  if (blade.kind === 'video' && blade.url) {
    return (
      <video
        className="bl-video"
        src={viaBridge(blade.url, 'media')}
        controls
        playsInline
        preload="metadata"
      />
    )
  }

  if (blade.kind === 'image' && blade.url) {
    return <img className="bl-image" src={viaBridge(blade.url, 'img')} alt={blade.title} />
  }

  if (blade.kind === 'gallery') {
    return (
      <div className="bl-gallery">
        {(blade.images ?? []).map((src, i) => (
          <img key={`${src}-${i}`} className="bl-thumb" src={viaBridge(src, 'img')} alt="" />
        ))}
      </div>
    )
  }

  if (blade.kind === 'markup' && blade.html) {
    // Model-authored markup gets exactly the treatment panel markup gets.
    // There is one sanitiser, and this is it.
    return (
      <div
        className="bl-markup p-body"
        dangerouslySetInnerHTML={{ __html: sanitisePanelHtml(blade.html) }}
      />
    )
  }

  return <p className="bl-note">Nothing to show.</p>
})

/* -------------------------------------------------------------------- card */

function Card({
  blade,
  depth,
  focused,
  expanded,
  onFocus,
  onExpand,
  onClose,
}: {
  blade: Blade
  /** 0 is front-most. Drives the offset and the dimming behind it. */
  depth: number
  focused: boolean
  expanded: boolean
  onFocus: () => void
  onExpand: () => void
  onClose: () => void
}) {
  const drag = useDragControls()
  /** Size the user has dragged this blade to, overriding the class preset. */
  const [size, setSize] = useState<{ w: number; h: number } | null>(null)
  const shell = useRef<HTMLDivElement>(null)

  /**
   * Resize from the bottom-right grip.
   *
   * Pointer capture rather than window listeners: the pointer spends most of a
   * resize over an <iframe>, and an iframe swallows mousemove from the parent
   * document entirely. Without capture the blade stops resizing the instant the
   * cursor crosses into the article it is showing, which is precisely where it
   * always crosses.
   */
  const onGrip = (e: React.PointerEvent<HTMLSpanElement>) => {
    e.preventDefault()
    e.stopPropagation()
    const box = shell.current?.getBoundingClientRect()
    if (!box) return
    const startX = e.clientX
    const startY = e.clientY
    const from = { w: box.width, h: box.height }
    const grip = e.currentTarget
    grip.setPointerCapture(e.pointerId)

    const move = (ev: PointerEvent) => {
      setSize({
        w: Math.max(280, Math.min(window.innerWidth * 0.96, from.w + (ev.clientX - startX))),
        h: Math.max(180, Math.min(window.innerHeight * 0.94, from.h + (ev.clientY - startY))),
      })
    }
    const done = () => {
      grip.releasePointerCapture(e.pointerId)
      grip.removeEventListener('pointermove', move)
      grip.removeEventListener('pointerup', done)
      grip.removeEventListener('pointercancel', done)
    }
    grip.addEventListener('pointermove', move)
    grip.addEventListener('pointerup', done)
    grip.addEventListener('pointercancel', done)
  }

  return (
    /**
     * Two elements, because two different things want the transform.
     *
     * The outer one carries the depth offset — the small lift and scale that
     * makes the stack read as objects rather than as a list. The inner one is
     * what the user drags. Framer owns `transform` on anything it animates, so
     * with both jobs on one element the drag and the stack animation overwrite
     * each other every frame and the blade jitters back to its slot.
     */
    <motion.div
      className="bl-slot"
      initial={{ opacity: 0, y: 26, scale: 0.96, filter: 'blur(6px)' }}
      animate={{
        opacity: expanded || depth === 0 ? 1 : Math.max(0.3, 1 - depth * 0.24),
        y: expanded ? 0 : depth * -13,
        x: expanded ? 0 : depth * 15,
        scale: expanded ? 1 : 1 - depth * 0.035,
        filter: depth === 0 || expanded ? 'blur(0px)' : `blur(${depth * 0.7}px)`,
      }}
      exit={{ opacity: 0, y: 18, filter: 'blur(8px)', transition: { duration: 0.28 } }}
      transition={{ type: 'spring', stiffness: 260, damping: 30 }}
      style={{ zIndex: expanded ? 60 : 40 - depth }}
    >
      <motion.section
        ref={shell}
        className={
          `bl bl-${blade.size}` +
          (expanded ? ' bl-expanded' : '') +
          (focused ? ' bl-front' : '')
        }
        // Dragged by the header only. `dragListener={false}` is what makes that
        // true: without it the whole card is a drag handle, and every attempt to
        // select a line of the article drags the blade across the screen instead.
        drag={!expanded}
        dragControls={drag}
        dragListener={false}
        dragMomentum={false}
        dragElastic={0.04}
        // Kept inside the window, with enough slack that a blade can be pushed
        // mostly off-screen when the user wants it out of the way.
        dragConstraints={{ top: -260, bottom: 260, left: -520, right: 520 }}
        style={size && !expanded ? { width: size.w, height: size.h } : undefined}
        onMouseDown={() => {
          if (!focused) onFocus()
        }}
      >
        <span className="pk pk-tl" />
        <span className="pk pk-tr" />
        <span className="pk pk-bl" />
        <span className="pk pk-br" />

        <header
          className="bl-head"
          onPointerDown={(e) => {
            // Buttons live in here too; starting a drag from one would mean the
            // click never lands.
            if ((e.target as HTMLElement).closest('button')) return
            if (!expanded) drag.start(e)
          }}
        >
          <span className="bl-title">{blade.title}</span>
          <span className="bl-kind">{blade.kind}</span>
          <span className="bl-acts">
            {size && !expanded && (
              <button
                className="bl-btn"
                onClick={(e) => {
                  e.stopPropagation()
                  setSize(null)
                }}
                title="Back to its normal size"
              >
                ⤾
              </button>
            )}
            <button
              className="bl-btn"
              onClick={(e) => {
                e.stopPropagation()
                onExpand()
              }}
              title={expanded ? 'Shrink (E)' : 'Full screen (E)'}
            >
              {expanded ? '⤡' : '⤢'}
            </button>
            <button
              className="bl-btn"
              onClick={(e) => {
                e.stopPropagation()
                onClose()
              }}
              title="Close (X)"
            >
              ✕
            </button>
          </span>
        </header>

        <div className="bl-body">
          <Body blade={blade} />
        </div>

        {/* Resize grip. Absent while expanded, where the size is the point. */}
        {!expanded && <span className="bl-grip" onPointerDown={onGrip} title="Drag to resize" />}
      </motion.section>
    </motion.div>
  )
}

/* ------------------------------------------------------------------- stack */

export function Blades() {
  const blades = useStore((s) => s.blades)
  const focusedBlade = useStore((s) => s.focusedBlade)
  const expandedBlade = useStore((s) => s.expandedBlade)
  const focusBlade = useStore((s) => s.focusBlade)
  const expandBlade = useStore((s) => s.expandBlade)
  const closeBlade = useStore((s) => s.closeBlade)

  /**
   * Newest first, then whichever the user pulled forward lifted to the front.
   *
   * Ordered here rather than in the store because it is a view concern, and the
   * store's array order is the history — which is what makes "the one before
   * that" a meaningful thing to ask for.
   */
  const ordered = useMemo(() => {
    const newestFirst = [...blades].reverse()
    if (!focusedBlade) return newestFirst
    const hit = newestFirst.findIndex((b) => b.id === focusedBlade)
    if (hit <= 0) return newestFirst
    const copy = [...newestFirst]
    const [lifted] = copy.splice(hit, 1)
    return [lifted, ...copy]
  }, [blades, focusedBlade])

  const front = ordered[0]

  const cycle = useCallback(
    (by: number) => {
      if (ordered.length < 2) return
      const at = ordered.findIndex((b) => b.id === front?.id)
      const next = ordered[(at + by + ordered.length) % ordered.length]
      if (next) focusBlade(next.id)
    },
    [ordered, front, focusBlade],
  )

  // Bound here rather than in App, and only while something is open, so E and X
  // are free for anything else the moment the last blade closes.
  const live = useRef(false)
  live.current = blades.length > 0

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!live.current) return
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA') return
      if (e.metaKey || e.ctrlKey || e.altKey || e.repeat) return

      if (e.key === 'e') {
        e.preventDefault()
        expandBlade(expandedBlade ? null : (front?.id ?? null))
      } else if (e.key === 'x') {
        e.preventDefault()
        if (front) closeBlade(front.id)
      } else if (e.key === ']') {
        e.preventDefault()
        cycle(1)
      } else if (e.key === '[') {
        e.preventDefault()
        cycle(-1)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [front, expandedBlade, expandBlade, closeBlade, cycle])

  if (!blades.length) return null

  return (
    <div className={`blades-stack${expandedBlade ? ' blades-stack-full' : ''}`}>
      <AnimatePresence>
        {ordered.map((blade, i) => {
          const expanded = expandedBlade === blade.id
          // While one is expanded it is the only thing on screen; the rest are
          // unmounted rather than hidden so their iframes stop loading.
          if (expandedBlade && !expanded) return null
          return (
            <Card
              key={blade.id}
              blade={blade}
              depth={expanded ? 0 : i}
              focused={blade.id === front?.id}
              expanded={expanded}
              onFocus={() => focusBlade(blade.id)}
              onExpand={() => expandBlade(expanded ? null : blade.id)}
              onClose={() => closeBlade(blade.id)}
            />
          )
        })}
      </AnimatePresence>

      {blades.length > 1 && !expandedBlade && (
        <div className="bl-hint">
          <kbd>[</kbd> <kbd>]</kbd> cycle · <kbd>E</kbd> full · <kbd>X</kbd> close
        </div>
      )}
    </div>
  )
}

/* --------------------------------------------------------------- the sweep */

/**
 * The original blades: slivers of light raking across the frame while a tool
 * runs. Unchanged, because it is still the right answer to "something is
 * happening" — a tool call is the one moment the interface stops being a face
 * and becomes machinery, and the reactor cannot carry that on its own.
 *
 * Deliberately CSS rather than three.js: the scene is bloomed and tone-mapped,
 * which is exactly wrong for a 1px edge. Kept in the DOM it stays a blade.
 */
const SWEEP = [1, 2, 3, 4, 5, 6]

export function BladeSweep() {
  const phase = useStore((s) => s.phase)
  const activeTool = useStore((s) => s.activeTool)

  return (
    <AnimatePresence>
      {phase === 'tooling' && (
        <motion.div
          className="blades"
          // Only opacity is animated here. The sweeps are CSS keyframes on the
          // children, and framer writes `transform` inline on anything it
          // animates — one transform prop in this list and every blade would be
          // sliding inside an element that is itself sliding.
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
        >
          <div className="blade-field">
            {SWEEP.map((n) => (
              <span key={n} className={`blade blade-${n}`} />
            ))}
          </div>

          {activeTool && (
            // Keyed on the name so a chain of tools re-runs the ride-in for
            // each one rather than silently swapping the text mid-sweep.
            <div className="blade-carrier">
              <span key={activeTool} className="blade-tool">
                {activeTool}
              </span>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
