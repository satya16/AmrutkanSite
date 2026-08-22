import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Breadcrumb, Button, Drawer, List, Result, Skeleton, Slider, Space, Spin, Typography, theme as antdTheme } from 'antd'
import {
  FullscreenExitOutlined,
  FullscreenOutlined,
  LeftOutlined,
  RightOutlined,
  UnorderedListOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
} from '@ant-design/icons'
import { fetchPustake, type PustakBook } from '../api'
import { toDevanagari } from '../devanagari'
import { loadPustakPage, savePustakPage } from '../pustakProgress'

// Pages are drawn into a <canvas> rather than an <img> — a canvas has no
// built-in "Save image as…"/drag-out affordance, and pairing it with
// onContextMenu/onDragStart prevention and disabled text-selection raises
// the bar against casual one-click saving without pretending to stop a
// determined screen-recorder (nothing client-side can do that).
export default function PustakPage() {
  const { bookId } = useParams<{ bookId: string }>()
  const [book, setBook] = useState<PustakBook | null | undefined>(undefined)
  // Resume where you left off, same idea as the audio player's ak_playback
  // — read synchronously from localStorage so the first-ever page fetch is
  // already for the right page (no flash of page 1 while a "jump to saved
  // page" correction effect kicks in after the book metadata loads).
  const [page, setPage] = useState(() => loadPustakPage(bookId) ?? 1)
  const [imageLoaded, setImageLoaded] = useState(false)
  // Which way the page turn animation (below) should nudge in from — set
  // explicitly by goNext/goPrev rather than inferred by diffing page
  // numbers, since a couple of page changes (resuming a saved page,
  // switching books) aren't really "turns" and don't need a meaningful
  // direction.
  const [direction, setDirection] = useState<1 | -1>(1)
  // "Immersive" is a CSS full-viewport style on the (always-mounted)
  // readerRef container — the source of truth for the bigger-page layout,
  // and works everywhere, including iOS Safari and in-app browsers
  // (WhatsApp/Instagram) that don't support/allow the real Fullscreen API.
  // Requesting the browser's native fullscreen on the same element (below)
  // is best-effort on top — when it works, it also hides the browser
  // chrome/address bar. It's the *same* element in both states (styled
  // differently, never unmounted) — swapping to a different element while
  // fullscreen would make the browser treat that as exiting fullscreen.
  const [immersive, setImmersive] = useState(false)
  // Tracks phone rotation so the fit-width math (below) and the
  // non-fullscreen mobile-landscape layout (the `wide` flag further down)
  // can react to it. Re-checked on every orientation change, not just once
  // on mount.
  const [isLandscape, setIsLandscape] = useState(
    () => window.matchMedia('(orientation: landscape)').matches,
  )
  // The fit-width math below needs the *current* viewport size, but mobile
  // browsers don't necessarily finish resizing the visual viewport in the
  // same tick as the matchMedia orientation flip — reading
  // window.innerWidth/innerHeight directly at render time could grab a
  // stale, mid-rotation value and leave the canvas sized for the old
  // orientation ("zoom is weird" after portrait -> landscape -> portrait).
  // Tracking both via their own resize listener keeps them reactive
  // through the whole transition, not just at the orientation boundary.
  const [viewport, setViewport] = useState(() => ({ w: window.innerWidth, h: window.innerHeight }))
  // Zoom only applies in fullscreen (immersive). 1 = fit-to-screen default.
  // Tracking the loaded image's own pixel dimensions lets zoom compute an
  // exact fit width instead of fighting CSS percentage/max-height rules.
  const [zoom, setZoom] = useState(1)
  const [naturalSize, setNaturalSize] = useState<{ w: number; h: number } | null>(null)
  const [tocOpen, setTocOpen] = useState(false)
  // Mirrors `page` but updates on every drag tick of the progress slider
  // (below) without triggering a page load — only onChangeComplete commits
  // to `page`, so dragging across the whole book doesn't fetch every page
  // in between. Kept in sync whenever `page` changes some other way (prev/
  // next/chapter link) so the handle never drifts from the actual page.
  const [sliderValue, setSliderValue] = useState(page)
  // Outside fullscreen, the reader is capped to a comfortable reading width
  // (560px) — good on a phone held in portrait, but on a phone rotated to
  // landscape that cap leaves most of the (much wider) screen empty instead
  // of using it. On mobile landscape specifically, drop the cap so the page
  // fills the available width — same idea as the immersive-landscape case
  // below, just without requiring the user to tap into fullscreen first.
  // Desktop/tablet browsers, which are "landscape" by default, are
  // untouched by this — it's keyed off a mobile-device UA check too, same
  // pattern Home.tsx uses for its podcast-link target behavior.
  const isMobile = /iphone|ipad|ipod|android/i.test(navigator.userAgent)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const readerRef = useRef<HTMLDivElement>(null)
  const touchStartRef = useRef<{ x: number; y: number } | null>(null)
  const { token } = antdTheme.useToken()

  useEffect(() => {
    fetchPustake().then((data) => setBook(data.books.find((b) => b.id === bookId) ?? null))
  }, [bookId])

  useEffect(() => {
    setPage(loadPustakPage(bookId) ?? 1)
  }, [bookId])

  // Defensive clamp only — the lazy useState initializer and the effect
  // above already cover the normal case. This just guards against a saved
  // page number that's out of range for the book as it exists now (e.g. a
  // book was re-rendered with fewer pages after the save happened).
  useEffect(() => {
    if (book && page > book.pageCount) setPage(book.pageCount)
  }, [book, page])

  useEffect(() => {
    if (book) savePustakPage(book.id, page)
  }, [book, page])

  useEffect(() => {
    if (!book) return
    setImageLoaded(false)
    // The turn animation (canvas opacity/transform, further down) is driven
    // by imageLoaded flipping false → true — but the next-page prefetch
    // below means that flip often happens (cache hit) well under a
    // frame after it goes false, which cuts the fade-out off before it's
    // gone anywhere visible: the transition reverses almost immediately
    // instead of actually being seen. Holding imageLoaded false for at
    // least one full transition's worth of time (matching the 180ms in the
    // canvas's own `transition` below) guarantees the fade-out always has
    // time to complete before the fade-in starts, regardless of how fast
    // the image itself loads.
    const TURN_HOLD_MS = 180
    const start = performance.now()
    let holdTimeout: ReturnType<typeof setTimeout> | undefined
    const img = new Image()
    img.onload = () => {
      const canvas = canvasRef.current
      if (!canvas) return
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      canvas.getContext('2d')?.drawImage(img, 0, 0)
      setNaturalSize({ w: img.naturalWidth, h: img.naturalHeight })
      const remaining = TURN_HOLD_MS - (performance.now() - start)
      if (remaining > 0) {
        holdTimeout = setTimeout(() => setImageLoaded(true), remaining)
      } else {
        setImageLoaded(true)
      }
    }
    img.src = `/pustak/${book.id}/page/${page}.jpg`

    // Prefetch the next page so turning forward feels instant — the browser
    // cache does the rest, no extra state needed here.
    if (page < book.pageCount) {
      new Image().src = `/pustak/${book.id}/page/${page + 1}.jpg`
    }

    return () => {
      if (holdTimeout) clearTimeout(holdTimeout)
    }
  }, [book, page])

  // Swipe-to-turn-page, mainly for mobile fullscreen reading. Read the
  // start point on touchstart, compare to the end point on touchend — a
  // horizontal swipe past SWIPE_THRESHOLD that's more horizontal than
  // vertical (so a normal vertical scroll/pull doesn't get misread as a
  // page turn) counts: right-to-left → next page, left-to-right → previous.
  // Disabled while zoomed in — at that point a horizontal drag is someone
  // panning across the enlarged page to read it, not asking to turn the
  // page, so the browser's native scroll/pan takes over instead (see
  // touchAction below).
  const SWIPE_THRESHOLD = 50
  const onTouchStart = (e: React.TouchEvent) => {
    const t = e.touches[0]
    touchStartRef.current = { x: t.clientX, y: t.clientY }
  }

  const goNext = () => {
    setDirection(1)
    setPage((p) => (book ? Math.min(book.pageCount, p + 1) : p))
  }
  const goPrev = () => {
    setDirection(-1)
    setPage((p) => Math.max(1, p - 1))
  }
  // Shared by the chapter drawer and the progress slider below — both jump
  // straight to an arbitrary page rather than stepping one at a time, so
  // the turn-animation direction is derived from where the target page
  // sits relative to the current one instead of always being "forward".
  const goToPage = (target: number) => {
    if (!book) return
    const clamped = Math.max(1, Math.min(book.pageCount, target))
    setDirection(clamped >= page ? 1 : -1)
    setPage(clamped)
  }

  useEffect(() => {
    setSliderValue(page)
  }, [page])

  const onTouchEnd = (e: React.TouchEvent) => {
    const start = touchStartRef.current
    touchStartRef.current = null
    if (!start || !book || zoom !== 1) return
    const t = e.changedTouches[0]
    const dx = t.clientX - start.x
    const dy = t.clientY - start.y
    if (Math.abs(dx) < SWIPE_THRESHOLD || Math.abs(dx) < Math.abs(dy)) return
    if (dx < 0) {
      goNext()
    } else {
      goPrev()
    }
  }

  const ZOOM_MIN = 1
  const ZOOM_MAX = 3
  const ZOOM_STEP = 0.25
  const zoomIn = () => setZoom((z) => Math.min(ZOOM_MAX, +(z + ZOOM_STEP).toFixed(2)))
  const zoomOut = () => setZoom((z) => Math.max(ZOOM_MIN, +(z - ZOOM_STEP).toFixed(2)))

  // Mouse-wheel zoom, desktop only in practice (a wheel event never fires
  // from a touchscreen, so this can't conflict with the pinch/swipe touch
  // handlers above) — scoped to the fullscreen reader, which is where zoom
  // already has on-screen buttons and correctly centers/scrolls at any
  // zoom level (see the scroll-centering effect below). Scaling the change
  // by e.deltaY directly (rather than a fixed step per event) matters
  // because a trackpad fires many small wheel events per gesture where a
  // mouse fires one large one per notch — a fixed step would make trackpad
  // zooming shoot past where the user meant to stop.
  const ZOOM_WHEEL_SENSITIVITY = 0.0015
  const onWheel = (e: React.WheelEvent) => {
    if (!immersive) return
    e.preventDefault()
    setZoom((z) => {
      const next = z - e.deltaY * ZOOM_WHEEL_SENSITIVITY
      return Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, +next.toFixed(2)))
    })
  }

  const toggleImmersive = async () => {
    const next = !immersive
    setImmersive(next)
    if (!next) setZoom(1)
    try {
      if (next && readerRef.current?.requestFullscreen) {
        await readerRef.current.requestFullscreen()
      } else if (!next && document.fullscreenElement) {
        await document.exitFullscreen()
      }
    } catch {
      // Native fullscreen unsupported/blocked — the CSS immersive state
      // above already gives the bigger, distraction-free view regardless.
    }
  }

  useEffect(() => {
    const mq = window.matchMedia('(orientation: landscape)')
    const onChange = () => setIsLandscape(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  useEffect(() => {
    const onResize = () => setViewport({ w: window.innerWidth, h: window.innerHeight })
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  // Zoom is per-page and per-orientation — a fresh page or a rotation
  // should start back at fit-to-screen rather than carrying over a zoom
  // level computed for a different layout.
  useEffect(() => {
    setZoom(1)
  }, [page, isLandscape])

  // Panning around a zoomed-in page leaves the container scrolled to some
  // arbitrary (scrollLeft, scrollTop). If that offset survives a zoom
  // change, resizing the canvas underneath it re-anchors the same raw
  // scroll numbers to a completely different part of the (now smaller or
  // larger) content — that's the "zooming out lands on a weird
  // off-center view" bug. Snapping scroll to the middle of whatever just
  // got (re)rendered on every page/orientation/zoom change keeps each new
  // size starting from a known, consistent position instead of an offset
  // computed for a different size — centered, not top-left, since the
  // container itself is a centered flex layout (see `scrollable` below):
  // resting at (0, 0) visually shoved the zoomed page into a corner instead
  // of leaving it looking centered, which is the point of the reset here.
  useEffect(() => {
    const el = readerRef.current
    if (el) {
      el.scrollTop = (el.scrollHeight - el.clientHeight) / 2
      el.scrollLeft = (el.scrollWidth - el.clientWidth) / 2
    }
  }, [page, isLandscape, zoom])

  // Keeps our state in sync if the *browser's* fullscreen is exited some
  // other way (Esc, F11, swipe-down on Android) instead of our own button.
  useEffect(() => {
    const onFsChange = () => {
      if (!document.fullscreenElement) setImmersive(false)
    }
    document.addEventListener('fullscreenchange', onFsChange)
    return () => document.removeEventListener('fullscreenchange', onFsChange)
  }, [])

  useEffect(() => {
    if (!immersive) return
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prevOverflow
    }
  }, [immersive])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') goPrev()
      if (e.key === 'ArrowRight' && book) goNext()
      if (e.key === 'Escape' && immersive) toggleImmersive()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [book, immersive])

  if (book === undefined) {
    return <Skeleton active paragraph={{ rows: 8 }} />
  }
  if (book === null) {
    return (
      <Result
        status="404"
        title="पुस्तक सापडले नाही"
        extra={
          <Link to="/">
            <Button type="primary">मुख्य पानावर जा</Button>
          </Link>
        }
      />
    )
  }

  // Only zooming in can make the page bigger than the viewport now (fit is
  // always height-capped below, landscape included) — that's when the
  // container needs to actually scroll.
  const scrollable = immersive && zoom > 1

  // In the normal (non-fullscreen) reader on a phone rotated to landscape,
  // width:100% (the portrait behavior below) makes a portrait-shaped page
  // taller than the short landscape viewport, cutting it off and forcing a
  // scroll to see the rest of the page. Landscape needs the opposite fix
  // from immersive's width-fill: cap by *height* instead so the whole page
  // is visible at once, same as it used to look — the user can still pinch
  // to zoom in natively for detail.
  const wide = isMobile && isLandscape && !immersive

  // Fit-to-screen width in real pixels (not a CSS percentage) so zoom can
  // just multiply it directly. Always height-capped (viewport height minus
  // room for the control bar) regardless of orientation, so the whole page
  // is visible without scrolling at the default zoom — landscape used to
  // fill the viewport's width instead (making a portrait-shaped page run
  // taller than the screen, requiring a scroll to see the rest of it), but
  // that traded away "see the whole page at a glance" for "bigger text",
  // which is the wrong trade for this reader. Zooming in (pinch-equivalent
  // buttons) is how you get bigger text now, same as portrait always did.
  let canvasStyle: React.CSSProperties
  if (!immersive) {
    canvasStyle = wide
      ? { width: 'auto', height: 'auto', maxWidth: '100%', maxHeight: 'calc(100vh - 150px)' }
      : { width: '100%', height: 'auto', maxWidth: '100%' }
  } else if (!naturalSize) {
    canvasStyle = { width: 'auto', height: 'auto', maxWidth: '100%', maxHeight: 'calc(100vh - 64px)' }
  } else {
    const fitWidth = Math.min(viewport.w, (viewport.h - 64) * (naturalSize.w / naturalSize.h))
    canvasStyle = { width: `${fitWidth * zoom}px`, height: 'auto', maxWidth: 'none' }
  }

  return (
    <div
      ref={readerRef}
      style={
        immersive
          ? {
              position: 'fixed',
              inset: 0,
              zIndex: 2000,
              background: '#000',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              overflow: scrollable ? 'auto' : 'hidden',
              padding: scrollable ? '8px 0 72px' : '8px 0',
            }
          : { maxWidth: 560, margin: '0 auto' }
      }
    >
      {!immersive && (
        <>
          <Breadcrumb
            items={[{ title: <Link to="/">अमृतकण</Link> }, { title: book.title }]}
            style={{ marginBottom: wide ? 8 : 16 }}
          />
          {/* Landscape-mobile: the title/subtitle block is dropped (the
              breadcrumb above still names the book) to free up the vertical
              room a short landscape viewport needs to fit the whole page. */}
          {!wide && (
            <>
              <Typography.Title level={3} style={{ textAlign: 'center', marginTop: 0 }}>
                {book.title}
              </Typography.Title>
              {book.subtitle && (
                <Typography.Paragraph type="secondary" style={{ textAlign: 'center', marginTop: -8 }}>
                  {book.subtitle}
                </Typography.Paragraph>
              )}
            </>
          )}
        </>
      )}

      <div
        onContextMenu={(e) => e.preventDefault()}
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
        onWheel={onWheel}
        style={{
          background: token.colorFillTertiary,
          borderRadius: immersive ? 0 : 12,
          padding: immersive ? 0 : 12,
          display: 'flex',
          justifyContent: 'center',
          // Flex auto-margins (rather than the parent's justify/align-
          // center above) are what actually keep this centered *while*
          // scrollable — centering an overflowing flex item purely via the
          // parent's justify-content/align-items can leave the overflow on
          // the "before center" side unreachable by scroll in some
          // browsers (notably Safari); auto margins don't have that bug and
          // still resolve to dead-center when there's no overflow to speak
          // of, so this is safe to apply unconditionally.
          margin: 'auto',
          userSelect: 'none',
          WebkitUserSelect: 'none',
          WebkitTouchCallout: 'none',
          // Zoomed in: let the browser's native panning handle both
          // directions (finger-drag to explore the enlarged page). At the
          // default zoom, only vertical panning is native — horizontal
          // drags are ours (the swipe-to-turn-page handler above).
          touchAction: zoom > 1 ? 'auto' : 'pan-y',
        }}
      >
        {/* Only the very first page a session ever loads has nothing to
            show while it's in flight — every page turn after that already
            has the previous page's pixels on the canvas, which the
            fade/slide below uses instead of a spinner (and which, thanks to
            the next-page prefetch, is normally so fast the spinner would
            just flash anyway). */}
        {!imageLoaded && !naturalSize && (
          <div
            style={{
              width: '100%',
              aspectRatio: '2 / 3',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Spin size="large" />
          </div>
        )}
        <canvas
          ref={canvasRef}
          draggable={false}
          onDragStart={(e) => e.preventDefault()}
          style={{
            display: naturalSize ? 'block' : 'none',
            ...canvasStyle,
            // Page-turn animation: the outgoing page fades/nudges out the
            // moment a turn starts (imageLoaded goes false while the canvas
            // still holds the old page's pixels), then the incoming page
            // fades/nudges in from `direction`'s side once the new image
            // has loaded and been drawn. One canvas, reused in place, not a
            // true simultaneous two-layer slide — simple, and the site's
            // global prefers-reduced-motion rule (index.css) already forces
            // this down to ~instant for anyone who's asked for that.
            opacity: imageLoaded ? 1 : 0,
            transform: imageLoaded ? 'translateX(0)' : `translateX(${direction * 20}px)`,
            transition: 'opacity 180ms ease, transform 180ms ease',
            // Without this, the flex wrapper's default flex-shrink can
            // squeeze a canvas wider than it down to fit — defeating zoom.
            flexShrink: 0,
            borderRadius: 4,
            boxShadow: immersive ? undefined : token.boxShadow,
          }}
        />
      </div>

      <div
        style={
          immersive
            ? {
                position: 'fixed',
                bottom: 0,
                left: 0,
                right: 0,
                background: 'rgba(0, 0, 0, 0.55)',
                padding: '10px 16px',
                zIndex: 2001,
              }
            : { marginTop: 16 }
        }
      >
        {/* Seekable progress bar — same idea as the audio player's seek
            Slider (NowPlayingOverlay.tsx), just scrubbing pages instead of
            seconds. `sliderValue` tracks the drag live (smooth handle
            movement, no page fetch per tick); the actual page only changes
            on release via onChangeComplete. */}
        <div style={{ maxWidth: immersive ? 480 : 420, margin: '0 auto 4px' }}>
          <Slider
            min={1}
            max={book.pageCount}
            value={sliderValue}
            onChange={setSliderValue}
            onChangeComplete={(v) => goToPage(v)}
            tooltip={{ formatter: (v) => `पृष्ठ ${toDevanagari(v ?? 1)}` }}
            aria-label="पृष्ठ सरकवा"
          />
        </div>
        <Space style={{ width: '100%', justifyContent: 'center' }} size={immersive ? 12 : 24} wrap>
          {book.chapters.length > 0 && (
            <Button
              icon={<UnorderedListOutlined />}
              onClick={() => setTocOpen(true)}
              aria-label="अनुक्रमणिका"
            />
          )}
          <Button
            icon={<LeftOutlined />}
            onClick={goPrev}
            disabled={page <= 1}
            aria-label="मागील पान"
          />
          <Typography.Text style={{ color: immersive ? token.colorTextLightSolid : undefined }}>
            पृष्ठ {toDevanagari(page)} / {toDevanagari(book.pageCount)}
          </Typography.Text>
          <Button
            icon={<RightOutlined />}
            onClick={goNext}
            disabled={page >= book.pageCount}
            aria-label="पुढील पान"
          />
          {immersive && (
            <>
              <Button icon={<ZoomOutOutlined />} onClick={zoomOut} disabled={zoom <= ZOOM_MIN} aria-label="झूम आउट" />
              <Button icon={<ZoomInOutlined />} onClick={zoomIn} disabled={zoom >= ZOOM_MAX} aria-label="झूम इन" />
            </>
          )}
          <Button
            icon={immersive ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
            onClick={toggleImmersive}
            aria-label={immersive ? 'पूर्ण स्क्रीनमधून बाहेर पडा' : 'पूर्ण स्क्रीन'}
          />
        </Space>
      </div>

      <Drawer
        title="अनुक्रमणिका"
        open={tocOpen}
        onClose={() => setTocOpen(false)}
        placement="right"
      >
        <List
          dataSource={book.chapters}
          renderItem={(chapter, i) => {
            const next = book.chapters[i + 1]
            const isCurrent = page >= chapter.page && (!next || page < next.page)
            return (
              <List.Item
                onClick={() => {
                  goToPage(chapter.page)
                  setTocOpen(false)
                }}
                style={{
                  cursor: 'pointer',
                  borderRadius: 8,
                  paddingLeft: 12,
                  paddingRight: 12,
                  background: isCurrent ? token.colorPrimaryBg : undefined,
                }}
              >
                <Typography.Text strong={isCurrent}>{chapter.title}</Typography.Text>
              </List.Item>
            )
          }}
        />
      </Drawer>
    </div>
  )
}
