import { useEffect } from 'react'
import { App as AntApp, Button, ConfigProvider, Layout, Space, Switch, theme as antdTheme, Typography } from 'antd'
import { MoonOutlined, ShareAltOutlined, SunOutlined } from '@ant-design/icons'
import { Link, Route, Routes, useLocation } from 'react-router-dom'
import { useDarkMode } from './useDarkMode'
import { PlayerProvider, usePlayer } from './player/PlayerContext'
import MiniBar from './player/MiniBar'
import NowPlayingOverlay from './player/NowPlayingOverlay'
import Home from './pages/Home'
import BookPage from './pages/Book'
import ChapterPage from './pages/Chapter'
import { ACCENT } from './theme'

// Reserved space below page content when the mini-bar is showing — taller
// than the bar's own ~51px so there's real breathing room, plus the iOS
// home-indicator safe area (0 on devices/browsers without one).
const MINI_BAR_CLEARANCE = 'calc(96px + env(safe-area-inset-bottom))'

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
  const { message } = AntApp.useApp()
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
    try {
      await navigator.clipboard.writeText(shareData.url)
      message.success('लिंक कॉपी केली')
    } catch {
      message.error('लिंक कॉपी करता आली नाही')
    }
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
        <Space size={4}>
          <Button
            type="text"
            icon={<ShareAltOutlined style={{ color: '#fff', fontSize: 18 }} />}
            onClick={handleShare}
            aria-label="Share this page"
          />
          <Switch
            checked={dark}
            onChange={toggleDark}
            checkedChildren={<MoonOutlined />}
            unCheckedChildren={<SunOutlined />}
            aria-label="Toggle dark mode"
          />
        </Space>
      </Layout.Header>
      <Layout.Content
        style={
          isHome
            ? { paddingBottom: player.currentSrc ? MINI_BAR_CLEARANCE : 0, width: '100%' }
            : {
                padding: '24px 16px',
                paddingBottom: player.currentSrc ? MINI_BAR_CLEARANCE : 24,
                maxWidth: 960,
                margin: '0 auto',
                width: '100%',
              }
        }
      >
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/book/:bookId" element={<BookPage />} />
          <Route path="/book/:bookId/:slug" element={<ChapterPage />} />
        </Routes>
      </Layout.Content>
      <MiniBar />
      <NowPlayingOverlay />
    </Layout>
  )
}
