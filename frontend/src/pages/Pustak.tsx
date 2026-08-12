import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Breadcrumb, Button, Result, Skeleton, Space, Spin, Typography, theme as antdTheme } from 'antd'
import {
  FullscreenExitOutlined,
  FullscreenOutlined,
  LeftOutlined,
  RightOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
} from '@ant-design/icons'
import { fetchPustake, type PustakBook } from '../api'
import { toDevanagari } from '../devanagari'

// Pages are drawn into a <canvas> rather than an <img> — a canvas has no
// built-in "Save image as…"/drag-out affordance, and pairing it with
// onContextMenu/onDragStart prevention and disabled text-selection raises
// the bar against casual one-click saving without pretending to stop a
// determined screen-recorder (nothing client-side can do that).
export default function PustakPage() {
  const { bookId } = useParams<{ bookId: string }>()
  const [book, setBook] = useState<PustakBook | null | undefined>(undefined)
  const [page, setPage] = useState(1)
  const [imageLoaded, setImageLoaded] = useState(false)
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
  // In landscape fullscreen, a portrait-shaped page should fill the
  // screen's width (readable, like the request asked for) rather than
  // being height-capped and left narrow with black bars on the sides —
  // the trade-off is the page then runs taller than the viewport, so that
  // case scrolls instead of centering. Re-checked on every orientation
  // change (phone rotation), not just once on mount.
  const [isLandscape, setIsLandscape] = useState(
    () => window.matchMedia('(orientation: landscape)').matches,
  )
  // Zoom only applies in fullscreen (immersive). 1 = fit-to-screen default.
  // Tracking the loaded image's own pixel dimensions lets zoom compute an
  // exact fit width instead of fighting CSS percentage/max-height rules.
  const [zoom, setZoom] = useState(1)
  const [naturalSize, setNaturalSize] = useState<{ w: number; h: number } | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const readerRef = useRef<HTMLDivElement>(null)
  const touchStartRef = useRef<{ x: number; y: number } | null>(null)
  const { token } = antdTheme.useToken()

  useEffect(() => {
    fetchPustake().then((data) => setBook(data.books.find((b) => b.id === bookId) ?? null))
  }, [bookId])

  useEffect(() => {
    setPage(1)
  }, [bookId])

  useEffect(() => {
    if (!book) return
    setImageLoaded(false)
    const img = new Image()
    img.onload = () => {
      const canvas = canvasRef.current
      if (!canvas) return
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      canvas.getContext('2d')?.drawImage(img, 0, 0)
      setNaturalSize({ w: img.naturalWidth, h: img.naturalHeight })
      setImageLoaded(true)
    }
    img.src = `/pustak/${book.id}/page/${page}.jpg`

    // Prefetch the next page so turning forward feels instant — the browser
    // cache does the rest, no extra state needed here.
    if (page < book.pageCount) {
      new Image().src = `/pustak/${book.id}/page/${page + 1}.jpg`
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
  const onTouchEnd = (e: React.TouchEvent) => {
    const start = touchStartRef.current
    touchStartRef.current = null
    if (!start || !book || zoom !== 1) return
    const t = e.changedTouches[0]
    const dx = t.clientX - start.x
    const dy = t.clientY - start.y
    if (Math.abs(dx) < SWIPE_THRESHOLD || Math.abs(dx) < Math.abs(dy)) return
    if (dx < 0) {
      setPage((p) => Math.min(book.pageCount, p + 1))
    } else {
      setPage((p) => Math.max(1, p - 1))
    }
  }

  const ZOOM_MIN = 1
  const ZOOM_MAX = 3
  const ZOOM_STEP = 0.25
  const zoomIn = () => setZoom((z) => Math.min(ZOOM_MAX, +(z + ZOOM_STEP).toFixed(2)))
  const zoomOut = () => setZoom((z) => Math.max(ZOOM_MIN, +(z - ZOOM_STEP).toFixed(2)))

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
  // off-center view" bug. Snapping scroll back to the top-left on every
  // page/orientation/zoom change keeps each new size starting from a
  // known, consistent position instead of an offset computed for a
  // different size.
  useEffect(() => {
    const el = readerRef.current
    if (el) {
      el.scrollTop = 0
      el.scrollLeft = 0
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
      if (e.key === 'ArrowLeft') setPage((p) => Math.max(1, p - 1))
      if (e.key === 'ArrowRight' && book) setPage((p) => Math.min(book.pageCount, p + 1))
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

  // Anything that can make the page bigger than the viewport — landscape's
  // width-fill, or zooming in — needs the container to actually scroll in
  // both directions, and needs to give up on centering: centering a flex
  // item that overflows its container can leave the start of it
  // unreachable by scroll in some browsers, so once it can overflow, both
  // axes top/left-align instead.
  const scrollable = immersive && (isLandscape || zoom > 1)

  // Fit-to-screen width in real pixels (not a CSS percentage) so zoom can
  // just multiply it directly: landscape fills the viewport's width;
  // portrait is height-capped (viewport height minus room for the control
  // bar), so its fit width comes from the image's own aspect ratio.
  let canvasStyle: React.CSSProperties
  if (!immersive) {
    canvasStyle = { width: '100%', height: 'auto', maxWidth: '100%' }
  } else if (!naturalSize) {
    canvasStyle = { width: 'auto', height: 'auto', maxWidth: '100%', maxHeight: 'calc(100vh - 64px)' }
  } else {
    const fitWidth = isLandscape
      ? window.innerWidth
      : (window.innerHeight - 64) * (naturalSize.w / naturalSize.h)
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
              alignItems: scrollable ? 'flex-start' : 'center',
              justifyContent: scrollable ? 'flex-start' : 'center',
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
            style={{ marginBottom: 16 }}
          />
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

      <div
        onContextMenu={(e) => e.preventDefault()}
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
        style={{
          background: token.colorFillTertiary,
          borderRadius: immersive ? 0 : 12,
          padding: immersive ? 0 : 12,
          display: 'flex',
          justifyContent: 'center',
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
        {!imageLoaded && (
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
            display: imageLoaded ? 'block' : 'none',
            ...canvasStyle,
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
                padding: '10px 0',
                zIndex: 2001,
              }
            : { marginTop: 16 }
        }
      >
        <Space style={{ width: '100%', justifyContent: 'center' }} size={immersive ? 12 : 24} wrap>
          <Button
            icon={<LeftOutlined />}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            aria-label="मागील पान"
          />
          <Typography.Text style={{ color: immersive ? token.colorTextLightSolid : undefined }}>
            पृष्ठ {toDevanagari(page)} / {toDevanagari(book.pageCount)}
          </Typography.Text>
          <Button
            icon={<RightOutlined />}
            onClick={() => setPage((p) => Math.min(book.pageCount, p + 1))}
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
    </div>
  )
}
