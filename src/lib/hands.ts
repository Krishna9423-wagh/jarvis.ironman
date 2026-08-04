import { FilesetResolver, HandLandmarker } from '@mediapipe/tasks-vision'
import { OneEuroPoint } from './oneEuro'

/**
 * Hands.
 *
 * Your hand appears on screen as a skeleton — every joint, every finger — and
 * the tip of your index finger is the cursor. Pinch thumb to finger to press.
 *
 * Drawing the whole hand rather than a floating dot is not decoration. You
 * cannot see your own hand against the screen, so with only a dot you are
 * aiming something whose orientation and shape you have to infer. With the
 * skeleton you can see the pinch closing before it fires, see which finger the
 * cursor is riding on, and see immediately when tracking has lost you rather
 * than wondering why nothing responds.
 *
 * The architectural decision is that nothing here knows what a blade is. No
 * hit-testing of blades, no calls to close or move them, no knowledge of the
 * header you drag by. It turns a hand into a position and a press and
 * dispatches ordinary PointerEvents there — so every interaction the mouse
 * already has works with a hand for free, and anything added later works
 * without being taught that hands exist.
 *
 * The camera is off until you ask for it, says so on screen the whole time it
 * is on, and nothing leaves the machine: the model runs locally on the GPU and
 * frames are read and discarded.
 */

/**
 * Served from our own origin, copied out of node_modules by scripts/start.mjs.
 *
 * Not a CDN, for two reasons that both bite. The runtime arrives as a script
 * and the page's CSP names no CDN in `script-src` — so a CDN path is simply
 * blocked, and the symptom is gesture control that never starts with nothing
 * obviously wrong. And a CDN import is a live supply-chain dependency:
 * executable code, re-resolved every load, that we neither control nor can pin
 * against being changed underneath us.
 */
const WASM_BASE = '/mediapipe'

/**
 * The weights stay remote, and that is a different call from the runtime above.
 * This is data, not code: it is fetched, so `connect-src` governs it rather
 * than `script-src`, and nothing in it executes. The browser caches it after
 * first use, exactly as the neural voice model is handled.
 */
const MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'

/* ------------------------------------------------------------------ anatomy */

export const WRIST = 0
const THUMB_MCP = 2
export const THUMB_TIP = 4
const INDEX_PIP = 6
export const INDEX_TIP = 8
const MIDDLE_MCP = 9
const MIDDLE_PIP = 10
const MIDDLE_TIP = 12
const RING_PIP = 14
const RING_TIP = 16
const PINKY_PIP = 18
const PINKY_TIP = 20

/**
 * The skeleton, as pairs of landmark indices.
 *
 * Written out rather than taken from HandLandmarker.HAND_CONNECTIONS so the
 * renderer does not depend on a static that the library is free to reshape, and
 * so the palm arch below reads as a deliberate choice.
 */
export const BONES: readonly [number, number][] = [
  // thumb
  [0, 1], [1, 2], [2, 3], [3, 4],
  // index
  [0, 5], [5, 6], [6, 7], [7, 8],
  // middle
  [9, 10], [10, 11], [11, 12],
  // ring
  [13, 14], [14, 15], [15, 16],
  // pinky
  [0, 17], [17, 18], [18, 19], [19, 20],
  // the arch across the knuckles, which is what makes it read as a hand
  // rather than as five separate sticks
  [5, 9], [9, 13], [13, 17],
]

export const TIPS = [THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]

/* -------------------------------------------------------------------- tuning */

/**
 * 1€ filter constants, tuned by the published method: beta at zero, drop
 * minCutoff until a resting hand stops shivering, then raise beta until a fast
 * movement stops trailing.
 *
 * The cursor is filtered harder than the skeleton. Aiming is a precision task
 * and benefits from every bit of steadiness; the skeleton is a picture of your
 * hand and only has to look alive, so it is allowed to be looser and more
 * responsive. Filtering both identically made the drawing feel dead.
 */
