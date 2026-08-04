/**
 * Score.
 *
 * Three cues, all local files under public/audio/:
 *   boot-music — the JARVIS start-up sound, once, as the reactor comes up
 *   ambient    — the opening music, once, alongside it
 *   work       — an industrial cue that loops while a tool is running
 *
 * Only `work` repeats. The other two belong to the power-up and are over when
 * it is: an interface that keeps playing music at you for as long as it is open
 * is one you end up muting, and a muted assistant loses the sounds that
 * actually carry meaning — the wake tone, the tool tick, the completion chime.
 *
 * All of it is Kevin MacLeod (incompetech.com), CC BY 4.0 — free to use with
 * attribution and safe on a monetised channel, unlike the actual film score,
 * which would be claimed within a day of upload.
 *
 * Everything degrades quietly: if a file is missing the cue simply doesn't
 * play, and the synthesised bed in sfx.ts covers the ambient case.
 */

type Cue = 'boot-music' | 'ambient' | 'work'

type Track = {
  el: HTMLAudioElement
  fade: number | null
}

const tracks = new Map<Cue, Track>()
/** Cues whose file failed to load. Retrying only spends another 404. */
const missing = new Set<Cue>()
const ALL: Cue[] = ['boot-music', 'ambient', 'work']
let enabled = false

/** Resting levels. Music sits well under the voice — it is atmosphere, not a
 *  soundtrack, and JARVIS has to stay intelligible over it. */
const LEVEL: Record<Cue, number> = {
  // The boot cue is the JARVIS start-up sound itself, not background swell, so
  // it sits forward — it is meant to be heard as the reactor comes up, the way
  // the film plays it. The ambient bed underneath stays a whisper.
  'boot-music': 0.85,
  /**
   * Raised from the 0.075 it sat at as an all-session bed.
   *
   * That number was chosen for something you were never meant to notice, which
   * is the right level for a whisper running for an hour and the wrong one for
   * a piece that plays once and stops. Under a start-up sound at 0.85 it was
   * inaudible — technically playing, and no different from silence. This is
   * still clearly underneath, just actually there.
   */
  ambient: 0.2,
  work: 0.11,
}

/**
 * Where each cue currently wants to sit, before ducking. Kept separately from
 * the element volume so the two systems compose: a tool starting while JARVIS
 * is speaking brings the work cue in at its ducked level rather than at full,
 * and it rises the rest of the way when he stops.
 */
const want: Record<Cue, number> = { 'boot-music': 0, ambient: 0, work: 0 }

let ducked = false
/** How far the bed drops under the voice. */
const DUCK = 0.35

function track(cue: Cue): Track | null {
  if (!enabled || missing.has(cue)) return null
  let t = tracks.get(cue)
  if (!t) {
    const el = new Audio(`/audio/${cue}.mp3`)
    el.preload = 'auto'
    // Only the work cue repeats. It has to, because it covers an operation of
    // unknown length; the two power-up cues are events with an end.
    el.loop = cue === 'work'
    el.volume = 0
    // A missing file is not an error worth surfacing — the interface just
    // runs without that layer.
    el.addEventListener(
      'error',
      () => {
        tracks.delete(cue)
        missing.add(cue)
      },
      { once: true },
    )
    t = { el, fade: null }
    tracks.set(cue, t)
  }
  return t
}

/** Must be called from a user gesture — browsers block audio before one. */
export function enable() {
  enabled = true
  // Warm the files so the boot cue starts on time rather than after a buffer.
  ALL.forEach(track)
}

/**
 * The level a cue should actually be at right now. The boot swell is exempt
 * from ducking: it is a scripted one-shot with its own dissolve already
 * written, and pulling it down mid-flight reads as a fault rather than as
 * headroom being made.
 */
function level(cue: Cue): number {
  return ducked && cue !== 'boot-music' ? want[cue] * DUCK : want[cue]
}

