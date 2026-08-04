import { FilesetResolver, HandLandmarker } from '@mediapipe/tasks-vision'

/**
 * Hands.
 *
 * A reticle follows your index finger; pinching your thumb and finger together
 * presses. That is the whole interaction, and it is deliberately that small —
 * a gesture vocabulary you have to remember is a worse interface than a mouse,
 * and this one has exactly two words in it: where, and press.
 *
 * The important decision here is architectural rather than gestural. Nothing in
 * this file knows what a blade is. It does not know about dragging, resizing,
 * closing, or the header bar you drag by. It converts a hand into a position
 * and a press, and then dispatches ordinary PointerEvents at that position —
 * so every interaction the mouse already has works with the hand for free, and
 * anything added later works without being taught about hands. The alternative,
 * a gesture layer that hit-tests blades and calls their actions directly, is
 * the same code written twice and left to drift.
 *
 * Two consequences worth naming:
 *
 *   - The camera is off until you ask for it. An always-on webcam for an
 *     interface you use occasionally is a bad trade, and a visible indicator
 *     is the minimum honesty when one is running.
 *   - Nothing leaves the machine. The model runs locally on the GPU; frames are
 *     read and discarded, never uploaded, never recorded.
 */

/**
 * Served from our own origin, copied out of node_modules by scripts/start.mjs.
 *
 * Not a CDN, for two reasons that both bite. The runtime arrives as a script,
 * and the page's CSP names no CDN in `script-src` — so a CDN path is simply
 * blocked, and the symptom is gesture control that never starts with nothing
 * obviously wrong. And a CDN import is a live supply-chain dependency:
 * executable code, re-resolved every load, that we neither control nor can pin
 * against being changed underneath us. Local is the exact bytes of the version
 * in the lockfile.
 */
const WASM_BASE = '/mediapipe'
/**
 * The weights stay remote, and that is a different call from the runtime above.
 *
 * This is data, not code: it is fetched, so `connect-src` governs it rather
 * than `script-src`, and nothing in it executes. Seven megabytes is also not
 * worth vendoring for a feature most people will never turn on — the browser
 * caches it after the first use, exactly as the neural voice model is handled.
 */
const MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'

/** MediaPipe's landmark indices, named so the geometry below reads as intent. */
const WRIST = 0
const THUMB_TIP = 4
const INDEX_TIP = 8
const MIDDLE_MCP = 9

/**
 * Pinch thresholds, as a fraction of hand span rather than an absolute.
 *
 * The raw distance between two fingertips is meaningless on its own: it halves
 * when you lean back and doubles when you lean in, so a fixed threshold means
 * the interface works at one distance from the camera. Dividing by the span
 * from wrist to middle knuckle — a length that scales with the same
 * perspective — makes it a property of the hand's shape instead of its
 * distance, which is what a pinch actually is.
 *
 * Two thresholds, not one. A single threshold flickers on the boundary, and a
 * press that stutters is worse than one that is slightly late.
 */
const PINCH_ON = 0.42
const PINCH_OFF = 0.62

/**
 * How hard the position is smoothed. Hand tracking is jittery at rest — a still
 * finger moves several pixels a frame — and an unsmoothed reticle is unusable
 * for anything small. Higher is steadier and laggier.
 */
const SMOOTH = 0.35

/** Below this the hand is not confidently present; drop the reticle. */
const MIN_VISIBLE = 0.5

export type HandPointer = {
  id: number
  /** Viewport pixels. */
  x: number
  y: number
  pinched: boolean
  /** 0..1, how closed the pinch is — drives the reticle's tightening ring. */
  closeness: number
  handedness: string
}

/**
 * Live pointers, mutated in place.
 *
 * Deliberately not React state. This updates at camera rate and is read by a
 * component that positions two elements with a transform; routing it through
 * the store would re-render the entire HUD sixty times a second to move a
 * circle. The same reasoning as the scene's Drive object.
 */
export const pointers: HandPointer[] = []

export const diag = {
  enabled: false,
  loading: false,
  ready: false,
  hands: 0,
  fps: 0,
  lastError: '',
}

if (typeof window !== 'undefined') {
  ;(window as unknown as Record<string, unknown>).__hands = diag
}

let landmarker: HandLandmarker | null = null
let video: HTMLVideoElement | null = null
let stream: MediaStream | null = null
let running = false
let frames = 0
let fpsAt = 0

/* -------------------------------------------------------------- synthetics */