const CURSOR_MIN_CUTOFF = 1.1
const CURSOR_BETA = 0.012
const SKELETON_MIN_CUTOFF = 2.4
const SKELETON_BETA = 0.02

/**
 * Pinch thresholds, as a fraction of hand span rather than an absolute.
 *
 * The raw gap between two fingertips is meaningless alone: it halves when you
 * lean back and doubles when you lean in, so a fixed threshold means the
 * interface only works at one distance from the camera. Dividing by the span
 * from wrist to middle knuckle — a length that shrinks with the same
 * perspective — makes it a property of the hand's shape rather than its
 * distance, which is what a pinch actually is.
 *
 * Two thresholds, not one: it takes a tighter pinch to start a press than to
 * keep one, so the press cannot flicker on the boundary.
 */
const PINCH_ON = 0.40
const PINCH_OFF = 0.60

/** A finger counts as extended when its tip is this much further from the
 *  wrist than its middle joint. Ratio rather than a y-comparison, so it still
 *  works with your hand rotated or upside down. */
const EXTEND_RATIO = 1.12

/**
 * A gesture must hold for this long before it counts.
 *
 * Fingers pass through other shapes on the way to the one you meant — a fist
 * becomes a point by way of several ambiguous frames — and acting on those
 * intermediate readings is what makes gesture interfaces feel possessed.
 */
const GESTURE_HOLD_MS = 120

/** Below this many pixels of travel, a press was a click rather than a drag. */
const CLICK_SLOP = 20

export type Gesture = 'point' | 'pinch' | 'open' | 'fist' | 'peace' | 'none'

export type Hand = {
  id: number
  /** Every joint, in viewport pixels, smoothed and mirrored. */
  points: { x: number; y: number }[]
  /** Cursor position — the index tip, or the pinch point while pinching. */
  x: number
  y: number
  pinched: boolean
  /** 0..1, how closed the pinch is. Drives the reticle's tightening ring. */
  closeness: number
  gesture: Gesture
  fingers: { thumb: boolean; index: boolean; middle: boolean; ring: boolean; pinky: boolean }
  handedness: string
  /** Rough hand size in pixels, so the renderer can scale line weight to it. */
  span: number
}

/**
 * Live hands, mutated in place.
 *
 * Deliberately not React state. This updates at camera rate and is consumed by
 * a canvas that redraws itself; routing it through the store would re-render
 * the entire HUD sixty times a second to move some lines. Same reasoning as the
 * scene's Drive object.
 */
export const hands: Hand[] = []

export const diag = {
  enabled: false,
  loading: false,
  ready: false,
  count: 0,
  fps: 0,
  gesture: '' as string,
  lastError: '',
}

if (typeof window !== 'undefined') {
  ;(window as unknown as Record<string, unknown>).__hands = diag
}

let landmarker: HandLandmarker | null = null
let video: HTMLVideoElement | null = null
let stream: MediaStream | null = null
let running = false
/** Bumped on every enable, so a loop from a previous session stops itself. */
let generation = 0
let frames = 0
let fpsAt = 0
/** detectForVideo rejects a timestamp that does not advance, and performance.now()
 *  restarts its relationship with the model on every enable. Keep our own. */
let stamp = 0

/* ------------------------------------------------------------------ filters */

type Filters = {
  cursor: OneEuroPoint
  joints: OneEuroPoint[]
}

const filters = new Map<number, Filters>()

function filtersFor(id: number): Filters {
  let f = filters.get(id)
  if (!f) {
    f = {
      cursor: new OneEuroPoint(CURSOR_MIN_CUTOFF, CURSOR_BETA),
      joints: Array.from({ length: 21 }, () => new OneEuroPoint(SKELETON_MIN_CUTOFF, SKELETON_BETA)),
    }
    filters.set(id, f)
  }
  return f
}

/* ---------------------------------------------------------------- synthetics */

