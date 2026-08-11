import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Breadcrumb, Button, List, Skeleton, Typography } from 'antd'
import { DownloadOutlined, PauseCircleFilled, PlayCircleFilled } from '@ant-design/icons'
import { fetchLibrary, type Book, type Chapter, type Library } from '../api'
import { usePlayer } from '../player/PlayerContext'

export default function ChapterPage() {
  const { bookId, slug } = useParams<{ bookId: string; slug: string }>()
  const [library, setLibrary] = useState<Library | null>(null)
  const player = usePlayer()

  useEffect(() => {
    fetchLibrary().then(setLibrary)
  }, [])

  if (!library) {
    return (
      <List
        bordered
        dataSource={Array.from({ length: 6 }, (_, i) => i)}
        renderItem={(i) => (
          <List.Item key={i}>
            <Skeleton active title={false} paragraph={{ rows: 1, width: '60%' }} />
          </List.Item>
        )}
      />
    )
  }

  const book: Book | undefined = library.books.find((b) => b.id === bookId)
  const chapter: Chapter | undefined = book?.chapters.find((c) => c.slug === slug)
  if (!book || !chapter) {
    return <Typography.Paragraph>भाग सापडला नाही.</Typography.Paragraph>
  }

  return (
    <>
      <Breadcrumb
        items={[
          { title: <Link to="/">अमृतकण</Link> },
          { title: <Link to={`/book/${book.id}`}>{book.name}</Link> },
          { title: chapter.label },
        ]}
        style={{ marginBottom: 16 }}
      />
      <Typography.Title level={2}>{chapter.label}</Typography.Title>
      <Button
        icon={<DownloadOutlined />}
        href={`/download/book/${book.id}/${chapter.slug}`}
        download={`${book.id}-${chapter.slug}.zip`}
        style={{ marginBottom: 16 }}
      >
        संपूर्ण {chapter.label} डाउनलोड करा (ZIP)
      </Button>
      <List
        bordered
        dataSource={chapter.episodes}
        renderItem={(episode, index) => {
          const isCurrent = player.currentSrc === episode.audioUrl
          return (
            <List.Item
              onClick={() =>
                player.play(episode.audioUrl, episode.label, {
                  subtitle: `${book.name} · ${chapter.label}`,
                  playlist: chapter.episodes.map((e) => ({ src: e.audioUrl, label: e.label })),
                  index,
                })
              }
              style={{ cursor: 'pointer' }}
              actions={[
                <a
                  key="dl"
                  href={episode.audioUrl}
                  download={episode.filename}
                  aria-label="डाउनलोड करा"
                  onClick={(e) => e.stopPropagation()}
                >
                  <DownloadOutlined />
                </a>,
              ]}
            >
              <Typography.Text strong={isCurrent}>
                {isCurrent ? (
                  player.isPlaying ? (
                    <PauseCircleFilled style={{ marginRight: 8 }} />
                  ) : (
                    <PlayCircleFilled style={{ marginRight: 8 }} />
                  )
                ) : null}
                {episode.label}
              </Typography.Text>
            </List.Item>
          )
        }}
      />
    </>
  )
}
