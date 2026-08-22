import { useEffect, useRef, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Col, Row, Skeleton, Space, Typography, theme as antdTheme } from 'antd'
import { LeftOutlined, PlayCircleFilled, ReadFilled, RightOutlined } from '@ant-design/icons'
import { fetchHome, fetchLibrary, fetchPustake, type HomeContent, type Library, type PustakBook } from '../api'
import { toDevanagari } from '../devanagari'
import ContinueListening from '../components/ContinueListening'

const MOBILE_UA_RE = /iphone|ipad|ipod|android/i

// यूट्यूब चॅनल shelf: a native CSS scroll-snap row instead of antd's
// Carousel (which wraps react-slick) — that route hit three separate
// problems in a row: the arrow button's color/size kept losing to antd's
// own Carousel CSS and needed every property pinned inline to win: its
// `responsive` breakpoint prop only ever recalculates on a `resize`
// *event*, so a page loaded fresh at phone width (i.e. every real phone
// visitor, not just a window someone manually shrank) got stuck on the
// desktop slidesToShow forever; and even once positioned "outside" the
// row, the arrow's own hit area still overlapped the first/last tile's
// hit area, so a click near that edge could land on either one — play the
// video or scroll the shelf, unpredictably. A plain horizontally
// scrolling flexbox with CSS scroll-snap (.yt-shelf/.yt-tile in
// index.css) is the same pattern most video shelves — including
// YouTube's own site — actually use: layout adapts to any width from
// first paint via plain CSS media queries (no JS breakpoint math to get
// out of sync), native touch/trackpad momentum scrolling, and the arrow
// buttons sit in their own reserved margin beside the row rather than on
// top of any tile, so the two controls can never overlap.
function VideoShelf({
  videoIds,
  playingVideoId,
  onPlay,
  isMobile,
}: {
  videoIds: string[]
  playingVideoId: string | null
  onPlay: (id: string) => void
  isMobile: boolean
}) {
  const { token } = antdTheme.useToken()
  const scrollRef = useRef<HTMLDivElement>(null)
  const [canScrollPrev, setCanScrollPrev] = useState(false)
  const [canScrollNext, setCanScrollNext] = useState(false)

  const updateScrollState = () => {
    const el = scrollRef.current
    if (!el) return
    setCanScrollPrev(el.scrollLeft > 4)
    setCanScrollNext(el.scrollLeft + el.clientWidth < el.scrollWidth - 4)
  }

  useEffect(() => {
    updateScrollState()
    window.addEventListener('resize', updateScrollState)
    return () => window.removeEventListener('resize', updateScrollState)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videoIds.length])

  // Snap exactly one tile at a time rather than scrolling by a fraction of
  // the container's width: on narrow (mobile) widths only ~1 tile fits per
  // screen, so a percentage-based scroll landed mid-way between two tiles —
  // part of the current video still showing alongside a sliver of the next
  // one — instead of cleanly advancing to the next tile's scroll-snap
  // boundary. scrollIntoView lets the browser compute the exact offset
  // (respecting the row's padding/gap) rather than us reproducing that math.
  const scrollByPage = (direction: 1 | -1) => {
    const el = scrollRef.current
    if (!el) return
    const tiles = Array.from(el.querySelectorAll<HTMLElement>('.yt-tile'))
    if (tiles.length === 0) return
    const gap = parseFloat(getComputedStyle(el).columnGap || '0') || 0
    const step = tiles[0].getBoundingClientRect().width + gap
    const index = Math.round(el.scrollLeft / step)
    const nextIndex = Math.min(Math.max(index + direction, 0), tiles.length - 1)
    tiles[nextIndex].scrollIntoView({ behavior: 'smooth', inline: 'start', block: 'nearest' })
  }

  const arrowStyle = (disabled: boolean): CSSProperties => ({
    flex: '0 0 auto',
    width: 36,
    height: 36,
    borderRadius: '50%',
    border: `1px solid ${token.colorBorderSecondary}`,
    background: token.colorBgContainer,
    color: token.colorText,
    boxShadow: token.boxShadowTertiary,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: disabled ? 'default' : 'pointer',
    opacity: disabled ? 0.35 : 1,
  })

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <button
        style={arrowStyle(!canScrollPrev)}
        onClick={() => scrollByPage(-1)}
        disabled={!canScrollPrev}
        aria-label="मागील व्हिडिओ"
      >
        <LeftOutlined />
      </button>
      <div className="yt-shelf" ref={scrollRef} onScroll={updateScrollState}>
        {videoIds.map((id) => (
          <div className="yt-tile" key={id}>
            <VideoTile id={id} playing={playingVideoId === id} onPlay={() => onPlay(id)} isMobile={isMobile} />
          </div>
        ))}
      </div>
      <button
        style={arrowStyle(!canScrollNext)}
        onClick={() => scrollByPage(1)}
        disabled={!canScrollNext}
        aria-label="पुढील व्हिडिओ"
      >
        <RightOutlined />
      </button>
    </div>
  )
}