/**
 * setPointerCapture, made safe for pointers that do not exist.
 *
 * A synthetic PointerEvent carries a pointerId the browser has never issued, so
 * any element that calls setPointerCapture with it throws NotFoundError and the
 * interaction dies at the first move. That call is made by framer-motion's drag
 * and by our own resize grip — both of which we very much want a hand to be
 * able to use — and neither is somewhere we can add a try/catch.
 *
 * Capture is an optimisation, not a requirement: it exists so a drag keeps
 * receiving events after the cursor leaves the element. Our events are aimed by
 * hit-testing every frame and routed to the element that took the press, so
 * they land correctly whether or not capture was granted.
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

type Press = {
  /** What took the press, so the release and any click agree on their target. */
  captured: Element | null
  wasPinched: boolean
  /** Where the press began — for telling a click from a drag. */
  downX: number
  downY: number
}

const presses = new Map<number, Press>()

function fire(el: Element | null, type: string, h: Hand, pressed: boolean) {
  if (!el) return
  el.dispatchEvent(
    new PointerEvent(type, {
      bubbles: true,
      cancelable: true,
      composed: true,
      clientX: h.x,
      clientY: h.y,
      // Well clear of any id the browser might issue for a real pointer.
      pointerId: 9000 + h.id,
      pointerType: 'touch',
      isPrimary: h.id === 0,
      button: 0,
      buttons: pressed ? 1 : 0,
      width: 1,
      height: 1,
      pressure: pressed ? 0.5 : 0,
    }),
  )
}

function emit(h: Hand) {
  let p = presses.get(h.id)
  if (!p) {
    p = { captured: null, wasPinched: false, downX: h.x, downY: h.y }
    presses.set(h.id, p)
  }

  const over = document.elementFromPoint(h.x, h.y)

  if (h.pinched && !p.wasPinched) {
    // Press. Record where it began BEFORE anything moves, which is what makes
    // the click-versus-drag test below mean anything.
    p.captured = over
    p.downX = h.x
    p.downY = h.y
    fire(over, 'pointerdown', h, true)
  } else if (!h.pinched && p.wasPinched) {
    const target = p.captured ?? over
    fire(target, 'pointerup', h, false)
    // Only a press that ends roughly where it began is a click. One that
    // travelled was a drag, and a drag that also clicked would close the very
    // blade it had just finished moving.
    const travelled = Math.hypot(h.x - p.downX, h.y - p.downY)
    if (target && travelled < CLICK_SLOP && target === over) {
      target.dispatchEvent(
        new MouseEvent('click', {
          bubbles: true,
          cancelable: true,
          composed: true,
          clientX: h.x,
          clientY: h.y,
        }),
      )
    }
    p.captured = null
  } else {
    // While pressed, moves go to whatever took the press, so a drag survives
    // the cursor sliding off the header it grabbed.
    fire(h.pinched ? (p.captured ?? over) : over, 'pointermove', h, h.pinched)
  }

  p.wasPinched = h.pinched
}

/** Let go of anything still held. A press that outlives its hand leaves
 *  whatever was being dragged stuck to a cursor that no longer exists. */
function releasePress(id: number, at: { x: number; y: number }) {
  const p = presses.get(id)
  if (!p?.wasPinched) return
  const ghost = { id, x: at.x, y: at.y } as Hand
  fire(p.captured, 'pointerup', ghost, false)
  fire(p.captured, 'pointercancel', ghost, false)
  p.wasPinched = false
  p.captured = null
}

/* ------------------------------------------------------------------ geometry */

const dist = (a: { x: number; y: number }, b: { x: number; y: number }) =>
  Math.hypot(a.x - b.x, a.y - b.y)

/**
 * Is this finger extended?
 *
 * Compared as distance from the wrist rather than by which landmark is higher
 * on screen. The y-comparison is the common recipe and it is wrong the moment
 * the hand is not upright: turn your hand sideways and every finger reads as
 * curled. Distance from the wrist is rotation-invariant, which is the property
 * the question actually needs.
 */
function isExtended(
  marks: { x: number; y: number }[],
  tip: number,
  pip: number,
): boolean {
  const wrist = marks[WRIST]
  return dist(marks[tip], wrist) > dist(marks[pip], wrist) * EXTEND_RATIO
}

