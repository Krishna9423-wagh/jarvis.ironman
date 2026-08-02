import { AnimatePresence, motion } from 'framer-motion'
import { useStore } from '../store'

/**
 * The start gate.
 *
 * Browsers refuse to play audio or start speech synthesis until the user has
 * interacted with the page, so something has to be clicked before JARVIS can
 * make a sound. Rather than hide that behind a permissions banner, it's the
 * cold open: a dead interface waiting to be switched on.
 */
export function Ignition({ onStart }: { onStart: () => void }) {
  const phase = useStore((s) => s.phase)

  return (
    <AnimatePresence>
      {phase === 'offline' && (
        <motion.button
          className="ignition"
          onClick={onStart}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, filter: 'blur(12px)', transition: { duration: 0.8 } }}
        >
          <motion.span
            className="ignition-ring"
            animate={{ rotate: 360 }}
            transition={{ duration: 18, repeat: Infinity, ease: 'linear' }}
          />
          <span className="ignition-label">
            <span className="ignition-word">INITIALISE</span>
            <span className="ignition-sub">click to power up</span>
          </span>
        </motion.button>
      )}
    </AnimatePresence>
  )
}
