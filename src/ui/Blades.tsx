import { AnimatePresence, motion } from 'framer-motion'
import { useStore } from '../store'

/**
 * The blade sweep — what "accessing systems" looks like.
 *
 * A tool call is the one moment the interface stops being a face and becomes
 * machinery, and the reactor cannot carry that on its own: it is a circle, it
 * breathes, and it says the same thing whether JARVIS is idle or halfway
 * through a shell command. So the tool phase gets its own vocabulary —
 * angular, directional, transient. Slivers of light rake across the frame at a
 * tilt, fastest and brightest in the middle where the reactor sits, and the
 * name of the running tool rides in on them.
 *
 * Deliberately CSS rather than three.js. The scene is bloomed and tone-mapped,
 * which is exactly wrong for a 1px edge — anything this thin drawn into the
 * canvas comes back as a soft smear. Kept in the DOM it stays a blade.
 *
 * The choreography lives in index.css (`.blade-1` … `.blade-6`) rather than in
 * props here: six slivers with six different widths, tilts, tempos and entry
 * delays is a lookup table, and a lookup table reads better as CSS than as an
 * array of style objects. It is also the only way the reduced-motion variant
 * can replace the whole thing with a still frame.
 */

const BLADES = [1, 2, 3, 4, 5, 6]

export function Blades() {
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
            {BLADES.map((n) => (
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