/**
 * Only report a finger pose once it has held.
 *
 * Fingers pass through other shapes on the way to the one you meant: a fist
 * opening into a point spends several frames looking like a pinch, and a hand
 * relaxing looks briefly like every gesture in the list. Acting on those
 * intermediate readings is exactly what makes gesture interfaces feel
 * possessed, so a pose has to survive GESTURE_HOLD_MS before it is believed.
 *
 * A pinch is deliberately exempt. It already carries its own hysteresis, and
 * it is the one gesture where the delay would be felt directly — as a press
 * that lands late.
 */
const settling = new Map<number, { raw: Gesture; since: number; held: Gesture }>()

function stableGesture(id: number, raw: Gesture, now: number): Gesture {
  if (raw === 'pinch') {
    settling.set(id, { raw, since: now, held: raw })
    return raw
  }
  const s = settling.get(id)
  if (!s || s.raw !== raw) {
    settling.set(id, { raw, since: now, held: s?.held === 'pinch' ? 'none' : (s?.held ?? 'none') })
    return settling.get(id)!.held
  }
  if (now - s.since >= GESTURE_HOLD_MS) s.held = raw
  return s.held
}

function classify(
  fingers: Hand['fingers'],
  pinched: boolean,
): Gesture {
  if (pinched) return 'pinch'
  const { thumb, index, middle, ring, pinky } = fingers
  const up = [thumb, index, middle, ring, pinky].filter(Boolean).length
  if (index && middle && !ring && !pinky) return 'peace'
  if (index && !middle && !ring && !pinky) return 'point'
  if (up >= 4) return 'open'
  if (up === 0) return 'fist'
  return 'none'
}

/* -------------------------------------------------------------------- camera */

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
  } catch (err) {
    // A machine with no working GPU delegate should still get hands rather than
    // an error — the CPU path is slower but perfectly usable at this frame size.
    diag.lastError = `GPU delegate failed (${(err as Error)?.message ?? err}); retrying on CPU`
    const vision = await FilesetResolver.forVisionTasks(WASM_BASE)
    landmarker = await HandLandmarker.createFromOptions(vision, {
      baseOptions: { modelAssetPath: MODEL_URL, delegate: 'CPU' },
      runningMode: 'VIDEO',
      numHands: 2,
    })
    diag.ready = true
    return landmarker
  } finally {
    diag.loading = false
  }
}

function dropHand(i: number) {
  const at = hands.findIndex((h) => h.id === i)
  if (at === -1) return
  releasePress(i, hands[at])
  hands.splice(at, 1)
  filters.get(i)?.cursor.reset()
  filters.get(i)?.joints.forEach((f) => f.reset())
  settling.delete(i)
}

/**
 * The tracking loop.
 *
 * Driven by requestVideoFrameCallback where it exists: rAF runs on the
 * display's clock and will happily hand the same camera frame to the model
 * several times, burning GPU on work whose answer cannot have changed. Falls
 * back to rAF on browsers that lack it, where the only cost is some wasted
 * inference.
 */