// One tile in the यूट्यूब चॅनल carousel. Renders a lightweight thumbnail +
// play badge (matching the same PlayCircleFilled affordance used for the
// audio book tiles above) until clicked. On desktop, clicking swaps just
// that tile to a live YouTube iframe — with 25+ videos in the shelf,
// embedding a real player for every tile up front would mean two dozen
// YouTube players loading at once; a thumbnail is one static image, and
// only the clicked video ever becomes a real embed. On mobile the tile
// instead links straight to the watch page (no inline iframe at all): the
// shelf only has room to show ~1 tile at a time on a phone, so a small
// inline embed inside that tile is cramped and can end up scrolled
// half-offscreen; letting the OS hand off to the YouTube app (or, absent
// the app, youtube.com's own full-width mobile player) gives a real
// fullscreen watch experience instead — same "let the native app take
// over" pattern already used for the podcast links above (`isMobile`).
function VideoTile({
  id,
  playing,
  onPlay,
  isMobile,
}: {
  id: string
  playing: boolean
  onPlay: () => void
  isMobile: boolean
}) {
  const { token } = antdTheme.useToken()
  if (playing) {
    return (
      <iframe
        title={`अमृतकण यूट्यूब व्हिडिओ ${id}`}
        src={`https://www.youtube-nocookie.com/embed/${id}?autoplay=1`}
        loading="lazy"
        allowFullScreen
        allow="autoplay; encrypted-media"
        style={{ width: '100%', aspectRatio: '16 / 9', border: 0, borderRadius: 8, display: 'block' }}
      />
    )
  }
  const thumbStyle: CSSProperties = {
    position: 'relative',
    width: '100%',
    aspectRatio: '16 / 9',
    border: 0,
    padding: 0,
    borderRadius: 8,
    overflow: 'hidden',
    cursor: 'pointer',
    display: 'block',
  }
  const thumbContent = (
    <>
      <img
        src={`https://img.youtube.com/vi/${id}/hqdefault.jpg`}
        alt=""
        draggable={false}
        style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
      />
      <span
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: 44,
          height: 44,
          borderRadius: '50%',
          background: token.colorPrimary,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <span
          style={{
            marginLeft: 4,
            width: 0,
            height: 0,
            borderTop: '9px solid transparent',
            borderBottom: '9px solid transparent',
            borderLeft: '14px solid #fff',
          }}
        />
      </span>
    </>
  )
  if (isMobile) {
    return (
      <a
        href={`https://www.youtube.com/watch?v=${id}`}
        aria-label="व्हिडिओ प्ले करा"
        style={thumbStyle}
      >
        {thumbContent}
      </a>
    )
  }
  return (
    <button onClick={onPlay} aria-label="व्हिडिओ प्ले करा" style={thumbStyle}>
      {thumbContent}
    </button>
  )
}

function Section({
  background,
  children,
}: {
  background: string
  children: ReactNode
}) {
  return (
    <section style={{ background, padding: '64px 24px' }}>
      <div style={{ maxWidth: 720, margin: '0 auto' }}>{children}</div>
    </section>
  )
}

