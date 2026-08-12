import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Breadcrumb, Button, List, Result, Skeleton, Typography } from 'antd'
import { DownloadOutlined, PauseCircleFilled, PlayCircleFilled, PlayCircleOutlined } from '@ant-design/icons'
import { fetchLibrary, type Book, type Chapter, type Library } from '../api'
import { usePlayer } from '../player/PlayerContext'
import { buildBookPlaylist } from '../bookPlaylist'
import { ACCENT } from '../theme'

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
    return (
      <Result
        status="404"
        title="भाग सापडला नाही"
        extra={
          <Link to="/">
            <Button type="primary">मुख्य पानावर जा</Button>
          </Link>
        }
      />
    )
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
        renderItem={(episode) => {
          const isCurrent = player.currentSrc === episode.audioUrl
          const playIcon = isCurrent ? (
            player.isPlaying ? (
              <PauseCircleFilled style={{ fontSize: 22, color: ACCENT }} />
            ) : (
              <PlayCircleFilled style={{ fontSize: 22, color: ACCENT }} />
            )
          ) : (
            <PlayCircleOutlined style={{ fontSize: 22, color: ACCENT }} />
          )
          return (
            <List.Item
              className="episode-item"
              onClick={() => {
                const playlist = buildBookPlaylist(book)
                player.play(episode.audioUrl, episode.label, {
                  subtitle: `${book.name} · ${chapter.label}`,
                  playlist,
                  index: playlist.findIndex((p) => p.src === episode.audioUrl),
                  bookId: book.id,
                })
              }}
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
              <List.Item.Meta
                avatar={playIcon}
                title={<Typography.Text strong={isCurrent}>{episode.label}</Typography.Text>}
              />
            </List.Item>
          )
        }}
      />
    </>
  )
}
