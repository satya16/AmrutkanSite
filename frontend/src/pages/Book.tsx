import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Breadcrumb, Button, Card, Col, Result, Row, Typography } from 'antd'
import { DownloadOutlined, FolderOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { fetchLibrary, type Book, type Library } from '../api'
import { toDevanagari } from '../devanagari'

export default function BookPage() {
  const { bookId } = useParams<{ bookId: string }>()
  const [library, setLibrary] = useState<Library | null>(null)

  useEffect(() => {
    fetchLibrary().then(setLibrary)
  }, [])

  if (!library) {
    return (
      <Row gutter={[16, 16]}>
        {Array.from({ length: 8 }).map((_, i) => (
          <Col xs={12} sm={8} md={6} key={i}>
            <Card loading size="small" />
          </Col>
        ))}
      </Row>
    )
  }

  const book: Book | undefined = library.books.find((b) => b.id === bookId)
  if (!book) {
    return (
      <Result
        status="404"
        title="ग्रंथ सापडला नाही"
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
        items={[{ title: <Link to="/">अमृतकण</Link> }, { title: book.name }]}
        style={{ marginBottom: 16 }}
      />
      <Typography.Title level={2}>{book.name}</Typography.Title>
      <Button
        icon={<DownloadOutlined />}
        href={`/download/book/${book.id}`}
        download={`${book.id}.zip`}
        style={{ marginBottom: 16 }}
      >
        संपूर्ण ग्रंथ डाउनलोड करा (ZIP)
      </Button>
      <Row gutter={[16, 16]}>
        {book.chapters.map((chapter) => (
          <Col xs={12} sm={8} md={6} key={chapter.slug}>
            <Link to={`/book/${book.id}/${chapter.slug}`}>
              <Card hoverable size="small">
                <Typography.Text strong>
                  {chapter.episodeCount === 1 ? <PlayCircleOutlined /> : <FolderOutlined />} {chapter.label}
                </Typography.Text>
                {chapter.episodeCount !== 1 && (
                  <>
                    <br />
                    <Typography.Text type="secondary">{toDevanagari(chapter.episodeCount)} भाग</Typography.Text>
                  </>
                )}
              </Card>
            </Link>
          </Col>
        ))}
      </Row>
    </>
  )
}