export default function Home() {
  const [library, setLibrary] = useState<Library | null>(null)
  const [home, setHome] = useState<HomeContent | null>(null)
  const [pustake, setPustake] = useState<PustakBook[] | null>(null)
  // Which single tile in the यूट्यूब carousel (if any) has been clicked into
  // a live player — see VideoTile above.
  const [playingVideoId, setPlayingVideoId] = useState<string | null>(null)
  const isMobile = MOBILE_UA_RE.test(navigator.userAgent)
  const { token } = antdTheme.useToken()

  useEffect(() => {
    fetchLibrary().then(setLibrary)
    fetchHome().then(setHome)
    // Own fetch, own null state — the पुस्तके section renders once this
    // resolves regardless of library/home, no reason to block the rest of
    // the page on it.
    fetchPustake().then((data) => setPustake(data.books))
  }, [])

  if (!library || !home) {
    return (
      <Section background={token.colorBgContainer}>
        <Skeleton active avatar={{ shape: 'circle', size: 120 }} paragraph={{ rows: 2 }} />
        <Row gutter={[16, 16]} style={{ marginTop: 48 }}>
          <Col xs={24} sm={12}>
            <Skeleton.Button active block style={{ height: 96 }} />
          </Col>
          <Col xs={24} sm={12}>
            <Skeleton.Button active block style={{ height: 96 }} />
          </Col>
        </Row>
      </Section>
    )
  }

  return (
    <div>
      {/* अमृतकण + book links + podcast links: one continuous section, not
          three separate boxes — this is what's actually browsable/audible. */}
      <Section background={token.colorBgContainer}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}>
          <img
            src={home.tilakImage}
            alt="तिलक"
            style={{ width: 18, height: 'auto', marginTop: -24, marginBottom: 8 }}
          />
          <Typography.Paragraph style={{ fontWeight: 600, marginBottom: 40 }}>
            {home.tilakText}
          </Typography.Paragraph>
          <img
            src={home.heroImage}
            alt="श्री ज्ञानेश्वर माऊली"
            style={{ width: 120, height: 120, borderRadius: '50%', objectFit: 'cover' }}
          />
          <Typography.Title level={1} style={{ marginBottom: 8 }}>
            अमृतकण
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ fontSize: 16 }}>
            {home.tagline}
          </Typography.Paragraph>
          <ContinueListening library={library} />
        </div>

        <Row gutter={[16, 16]} style={{ marginTop: 48 }}>
          {library.books.map((book) => (
            <Col xs={24} sm={12} key={book.id}>
              <Link to={`/book/${book.id}`} className="tile-link">
                <div
                  style={{
                    background: token.colorFillTertiary,
                    borderRadius: 16,
                    padding: '28px 24px',
                    textAlign: 'center',
                  }}
                >
                  <PlayCircleFilled style={{ fontSize: 22, color: token.colorPrimary, marginBottom: 8 }} />
                  <Typography.Title level={3} style={{ marginTop: 0, marginBottom: 4 }}>
                    {book.name}
                  </Typography.Title>
                  <Typography.Text type="secondary">{toDevanagari(book.totalEpisodes)} भाग</Typography.Text>
                </div>
              </Link>
            </Col>
          ))}
        </Row>

        {home.podcastLinks.length > 0 && (
          <div style={{ marginTop: 48, textAlign: 'center' }}>
            <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
              निरूपण इथेही उपलब्ध
            </Typography.Text>
            <Space size={24} wrap style={{ justifyContent: 'center', display: 'flex' }}>
              {home.podcastLinks.map((link) => (
                <a
                  key={link.label}
                  href={link.url}
                  {...(isMobile ? {} : { target: '_blank', rel: 'noopener noreferrer' })}
                  style={{ display: 'flex', alignItems: 'center', gap: 8 }}
                >
                  <svg viewBox="0 0 24 24" fill={link.color} width={22} height={22}>
                    <path d={link.path} />
                  </svg>
                  {link.label}
                </a>
              ))}
            </Space>
          </div>
        )}
      </Section>

      {/* YouTube: its own section, own tint, so it reads as a distinct topic.
          Deliberately *not* using the Section helper above — everywhere
          else on the page commits to the 720px reading column, but a video
          shelf benefits from the room to show more tiles at once, so this
          section spans the full page width (same 24px edge padding as
          every other section, just no inner max-width cap). */}
      <section style={{ background: token.colorFillAlter, padding: '64px 24px' }}>
        <div style={{ textAlign: 'center' }}>
          <Typography.Title level={2}>अमृतकण चॅनल</Typography.Title>
          <Typography.Paragraph>
            <a href={home.youtube.channelUrl} target="_blank" rel="noopener noreferrer">
              {home.youtube.channelHandle} चॅनलला भेट द्या
            </a>
          </Typography.Paragraph>
        </div>
        {/* Shows the whole channel — as many entries as YOUTUBE_VIDEO_IDS
            holds, not just today's handful. See VideoShelf above for why
            this is a plain scroll-snap row instead of antd's Carousel. */}
        <div style={{ marginTop: 16 }}>
          <VideoShelf
            videoIds={home.youtube.videoIds}
            playingVideoId={playingVideoId}
            onPlay={setPlayingVideoId}
            isMobile={isMobile}
          />
        </div>
      </section>

      {/* पुस्तके: digital-only book reader, own section between YouTube and
          About. Only rendered once the fetch resolves with at least one
          book — thumbnailUrl is empty (and this stays hidden) if the page
          cache hasn't been built yet, see build_pustak_cache.py. */}
      {pustake && pustake.length > 0 && (
        <Section background={token.colorBgContainer}>
          <Typography.Title level={2} style={{ textAlign: 'center' }}>
            पुस्तके
          </Typography.Title>
          <Row gutter={[16, 16]} style={{ marginTop: 16, justifyContent: 'center' }}>
            {pustake.map((book) => (
              <Col xs={12} sm={8} key={book.id}>
                <Link to={`/pustak/${book.id}`} className="tile-link">
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ position: 'relative', borderRadius: 8, overflow: 'hidden' }}>
                      <img
                        className="pustak-cover-img"
                        src={book.thumbnailUrl}
                        alt={book.title}
                        draggable={false}
                        onContextMenu={(e) => e.preventDefault()}
                        style={{
                          width: '100%',
                          aspectRatio: '2 / 3',
                          objectFit: 'cover',
                          display: 'block',
                          boxShadow: token.boxShadow,
                        }}
                      />
                      <span
                        className="pustak-read-badge"
                        style={{
                          position: 'absolute',
                          left: 8,
                          bottom: 8,
                          width: 32,
                          height: 32,
                          borderRadius: '50%',
                          background: 'rgba(0, 0, 0, 0.45)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        <ReadFilled style={{ fontSize: 15, color: '#fff' }} />
                      </span>
                    </div>
                    <Typography.Text strong style={{ display: 'block', marginTop: 8 }}>
                      {book.title}
                    </Typography.Text>
                    {book.author && (
                      <Typography.Text type="secondary" style={{ fontSize: 13 }}>
                        {book.author}
                      </Typography.Text>
                    )}
                  </div>
                </Link>
              </Col>
            ))}
          </Row>
        </Section>
      )}

      {/* About: alternates tint again so it reads distinct from पुस्तके above it. */}
      <Section background={token.colorFillAlter}>
        <Typography.Title level={2} style={{ textAlign: 'center' }}>
          {home.aboutHeading}
        </Typography.Title>
        <Typography.Paragraph>{home.aboutText}</Typography.Paragraph>
        <Typography.Title level={4} style={{ textAlign: 'center' }}>
          {home.aboutMeHeading}
        </Typography.Title>
        {/* display: flow-root (not overflow: hidden) so the container
            properly contains the floated image without any risk of
            clipping — the modern, side-effect-free way to contain a float. */}
        <div style={{ marginTop: 16, display: 'flow-root' }}>
          <img
            src={home.aboutMePhoto}
            alt="Dr Suresh Kumar Chaudhari"
            style={{
              width: 140,
              height: 180,
              objectFit: 'cover',
              borderRadius: 14,
              float: 'left',
              marginRight: 16,
              marginBottom: 8,
            }}
          />
          <Typography.Paragraph>{home.aboutMeText}</Typography.Paragraph>
        </div>
      </Section>
    </div>
  )
}
