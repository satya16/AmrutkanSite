import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, Col, Row, Space, Typography } from 'antd'
import { fetchHome, fetchLibrary, type HomeContent, type Library } from '../api'
import { toDevanagari } from '../devanagari'

const MOBILE_UA_RE = /iphone|ipad|ipod|android/i

export default function Home() {
  const [library, setLibrary] = useState<Library | null>(null)
  const [home, setHome] = useState<HomeContent | null>(null)
  const isMobile = MOBILE_UA_RE.test(navigator.userAgent)

  useEffect(() => {
    fetchLibrary().then(setLibrary)
    fetchHome().then(setHome)
  }, [])

  if (!library || !home) {
    // Card's `loading` prop renders a content-shaped skeleton in place of
    // its children — mirroring the real layout below (hero, book grid,
    // three more section cards) avoids a layout jump once data arrives.
    return (
      <Space orientation="vertical" size={32} style={{ width: '100%' }}>
        <Card loading />
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12}>
            <Card loading />
          </Col>
          <Col xs={24} sm={12}>
            <Card loading />
          </Col>
        </Row>
        <Card loading />
        <Card loading />
        <Card loading />
      </Space>
    )
  }

  return (
    <Space orientation="vertical" size={32} style={{ width: '100%' }}>
      <Card style={{ textAlign: 'center' }}>
        <img
          src={home.heroImage}
          alt="श्री ज्ञानेश्वर माऊली"
          style={{ width: 120, height: 120, borderRadius: '50%', objectFit: 'cover' }}
        />
        <Typography.Title level={1}>अमृतकण</Typography.Title>
        <Typography.Paragraph type="secondary">{home.tagline}</Typography.Paragraph>
      </Card>

      <Row gutter={[16, 16]}>
        {library.books.map((book) => (
          <Col xs={24} sm={12} key={book.id}>
            <Link to={`/book/${book.id}`}>
              <Card hoverable>
                <Typography.Title level={3} style={{ marginTop: 0 }}>
                  {book.name}
                </Typography.Title>
                <Typography.Text type="secondary">{toDevanagari(book.totalEpisodes)} भाग</Typography.Text>
              </Card>
            </Link>
          </Col>
        ))}
      </Row>

      {home.podcastLinks.length > 0 && (
        <Card>
          <Typography.Title level={4}>निरूपण इथेही उपलब्ध</Typography.Title>
          <Space size={16} wrap>
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
        </Card>
      )}

      <Card>
        <Typography.Title level={4}>यूट्यूब चॅनल</Typography.Title>
        <Typography.Paragraph>
          <a href={home.youtube.channelUrl} target="_blank" rel="noopener noreferrer">
            {home.youtube.channelHandle} चॅनलला भेट द्या
          </a>
        </Typography.Paragraph>
        <Row gutter={[16, 16]}>
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
      </Card>

      <Card>
        <Typography.Title level={4}>आमच्याबद्दल</Typography.Title>
        <Typography.Paragraph>{home.aboutText}</Typography.Paragraph>
        <Space align="start" size={16} wrap>
          <img
            src={home.aboutMePhoto}
            alt="Dr Suresh Kumar Chaudhari"
            style={{ width: 140, height: 180, objectFit: 'cover', borderRadius: 14 }}
          />
          <Typography.Paragraph style={{ flex: 1, minWidth: 200 }}>{home.aboutMeText}</Typography.Paragraph>
        </Space>
      </Card>
    </Space>
  )
}