function fadeTo(cue: Cue, to: number, ms: number) {
  const t = track(cue)
  if (!t) return
  if (t.fade !== null) cancelAnimationFrame(t.fade)
  const from = t.el.volume
  const start = performance.now()
  const step = () => {
    const k = Math.min(1, (performance.now() - start) / ms)
    t.el.volume = from + (to - from) * k
    if (k < 1) t.fade = requestAnimationFrame(step)
    else {
      t.fade = null
      if (to === 0) t.el.pause()
    }
  }
  if (to > 0 && t.el.paused) void t.el.play().catch(() => {})
  t.fade = requestAnimationFrame(step)
}

/** Set a cue's resting level and ramp to wherever that lands it. */
function set(cue: Cue, to: number, ms: number) {
  want[cue] = to
  fadeTo(cue, level(cue), ms)
}

/** The boot cue's own dissolve, held so stopAll can cancel it. */
let dissolve: ReturnType<typeof setTimeout> | null = null

/** The power-up swell. Plays once, then hands over to the ambient bed. */
export function playBoot() {
  const t = track('boot-music')
  if (!t) return
  t.el.currentTime = 0
  // In fast so the start-up sound lands with the first beat of the boot
  // sequence rather than easing in under it.
  set('boot-music', LEVEL['boot-music'], 120)
  /**
   * Dissolve near the end of whatever clip is actually there.
   *
   * This used to be a hardcoded fourteen seconds, measured off the clip that
   * happened to ship. Drop in a shorter one and the cue ends in silence long
   * before the fade starts; a longer one gets cut off mid-phrase. Reading the
   * duration means the boot sound is a file you can replace rather than a file
   * plus a constant somebody has to remember to change with it.
   */
  if (dissolve) clearTimeout(dissolve)
  const arm = () => {
    const secs = Number.isFinite(t.el.duration) && t.el.duration > 1 ? t.el.duration : 17
    // Start the fade far enough from the end that it is a dissolve rather than
    // a cut, and never sooner than half a second in.
    const at = Math.max(500, (secs - 2.6) * 1000)
    dissolve = setTimeout(() => {
      dissolve = null
      set('boot-music', 0, 2500)
    }, at)
  }
  if (t.el.readyState >= 1) arm()
  else t.el.addEventListener('loadedmetadata', arm, { once: true })
}

/**
 * The opening music. Once, from the top, and then it is finished.
 *
 * The four-second fade this used to have made sense for a bed that ran all
 * session — it had all the time in the world to arrive. For a cue that plays
 * once alongside the boot sequence it was spending a third of the track easing
 * in, so it is short now: present from the first beat, like the start-up sound
 * it plays under.
 *
 * Nothing stops it. The element does not loop, so it ends when the track ends.
 */
export function startAmbient() {
  const t = track('ambient')
  if (!t) return
  // From the top every time, so a second power-up in the same page sounds like
  // the first rather than resuming wherever the last one left off.
  t.el.currentTime = 0
  set('ambient', LEVEL.ambient, 900)
}

export function stopAll() {
  if (dissolve) {
    clearTimeout(dissolve)
    dissolve = null
  }
  ALL.forEach((c) => {
    want[c] = 0
    // Only touch cues that exist — asking for one that was never played would
    // otherwise construct an Audio element purely in order to silence it.
    if (tracks.has(c)) fadeTo(c, 0, 600)
  })
}

/** The work cue rises while a tool runs and falls the moment it's done. */
export function working(on: boolean) {
  set('work', on ? LEVEL.work : 0, on ? 900 : 1400)
}

/** Pull the bed down while JARVIS speaks so the voice stays clear. */
export function duck(on: boolean) {
  if (ducked === on) return
  ducked = on
  // Down quickly, back up slowly: the drop has to be out of the way before the
  // first syllable, but a fast recovery is audible as a swell.
  ;(['ambient', 'work'] as Cue[]).forEach((c) => {
    if (tracks.has(c)) fadeTo(c, level(c), on ? 250 : 900)
  })
}