function loop(mine: number) {
  if (!running || mine !== generation || !video || !landmarker) return

  const now = performance.now()
  // Strictly increasing, and independent of performance.now(): the model
  // rejects a timestamp that does not advance, and enable/disable cycles would
  // otherwise hand it the same clock twice.
  stamp += 1

  let result
  try {
    result = landmarker.detectForVideo(video, stamp)
  } catch (err) {
    diag.lastError = String((err as Error)?.message ?? err)
    result = null
  }

  const w = window.innerWidth
  const h = window.innerHeight
  const found = result?.landmarks ?? []
  diag.count = found.length
  const at = now / 1000

  for (let i = 0; i < 2; i++) {
    const marks = found[i]
    if (!marks || marks.length < 21) {
      dropHand(i)
      continue
    }

    const f = filtersFor(i)

    // Mirrored, because the camera faces you: moving your hand right should
    // move the cursor right, not left.
    const points = marks.map((m, j) =>
      f.joints[j].filter((1 - m.x) * w, m.y * h, at),
    )

    const span = dist(points[WRIST], points[MIDDLE_MCP]) || 1
    const gap = dist(points[THUMB_TIP], points[INDEX_TIP]) / span

    let hand = hands.find((q) => q.id === i)
    if (!hand) {
      hand = {
        id: i, points, x: points[INDEX_TIP].x, y: points[INDEX_TIP].y,
        pinched: false, closeness: 0, gesture: 'none',
        fingers: { thumb: false, index: false, middle: false, ring: false, pinky: false },
        handedness: '', span,
      }
      hands.push(hand)
    }
    hand.points = points
    hand.span = span

    // Hysteresis: a tighter pinch to start than to hold.
    const pinched = hand.pinched ? gap < PINCH_OFF : gap < PINCH_ON
    hand.closeness = Math.max(0, Math.min(1, 1 - (gap - PINCH_ON) / (PINCH_OFF - PINCH_ON)))

    /**
     * Where the cursor sits.
     *
     * The index tip when open, but the midpoint between thumb and finger once
     * you start closing — because that is the point you are actually aiming
     * when you pinch, and letting the cursor drift to the fingertip as the
     * fingers meet makes every press land slightly off from where it was aimed.
     * Blended by closeness so it moves there smoothly rather than jumping.
     */
    const tip = points[INDEX_TIP]
    const thumb = points[THUMB_TIP]
    const k = hand.closeness
    const aimed = f.cursor.filter(
      tip.x + (thumb.x - tip.x) * 0.5 * k,
      tip.y + (thumb.y - tip.y) * 0.5 * k,
      at,
    )
    hand.x = aimed.x
    hand.y = aimed.y
    hand.pinched = pinched

    hand.fingers = {
      // The thumb never straightens the way the fingers do, so it is measured
      // against its own base joint rather than by the same ratio.
      thumb: dist(points[THUMB_TIP], points[WRIST]) > dist(points[THUMB_MCP], points[WRIST]) * 1.35
        || dist(points[THUMB_TIP], points[INDEX_PIP]) > span * 1.1,
      index: isExtended(points, INDEX_TIP, INDEX_PIP),
      middle: isExtended(points, MIDDLE_TIP, MIDDLE_PIP),
      ring: isExtended(points, RING_TIP, RING_PIP),
      pinky: isExtended(points, PINKY_TIP, PINKY_PIP),
    }
    hand.gesture = stableGesture(i, classify(hand.fingers, pinched), now)
    hand.handedness = result?.handedness?.[i]?.[0]?.categoryName ?? ''

    emit(hand)
  }

  diag.gesture = hands.map((q) => q.gesture).join(' + ')

  frames++
  if (now - fpsAt > 1000) {
    diag.fps = Math.round((frames * 1000) / (now - fpsAt))
    frames = 0
    fpsAt = now
  }

  schedule(mine)
}

function schedule(mine: number) {
  if (!video) return
  if (typeof video.requestVideoFrameCallback === 'function') {
    video.requestVideoFrameCallback(() => loop(mine))
  } else {
    requestAnimationFrame(() => loop(mine))
  }
}

/** Turn the camera on and start tracking. Safe to call twice. */
export async function enableHands(): Promise<void> {
  if (running) return
  patchPointerCapture()
  const mine = ++generation
  try {
    // Video only. The microphone is opened elsewhere and shared; asking for it
    // again here would make Chrome drop the existing capture.
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 960, height: 540, facingMode: 'user', frameRate: { ideal: 60 } },
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
    fpsAt = performance.now()
    schedule(mine)
  } catch (err) {
    diag.lastError = String((err as Error)?.message ?? err)
    disableHands()
    throw err
  }
}

/** Camera off, tracking stopped, anything held released. */
export function disableHands(): void {
  running = false
  generation++
  diag.enabled = false
  diag.count = 0
  diag.fps = 0
  diag.gesture = ''
  for (const h of hands) releasePress(h.id, h)
  hands.length = 0
  presses.clear()
  filters.clear()
  settling.clear()
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