/**
 * setPointerCapture, made safe for pointers that do not exist.
 *
 * A synthetic PointerEvent carries a pointerId the browser has never issued, so
 * any element that calls setPointerCapture with it throws NotFoundError and the
 * interaction dies at the first move. That call is made by framer-motion's drag
 * and by our own resize grip — both of which we very much want the hand to be
 * able to use — and neither is somewhere we can add a try/catch.
 *
 * Capture is an optimisation, not a requirement: it exists so a drag keeps
 * receiving events after the cursor leaves the element. Our synthetic events
 * are dispatched by hit-testing every frame, so they land on the right element
 * whether or not capture was granted. Swallowing the failure costs nothing and
 * is what makes every existing mouse interaction work with a hand, unmodified.
 */
let patched = false
function patchPointerCapture() {
  if (patched || typeof Element === 'undefined') return
  patched = true
  const capture = Element.prototype.setPointerCapture
  const release = Element.prototype.releasePointerCapture
  Element.prototype.setPointerCapture = function (id: number) {
    try {
      return capture.call(this, id)
    } catch {
      /* a synthetic pointer; hit-testing covers what capture would have */
    }
  }
  Element.prototype.releasePointerCapture = function (id: number) {
    try {
      return release.call(this, id)
    } catch {
      /* as above */
    }
  }
}

/** The element a pointer is over, ignoring the reticle itself. */
function targetAt(x: number, y: number): Element | null {
  return document.elementFromPoint(x, y)
}

type Synth = {
  /** Where the press began, so a press and its release agree on their target. */
  captured: Element | null
  wasPinched: boolean
  lastX: number
  lastY: number
}

const synth = new Map<number, Synth>()

function fire(el: Element | null, type: string, p: HandPointer, extra: PointerEventInit = {}) {
  if (!el) return
  el.dispatchEvent(
    new PointerEvent(type, {
      bubbles: true,
      cancelable: true,
      composed: true,
      clientX: p.x,
      clientY: p.y,
      // Offset by a wide margin from any real pointer id the browser might use.
      pointerId: 9000 + p.id,
      pointerType: 'touch',
      isPrimary: p.id === 0,
      button: 0,
      buttons: p.pinched ? 1 : 0,
      ...extra,
    }),
  )
}

/**
 * Turn a pointer's frame into events.
 *
 * Ordinary pointerdown / pointermove / pointerup, plus the click that a real
 * press would synthesise, so a button responds to a pinch exactly as it does
 * to a tap.
 */
function emit(p: HandPointer) {
  let s = synth.get(p.id)
  if (!s) {
    s = { captured: null, wasPinched: false, lastX: p.x, lastY: p.y }
    synth.set(p.id, s)
  }

  const over = targetAt(p.x, p.y)

  if (p.pinched && !s.wasPinched) {
    s.captured = over
    fire(over, 'pointerdown', p)
  } else if (!p.pinched && s.wasPinched) {
    fire(s.captured ?? over, 'pointerup', p)
    // Only a press that ends roughly where it began is a click; one that
    // travelled was a drag, and a drag that also clicks would close the very
    // blade it was moving.
    const travelled = Math.hypot(p.x - s.lastX, p.y - s.lastY)
    if (s.captured && travelled < 18 && s.captured === over) {
      over?.dispatchEvent(
        new MouseEvent('click', { bubbles: true, cancelable: true, composed: true, clientX: p.x, clientY: p.y }),
      )
    }
    s.captured = null
  } else {
    // Moves go to whatever holds the press, so a drag survives the reticle
    // sliding off the header it grabbed.
    fire(p.pinched ? (s.captured ?? over) : over, 'pointermove', p)
  }

  if (!s.wasPinched && p.pinched) {
    s.lastX = p.x
    s.lastY = p.y
  }
  s.wasPinched = p.pinched
}

/** A press that is still held when tracking drops has to be let go, or the
 *  thing being dragged stays stuck to a hand that is no longer there. */
function releaseAll() {
  for (const [id, s] of synth) {
    if (!s.wasPinched) continue
    const ghost: HandPointer = {
      id,
      x: s.lastX,
      y: s.lastY,
      pinched: false,
      closeness: 0,
      handedness: '',
    }
    fire(s.captured, 'pointerup', ghost)
    fire(s.captured, 'pointercancel', ghost)
    s.wasPinched = false
    s.captured = null
  }
}

/* ------------------------------------------------------------------ camera */

