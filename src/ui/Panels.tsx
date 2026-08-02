import { memo, useEffect, useMemo, useRef } from 'react'
import { AnimatePresence, motion, type Variants } from 'framer-motion'
import DOMPurify from 'dompurify'
import { useStore, type Panel } from '../store'
import { BRIDGE_HTTP_URL } from '../config'

/**
 * Heads-up display panels.
 *
 * The markup inside each panel is written by JARVIS, not by this file — he
 * composes the layout for whatever he's showing and picks how it arrives. What
 * lives here is the frame, the safety boundary, and the motion vocabulary.
 */


/**
 * Paths that are genuinely on this machine's disk, as opposed to app-relative
 * URLs that happen to start with a slash. `/vite.svg` is one of our own static
 * assets; `/Users/you/shot.png` is a screenshot JARVIS just took.
 */
const DISK_PATH =
  /^\/(Users|home|root|Volumes|Applications|System|Library|private|tmp|var|opt|mnt|media|srv|data)\//

/**
 * Every media URL in a panel is rewritten to point at the bridge. There are two
 * destinations and they exist for different reasons.
 *
 * `/file` — a page served over http can't load `file:///…`, and the interesting
 * images (phone screenshots, generated art) land on disk as absolute paths.
 *
 * Only real disk paths qualify. Rewriting every src beginning with a slash also
 * caught the app's own assets, so `<img src="/vite.svg">` turned into a
 * readFileSync of `/vite.svg` on the host, 404'd, and rendered as the
 * 'image unavailable' caption.
 *
 * `/img` and `/media` — remote http(s) sources, which used to be refused
 * outright and are now proxied instead. The browser still only ever talks to
 * localhost, which is what lets the page CSP stay closed and stops markup that
 * summarises an untrusted web page from beaconing this machine's address to a
 * host the model was told to use. It also gets the bytes at all: news sites and
 * image CDNs routinely block hotlinking, which is why remote thumbnails
 * rendered as blank rectangles even before the sanitiser started refusing them.
 *
 * data:, blob: and app-relative URLs are left exactly as they are — nothing
 * leaves the page for those, so there is nothing to proxy.
 */
