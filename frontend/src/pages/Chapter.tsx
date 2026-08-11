import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Breadcrumb, Button, List, Spin, Typography } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import { fetchLibrary, type Book, type Chapter, type Library } from '../api'

export default function ChapterPage() {
  const { bookId, slug } = useParams<{ bookId: string; slug: string }>()
  const [library, setLibrary] = useState<Library | null>(null)

  useEffect(() => {
    fetchLibrary().then(setLibrary)
  }, [])

  if (!library) {
    return (
      <div style={{ textAlign: 'center', padding: 64 }}>
        <Spin size="large" />
      </div>
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
        renderItem={(episode) => (
          <List.Item
            actions={[
              <a key="dl" href={episode.audioUrl} download={episode.filename} aria-label="डाउनलोड करा">
                <DownloadOutlined />
              </a>,
            ]}
          >
            {episode.label}
          </List.Item>
        )}
      />
    </>
  )
}