async function ensureModel() {
  if (landmarker) return landmarker
  diag.loading = true
  try {
    const vision = await FilesetResolver.forVisionTasks(WASM_BASE)
    landmarker = await HandLandmarker.createFromOptions(vision, {
      baseOptions: { modelAssetPath: MODEL_URL, delegate: 'GPU' },
      runningMode: 'VIDEO',
      numHands: 2,
      minHandDetectionConfidence: 0.5,
      minHandPresenceConfidence: 0.5,
      minTrackingConfidence: 0.5,
    })
    diag.ready = true
    return landmarker
  } finally {
    diag.loading = false
  }
}

/**
 * The tracking loop.
 *
 * Driven by requestVideoFrameCallback rather than requestAnimationFrame: rAF
 * runs on the display's clock and will happily hand the same camera frame to
 * the model several times, burning GPU on work whose answer cannot have
 * changed. This fires once per actual frame.
 */
function loop() {
  if (!running || !video || !landmarker) return
  const now = performance.now()

  let result
  try {
    result = landmarker.detectForVideo(video, now)
  } catch (err) {
    diag.lastError = String((err as Error)?.message ?? err)
    result = null
  }

  const w = window.innerWidth
  const h = window.innerHeight
  const found = result?.landmarks ?? []
  diag.hands = found.length

  for (let i = 0; i < 2; i++) {
    const marks = found[i]
    if (!marks) {
      const stale = pointers.findIndex((p) => p.id === i)
      if (stale !== -1) {
        // Let go before the reticle disappears, or whatever it was holding
        // stays held for ever.
        const p = pointers[stale]
        if (p.pinched) {
          p.pinched = false
          emit(p)
        }
        pointers.splice(stale, 1)
      }
      continue
    }

    const tip = marks[INDEX_TIP]
    const thumb = marks[THUMB_TIP]
    const wrist = marks[WRIST]
    const knuckle = marks[MIDDLE_MCP]
    if (!tip || !thumb || !wrist || !knuckle) continue
    if ((tip.visibility ?? 1) < MIN_VISIBLE && (tip.visibility ?? 1) !== 0) continue

    // Mirrored, because the camera faces you: moving your hand right should
    // move the reticle right, not left.
    const x = (1 - tip.x) * w
    const y = tip.y * h

    const span = Math.hypot(knuckle.x - wrist.x, knuckle.y - wrist.y) || 0.0001
    const gap = Math.hypot(thumb.x - tip.x, thumb.y - tip.y) / span

    let p = pointers.find((q) => q.id === i)
    if (!p) {
      p = { id: i, x, y, pinched: false, closeness: 0, handedness: '' }
      pointers.push(p)
    } else {
      p.x += (x - p.x) * SMOOTH
      p.y += (y - p.y) * SMOOTH
    }

    p.handedness = result?.handedness?.[i]?.[0]?.categoryName ?? ''
    p.closeness = Math.max(0, Math.min(1, 1 - (gap - PINCH_ON) / (PINCH_OFF - PINCH_ON)))
    // Hysteresis: it takes a tighter pinch to press than to keep pressing.
    p.pinched = p.pinched ? gap < PINCH_OFF : gap < PINCH_ON

    emit(p)
  }

  frames++
  if (now - fpsAt > 1000) {
    diag.fps = Math.round((frames * 1000) / (now - fpsAt))
    frames = 0
    fpsAt = now
  }

  video.requestVideoFrameCallback(loop)
}

/** Turn the camera on and start tracking. Safe to call twice. */
export async function enableHands(): Promise<void> {
  if (running) return
  patchPointerCapture()
  try {
    // Video only. The microphone is opened elsewhere and shared; asking for it
    // again here would make Chrome drop the existing capture.
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: 'user' },
    })
    await ensureModel()

    video = document.createElement('video')
    video.autoplay = true
    video.playsInline = true
    video.muted = true
    video.srcObject = stream
    await video.play()

    running = true
    diag.enabled = true
    diag.lastError = ''
    fpsAt = performance.now()
    video.requestVideoFrameCallback(loop)
  } catch (err) {
    diag.lastError = String((err as Error)?.message ?? err)
    disableHands()
    throw err
  }
}

/** Camera off, tracking stopped, anything held released. */
export function disableHands(): void {
  running = false
  diag.enabled = false
  diag.hands = 0
  diag.fps = 0
  releaseAll()
  pointers.length = 0
  synth.clear()
  if (video) {
    video.pause()
    video.srcObject = null
    video = null
  }
  // Stopping every track is what actually extinguishes the camera light. Left
  // running, the indicator stays on and the user is right to distrust it.
  stream?.getTracks().forEach((t) => t.stop())
  stream = null
}

export const handsRunning = () => running