function rewriteSrc(el: Element, attr: 'src' | 'poster', route: 'img' | 'media') {
  const raw = el.getAttribute(attr) ?? ''
  if (!raw) return

  const path = raw.replace(/^file:\/\//, '')
  if (DISK_PATH.test(path)) {
    el.setAttribute(attr, `${BRIDGE_HTTP_URL}/file?path=${encodeURIComponent(path)}`)
    return
  }

  if (!/^https?:\/\//i.test(raw)) return
  // Already ours. Proxying the proxy would ask the bridge to fetch itself.
  if (raw.startsWith(`${BRIDGE_HTTP_URL}/`)) return
  el.setAttribute(attr, `${BRIDGE_HTTP_URL}/${route}?url=${encodeURIComponent(raw)}`)
}

function rewriteMedia(root: Element) {
  root.querySelectorAll('img').forEach((img) => rewriteSrc(img, 'src', 'img'))
  root.querySelectorAll('video').forEach((video) => {
    rewriteSrc(video, 'src', 'media')
    // The poster is a still, so it goes down the image route and gets the image
    // route's tighter size cap and content-type check.
    rewriteSrc(video, 'poster', 'img')
  })
  // A <source> is only reachable inside <video> here, but its `type` is the
  // model's own declaration of what it is — honour it, so an image-typed source
  // isn't sent to an endpoint that will refuse it for having the wrong
  // content-type.
  root.querySelectorAll('source').forEach((source) => {
    const type = source.getAttribute('type') ?? ''
    rewriteSrc(source, 'src', /^image\//i.test(type) ? 'img' : 'media')
  })
}

/**
 * The only iframe destinations that exist. An iframe is the one way to play a
 * YouTube or Vimeo result inline — they will not hand over the media file — so
 * these three load direct rather than through the proxy, and the trade is that
 * the host list is closed and the paths are pinned. Everything else is removed
 * outright; there is no proxying an embed and no unknown host worth framing.
 */
const EMBED_HOSTS: Record<string, RegExp> = {
  'www.youtube-nocookie.com': /^\/embed\/[\w-]+/,
  'www.youtube.com': /^\/embed\/[\w-]+/,
  'player.vimeo.com': /^\/video\/\d+/,
}

/** Eleven characters in practice; bounded rather than exact, in case that moves. */
const YT_ID = /^[\w-]{6,20}$/

/**
 * Search results hand back `youtube.com/watch?v=ID` and `youtu.be/ID`, so that
 * is what the model writes. Rejecting those would mean showing nothing, which
 * is precisely the failure this whole change exists to fix — rewrite them into
 * the cookieless embed form instead.
 */
function toEmbedUrl(url: URL): URL | null {
  const host = url.hostname.toLowerCase().replace(/^(?:www|m|music)\./, '')
  let id = ''
  if (host === 'youtube.com' && url.pathname === '/watch') id = url.searchParams.get('v') ?? ''
  else if (host === 'youtu.be') id = url.pathname.slice(1)
  if (!YT_ID.test(id)) return null
  return new URL(`https://www.youtube-nocookie.com/embed/${id}`)
}

function rewriteEmbeds(root: Element) {
  root.querySelectorAll('iframe').forEach((frame) => {
    let url: URL
    try {
      // Resolved against the page so a relative or protocol-relative src can't
      // slip past the host test by never being parsed at all. A relative one
      // resolves to this origin, which is not on the list, so it is dropped.
      url = new URL(frame.getAttribute('src') ?? '', document.baseURI)
    } catch {
      frame.remove()
      return
    }
    const embed = toEmbedUrl(url) ?? url
    const path = EMBED_HOSTS[embed.hostname.toLowerCase()]
    if (!path || !path.test(embed.pathname)) {
      frame.remove()
      return
    }
    // Pinned rather than merely permitted: the host is known-good, so an http
    // embed is upgraded instead of dropped.
    embed.protocol = 'https:'
    frame.setAttribute('src', embed.toString())
  })
}

/**
 * Powerful features an embed may ask for. Everything a video player needs and
 * nothing that reaches the room the user is sitting in: `camera`, `microphone`,
 * `geolocation` and `display-capture` are the interesting omissions. The host
 * is allowlisted, but the `allow` attribute is written by the model, and a
 * panel summarising a hostile page should not be able to hand a frame the
 * webcam — even one YouTube would never use, because the permission prompt
 * alone is the attack.
 */
const EMBED_FEATURES = new Set([
  'accelerometer', 'autoplay', 'clipboard-write', 'encrypted-media',
  'fullscreen', 'gyroscope', 'picture-in-picture', 'web-share',
])

/**
 * Attributes the model is not required to remember, and one it is not trusted
 * to choose.
 *
 * `referrerpolicy` because a proxied fetch already hides the user from the
 * origin server, and the embed hosts have no business being told which page
 * framed them either.
 *
 * The three video attributes because a <video> without `controls` is a still
 * frame the user cannot start, and on iOS one without `playsinline` hijacks the
 * whole screen the moment it plays. `preload="metadata"` keeps a panel with
 * several clips on it from pulling megabytes nobody asked for.
 */
function hardenMedia(root: Element) {
  root.querySelectorAll('img, video, iframe').forEach((el) => {
    el.setAttribute('referrerpolicy', 'no-referrer')
  })

  root.querySelectorAll('video').forEach((video) => {
    video.setAttribute('controls', '')
    video.setAttribute('preload', 'metadata')
    video.setAttribute('playsinline', '')
  })

  root.querySelectorAll('iframe[allow]').forEach((frame) => {
    // Each entry is a feature name optionally followed by an origin list. The
    // name is kept and the origin list dropped, which leaves the feature scoped
    // to the frame's own origin — the default, and the only one wanted here.
    const kept = (frame.getAttribute('allow') ?? '')
      .split(';')
      .map((part) => part.trim().split(/\s+/)[0].toLowerCase())
      .filter((feature) => EMBED_FEATURES.has(feature))
    if (kept.length) frame.setAttribute('allow', kept.join('; '))
    else frame.removeAttribute('allow')
  })
}

/**
 * The whole design-system vocabulary, and the only class names allowed to
 * survive. This has to be an allowlist rather than a `hud-` prefix test, and it
 * has to exist at all: `class` carries no URI, so DOMPurify never looks at its
 * value, and this stylesheet contains full-screen classes — `.ignition` and
 * `.boot` are both position:fixed, inset:0, opaque, above everything — so one
 * stray class token in model output blacks out the entire interface.
 *
 * Kept in step with the list in the `display` tool description
 * (bridge/panels.mjs). A name there that is missing here is silently stripped,
 * which is the failure mode we want but not one the model can diagnose.
 */
const ALLOWED_CLASSES = new Set([
  'hud-rows', 'hud-row', 'hud-idx', 'hud-main', 'hud-label', 'hud-sub',
  'hud-tag', 'hud-metric', 'hud-unit', 'hud-note', 'hud-img', 'hud-caption',
  'hud-grid', 'hud-bar', 'hud-dim', 'hud-hot',
  'hud-gallery', 'hud-thumb', 'hud-video', 'hud-embed', 'hud-figure',
])

function narrowClasses(root: Element) {
  root.querySelectorAll('[class]').forEach((el) => {
    const kept = (el.getAttribute('class') ?? '')
      .split(/\s+/)
      .filter((c) => ALLOWED_CLASSES.has(c))
    if (kept.length) el.setAttribute('class', kept.join(' '))
    else el.removeAttribute('class')
  })
}

/**
 * JARVIS's markup is model output, and some of what it summarises came from the
 * open web — so it is treated as untrusted. Scripts, event handlers and styles
 * are stripped; what survives is layout, text and media.
 */
function sanitise(html: string): string {
  const doc = new DOMParser().parseFromString(
    DOMPurify.sanitize(html, {
      ALLOWED_TAGS: [
        'div', 'span', 'p', 'ul', 'ol', 'li', 'img', 'b', 'strong', 'em', 'i',
        'br', 'small', 'table', 'thead', 'tbody', 'tr', 'td', 'th', 'code', 'pre',
        // Showing a video result as a line of text was the polite version of
        // refusing to answer.
        'video', 'source', 'iframe',
      ],
      // No href — a HUD panel isn't clickable, and it keeps navigation off the
      // table entirely.
      ALLOWED_ATTR: [
        'class', 'src', 'alt', 'style',
        'controls', 'poster', 'loop', 'muted', 'playsinline', 'preload',
        'width', 'height', 'allow', 'allowfullscreen', 'referrerpolicy',
        'type', 'title',
      ],
      // Attributes that are not URLs and must not be judged as if they were.
      //
      // DOMPurify tests ALLOWED_URI_REGEXP against the value of *every*
      // attribute, not only the ones that carry a URI — anything not on its
      // inert list has to look like a permitted URL or it is dropped. Its own
      // default regexp ends in a catch-all for values that aren't scheme-shaped,
      // so this never shows up until you tighten the regexp, and then it bites:
      // with the list below removed, `type="video/mp4"` disappears off every
      // <source>, `width` and `height` off every embed, and the panel is left
      // asking the browser to guess. `src` and `poster` are deliberately absent
      // — those are real URLs and they stay under the regexp.
      ADD_URI_SAFE_ATTR: [
        'controls', 'loop', 'muted', 'playsinline', 'preload', 'width',
        'height', 'allow', 'allowfullscreen', 'referrerpolicy', 'type',
      ],
      // http(s) is permitted here and then immediately taken away again:
      // rewriteMedia below turns every remote src into a bridge URL, so nothing
      // that survives this function actually points off the machine except an
      // allowlisted embed. Letting it through the sanitiser is what makes that
      // rewrite possible — refusing it here is how the display ended up unable
      // to show anything it found. Supplying ALLOWED_TAGS/ALLOWED_ATTR replaces
      // DOMPurify's defaults wholesale, so there is deliberately no FORBID_*
      // list here — one would read as defence in depth while doing nothing.
      ALLOWED_URI_REGEXP: /^(?:data:(?:image|video|audio)\/|file:\/\/|https?:\/\/|\/)/i,
    }),
    'text/html',
  )
  /**
   * `style` survives only for the --v custom property the progress bar uses.
   *
   * This narrowing is load-bearing security, not tidying up. DOMPurify performs
   * no CSS parsing whatsoever: `style` is one of its DEFAULT_URI_SAFE_ATTRIBUTES,
   * so it short-circuits before ALLOWED_URI_REGEXP is ever consulted and the
   * declaration block passes through verbatim. Delete this and
   * `style="position:fixed;inset:0;z-index:9999"` renders exactly as written.
   */
  doc.body.querySelectorAll('[style]').forEach((el) => {
    const style = el.getAttribute('style') ?? ''
    const v = /--v:\s*([\d.]+)/.exec(style)
    if (v) el.setAttribute('style', `--v:${v[1]}`)
    else el.removeAttribute('style')
  })
  narrowClasses(doc.body)
  // Order matters: rewriteEmbeds runs before hardenMedia so an iframe that is
  // about to be removed is never dressed up first, and both run after
  // narrowClasses so a dropped element takes its classes with it.
  rewriteMedia(doc.body)
  rewriteEmbeds(doc.body)
  hardenMedia(doc.body)
  return doc.body.innerHTML
}

/** How a panel arrives. The model picks one per panel. */
const VARIANTS: Record<Panel['anim'], Variants> = {
  materialise: {
    hidden: { opacity: 0, scaleY: 0.86, filter: 'blur(4px)' },
    shown: { opacity: 1, scaleY: 1, filter: 'blur(0px)' },
  },
  sweep: {
    hidden: { opacity: 0, x: 44 },
    shown: { opacity: 1, x: 0 },
  },
  unfold: {
    hidden: { opacity: 0, scaleY: 0.2, originY: 0 },
    shown: { opacity: 1, scaleY: 1, originY: 0 },
  },
  stagger: {
    hidden: { opacity: 0, y: 14 },
    shown: { opacity: 1, y: 0 },
  },
  snap: {
    // Overshoots to 1.03 then settles — reads as a hard cut rather than a glide.
    hidden: { opacity: 0, scale: 1.04 },
    shown: { opacity: 1, scale: 1 },
  },
}

const SPRING = { type: 'spring' as const, stiffness: 300, damping: 28 }

/**
 * A dead <img> at width:100% renders as a large blank rectangle that reads as a
 * broken interface, and a <video> that never loaded is a black one. Replace
 * either with a small caption.
 *
 * Now that remote media is proxied there is a third way to fail on top of the
 * two that always existed (a disk path the bridge can't read, and an element
 * whose src the sanitiser removed — which has no src at all, so it reports
 * complete with a natural width of 0): the bridge itself refusing the fetch,
 * because the host blocked it, the content-type wasn't media, or the URL
 * resolved somewhere on the LAN.
 *
 * The sanitiser strips `onerror`, so the handler has to be attached here.
 *
 * Flagged per element rather than per call: the body is only re-parsed when the
 * markup changes, but nothing stops this running twice over the same nodes, and
 * a second listener would replace an already-replaced image.
 */
function watchMedia(node: HTMLDivElement | null) {
  if (!node) return

  node.querySelectorAll('img').forEach((img) => {
    if (img.dataset.watched) return
    img.dataset.watched = '1'
    const fail = () => replaceWithNote(img, 'image unavailable')
    if (img.complete && img.naturalWidth === 0) fail()
    else img.addEventListener('error', fail, { once: true })
  })

  node.querySelectorAll('video').forEach((video) => {
    if (video.dataset.watched) return
    video.dataset.watched = '1'
    const fail = () => replaceWithNote(video, 'video unavailable')
    // A <video> the sanitiser stripped the src from never attempts a load, so
    // it never errors either — it just sits there as a black rectangle. The
    // <img> equivalent is caught by naturalWidth; this is the check that stands
    // in for it.
    if (!video.hasAttribute('src') && !video.querySelector('source[src]')) {
      fail()
      return
    }
    // Captured rather than bubbled. When the sources are <source> children the
    // media element itself never fires `error` — each child does, and error
    // events don't bubble — so listening on the parent alone would miss exactly
    // the shape the design system encourages. Capture sees both.
    video.addEventListener('error', fail, { capture: true, once: true })
  })
}

function replaceWithNote(el: Element, text: string) {
  const note = document.createElement('span')
  note.className = 'hud-caption hud-dim'
  note.textContent = text
  el.replaceWith(note)
}

/**
 * Memoised because the HUD around it re-renders with the microphone level —
 * roughly sixty times a second — and none of that has anything to do with what
 * is on a card. Panels are immutable once pushed, so identity comparison is
 * enough, and it is what keeps the sanitise pass below from running per frame.
 */
const Card = memo(function Card({ panel }: { panel: Panel }) {
  const html = useMemo(() => sanitise(panel.html ?? ''), [panel.html])

  // An empty body renders as a large blank rectangle, which looks like the
  // interface is broken rather than like nothing was sent. Say so instead.
  //
  // A panel whose entire content is a video or an embed has no text and no
  // <img>, and was being declared empty and thrown away — the caption said "no
  // content returned" while holding the thing it had been asked to show.
  const empty = useMemo(
    () => !html.replace(/<[^>]*>/g, '').trim() && !/<(?:img|video|iframe)\b/i.test(html),
    [html],
  )

  const body = useRef<HTMLDivElement>(null)

  // In an effect, so it is one line in the console per bad panel rather than
  // one per frame for as long as the panel is up.
  useEffect(() => {
    if (empty) console.warn('[jarvis] empty panel body', panel.title, panel.html)
  }, [panel, empty])

  // After the markup lands, and again only when the markup changes. As a
  // callback ref this re-queried every image on every render of the card.
  useEffect(() => {
    watchMedia(body.current)
  }, [html])

  return (
    <motion.section
      className={`panel panel-${panel.accent}`}
      variants={VARIANTS[panel.anim] ?? VARIANTS.materialise}
      initial="hidden"
      animate="shown"
      exit={{ opacity: 0, filter: 'blur(6px)', transition: { duration: 0.3 } }}
      transition={panel.anim === 'snap' ? { duration: 0.12 } : SPRING}
      // Deliberately no `layout` prop. Re-flowing the stack when a sibling
      // enters or leaves looks nice for one frame and flickers for the rest —
      // layout projection re-measures continuously and fights the container.
      // The gap between cards is fixed, so there is nothing to animate.
    >
      <span className="pk pk-tl" />
      <span className="pk pk-tr" />
      <span className="pk pk-bl" />
      <span className="pk pk-br" />

      {/* The scan wipe — a band that travels the height of the card once. */}
      <motion.span
        className="p-wipe"
        initial={{ y: '-100%', opacity: 0.9 }}
        animate={{ y: '300%', opacity: 0 }}
        transition={{ duration: 0.7, ease: 'easeOut' }}
      />

      <header className="p-head">
        <span className="p-title">{panel.title}</span>
      </header>

      {/* Sanitised above; `stagger` is handled in CSS so it applies to whatever
          children the model happened to author. */}
      {empty ? (
        <p className="p-empty">no content returned</p>
      ) : (
        <div
          ref={body}
          className={panel.anim === 'stagger' ? 'p-body p-stagger' : 'p-body'}
          dangerouslySetInnerHTML={{ __html: html }}
        />
      )}
    </motion.section>
  )
})

/**
 * Memoised for the same reason as Card: it takes no props, so it re-renders
 * only when the panel list itself changes rather than every time the HUD
 * repaints around it.
 */
export const Panels = memo(function Panels() {
  const panels = useStore((s) => s.panels)

  const slots = {
    right: panels.filter((p) => p.slot === 'right' || !p.slot),
    left: panels.filter((p) => p.slot === 'left'),
    wide: panels.filter((p) => p.slot === 'wide'),
  }

  return (
    <>
      {(['right', 'left', 'wide'] as const).map((slot) => (
        <div key={slot} className={`panels panels-${slot}`}>
          <AnimatePresence>
            {slots[slot].map((p) => (
              <Card key={p.id} panel={p} />
            ))}
          </AnimatePresence>
        </div>
      ))}
    </>
  )
})
