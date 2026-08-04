import { useEffect, useRef } from 'react'
import { pointers, diag } from '../lib/hands'

/**
 * Where your hands are.
 *
 * A touchless interface without a visible cursor is a guessing game: you cannot
 * see your own hand against the screen, so without this you are aiming at a
 * button you can only infer the position of. The reticle is not decoration, it
 * is the entire feedback loop.
 *
 * Two things it has to say at a glance: where the press will land, and how
 * close you are to pressing. The ring tightens as your finger and thumb close,
 * so the press is something you approach rather than something that happens to
 * you — which is what makes a pinch feel deliberate instead of accidental.
 *
 * Driven imperatively. The positions update at camera rate and nothing else on
 * screen depends on them, so this writes transforms directly rather than
 * re-rendering the HUD sixty times a second to move two circles.
 */

const MAX_HANDS = 2

export function Pointer() {
  const shells = useRef<(HTMLDivElement | null)[]>([])
  const raf = useRef(0)

  useEffect(() => {
    const tick = () => {
      raf.current = requestAnimationFrame(tick)
      for (let i = 0; i < MAX_HANDS; i++) {
        const el = shells.current[i]
        if (!el) continue
        const p = pointers.find((q) => q.id === i)
        if (!p || !diag.enabled) {
          if (el.style.opacity !== '0') el.style.opacity = '0'
          continue
        }
        el.style.opacity = '1'
        // translate3d to keep it on the compositor — this moves every frame and
        // has no business triggering layout.
        el.style.transform = `translate3d(${p.x}px, ${p.y}px, 0) translate(-50%, -50%)`
        el.dataset.pinched = p.pinched ? '1' : '0'
        el.style.setProperty('--close', String(p.closeness))
      }
    }
    tick()
    return () => cancelAnimationFrame(raf.current)
  }, [])

  return (
    <div className="hands" aria-hidden="true">
      {Array.from({ length: MAX_HANDS }, (_, i) => (
        <div
          key={i}
          ref={(el) => {
            shells.current[i] = el
          }}
          className="hand-dot"
          style={{ opacity: 0 }}
        >
          {/* Outer ring closes toward the core as the pinch tightens. */}
          <span className="hand-ring" />
          <span className="hand-core" />
        </div>
      ))}
    </div>
  )
}
