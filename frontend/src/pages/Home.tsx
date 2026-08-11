import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Col, Row, Skeleton, Space, Typography, theme as antdTheme } from 'antd'
import { fetchHome, fetchLibrary, type HomeContent, type Library } from '../api'
import { toDevanagari } from '../devanagari'

const MOBILE_UA_RE = /iphone|ipad|ipod|android/i

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
  const isMobile = MOBILE_UA_RE.test(navigator.userAgent)
  const { token } = antdTheme.useToken()

  useEffect(() => {
    fetchLibrary().then(setLibrary)
    fetchHome().then(setHome)
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
        <div style={{ textAlign: 'center' }}>
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

      {/* YouTube: its own section, own tint, so it reads as a distinct topic. */}
      <Section background={token.colorFillAlter}>
        <div style={{ textAlign: 'center' }}>
          <Typography.Title level={2}>यूट्यूब चॅनल</Typography.Title>
          <Typography.Paragraph>
            <a href={home.youtube.channelUrl} target="_blank" rel="noopener noreferrer">
              {home.youtube.channelHandle} चॅनलला भेट द्या
            </a>
          </Typography.Paragraph>
        </div>
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          {home.youtube.videoIds.map((id) => (
            <Col xs={24} sm={12} key={id}>
              <iframe
                title={`अमृतकण यूट्यूब व्हिडिओ ${id}`}
                src={`https://www.youtube-nocookie.com/embed/${id}`}
                loading="lazy"
                allowFullScreen
                style={{ width: '100%', aspectRatio: '16 / 9', border: 0, borderRadius: 8 }}
              />
            </Col>
          ))}
        </Row>
      </Section>

      {/* About: its own section again, back to the base tint. */}
      <Section background={token.colorBgContainer}>
        <Typography.Title level={2} style={{ textAlign: 'center' }}>
          आमच्याबद्दल
        </Typography.Title>
        <Typography.Paragraph>{home.aboutText}</Typography.Paragraph>
        <Space align="start" size={16} wrap style={{ marginTop: 16 }}>
          <img
            src={home.aboutMePhoto}
            alt="Dr Suresh Kumar Chaudhari"
            style={{ width: 140, height: 180, objectFit: 'cover', borderRadius: 14 }}
          />
          <Typography.Paragraph style={{ flex: 1, minWidth: 200 }}>{home.aboutMeText}</Typography.Paragraph>
        </Space>
      </Section>
    </div>
  )
}
