import { useEffect } from 'react'
import { App as AntApp, Button, ConfigProvider, Layout, Switch, theme as antdTheme, Typography } from 'antd'
import { MoonOutlined, ShareAltOutlined, SunOutlined } from '@ant-design/icons'
import { Link, Route, Routes, useLocation } from 'react-router-dom'
import { useDarkMode } from './useDarkMode'
import { PlayerProvider, usePlayer } from './player/PlayerContext'
import MiniBar from './player/MiniBar'
import NowPlayingOverlay from './player/NowPlayingOverlay'
import Home from './pages/Home'
import BookPage from './pages/Book'
import ChapterPage from './pages/Chapter'
import PustakPage from './pages/Pustak'
import FeedbackButton from './components/FeedbackButton'
import { ACCENT } from './theme'

// Reserved space below page content when the mini-bar is showing — taller
// than the bar's own ~51px so there's real breathing room, plus the iOS
// home-indicator safe area (0 on devices/browsers without one).
const MINI_BAR_CLEARANCE = 'calc(96px + env(safe-area-inset-bottom))'

// Some in-app browsers (WhatsApp/Instagram/Facebook's built-in webview,
// common for a site shared mostly via chat links) restrict or omit both
// navigator.share and the modern Clipboard API. document.execCommand is
// deprecated but still works in far more of those restricted contexts, so
// it's a worthwhile second-chance fallback before giving up entirely.
async function copyToClipboard(text: string): Promise<boolean> {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // fall through to the legacy method below
    }
  }
  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.focus()
    textarea.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(textarea)
    return ok
  } catch {
    return false
  }
}

export default function App() {
  const [dark, toggleDark] = useDarkMode()

  return (
    <ConfigProvider
      theme={{
        algorithm: dark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
        token: { colorPrimary: ACCENT, borderRadius: 10 },
      }}
    >
      <AntApp>
        <PlayerProvider>
          <AppShell dark={dark} toggleDark={toggleDark} />
        </PlayerProvider>
      </AntApp>
    </ConfigProvider>
  )
}

function AppShell({ dark, toggleDark }: { dark: boolean; toggleDark: () => void }) {
  const player = usePlayer()
  const { token } = antdTheme.useToken()
  const { message, modal } = AntApp.useApp()
  const isHome = useLocation().pathname === '/'

  // Keep the real <body> background in sync with antd's theme so mobile
  // overscroll/bounce reveals the right color instead of the browser's
  // default white beneath the themed Layout.
  useEffect(() => {
    document.body.style.background = token.colorBgLayout
    document.documentElement.style.colorScheme = dark ? 'dark' : 'light'
  }, [token.colorBgLayout, dark])

  const handleShare = async () => {
    const shareData = { title: document.title, url: window.location.href }
    if (navigator.share) {
      try {
        await navigator.share(shareData)
      } catch {
        // user cancelled the native share sheet — not an error
      }
      return
    }
    if (await copyToClipboard(shareData.url)) {
      message.success('लिंक कॉपी केली')
      return
    }
    // Both the Clipboard API and the execCommand fallback were blocked
    // (common in some in-app browsers) — show the link as selectable text
    // so the user can still copy it by hand. This always works.
    modal.info({
      title: 'लिंक शेअर करा',
      content: (
        <Typography.Paragraph copyable={{ text: shareData.url }} style={{ wordBreak: 'break-all', marginBottom: 0 }}>
          {shareData.url}
        </Typography.Paragraph>
      ),
      okText: 'ठीक आहे',
    })
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Layout.Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
          position: 'sticky',
          top: 0,
          zIndex: 10,
        }}
      >
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <img
            src="/static/mauli.jpg?v=2"
            alt="Dnyaneshwar Mauli"
            style={{ width: 36, height: 36, borderRadius: '50%', objectFit: 'cover' }}
          />
          <Typography.Title level={4} style={{ color: '#fff', margin: 0 }}>
            अमृतकण
          </Typography.Title>
        </Link>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <FeedbackButton />
          <Button
            type="text"
            icon={<ShareAltOutlined style={{ color: '#fff', fontSize: 16 }} />}
            onClick={handleShare}
            aria-label="Share this page"
            style={{ width: 22, height: 22, minWidth: 22, padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          />
          <Switch
            checked={dark}
            onChange={toggleDark}
            checkedChildren={<MoonOutlined />}
            unCheckedChildren={<SunOutlined />}
            aria-label="Toggle dark mode"
          />
        </div>
      </Layout.Header>
      <Layout.Content
        style={
          isHome
            ? { width: '100%' }
            : { padding: '24px 16px', maxWidth: 960, margin: '0 auto', width: '100%' }
        }
      >
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/book/:bookId" element={<BookPage />} />
          <Route path="/book/:bookId/:slug" element={<ChapterPage />} />
          <Route path="/pustak/:bookId" element={<PustakPage />} />
        </Routes>
      </Layout.Content>
      <Layout.Footer
        style={{
          textAlign: 'center',
          paddingBottom: player.currentSrc ? MINI_BAR_CLEARANCE : 24,
        }}
      >
        <div>॥ राम कृष्ण हरी ॥</div>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          © {new Date().getFullYear()} अमृतकण. सर्व हक्क राखीव.
        </Typography.Text>
      </Layout.Footer>
      <MiniBar />
      <NowPlayingOverlay />
    </Layout>
  )
}
