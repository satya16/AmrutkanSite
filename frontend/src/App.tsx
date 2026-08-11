import { useEffect } from 'react'
import { ConfigProvider, Layout, Switch, theme as antdTheme, Typography } from 'antd'
import { MoonOutlined, SunOutlined } from '@ant-design/icons'
import { Link, Route, Routes, useLocation } from 'react-router-dom'
import { useDarkMode } from './useDarkMode'
import { PlayerProvider, usePlayer } from './player/PlayerContext'
import MiniBar from './player/MiniBar'
import NowPlayingOverlay from './player/NowPlayingOverlay'
import Home from './pages/Home'
import BookPage from './pages/Book'
import ChapterPage from './pages/Chapter'
import { ACCENT } from './theme'

export default function App() {
  const [dark, toggleDark] = useDarkMode()

  return (
    <ConfigProvider
      theme={{
        algorithm: dark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
        token: { colorPrimary: ACCENT, borderRadius: 10 },
      }}
    >
      <PlayerProvider>
        <AppShell dark={dark} toggleDark={toggleDark} />
      </PlayerProvider>
    </ConfigProvider>
  )
}

function AppShell({ dark, toggleDark }: { dark: boolean; toggleDark: () => void }) {
  const player = usePlayer()
  const { token } = antdTheme.useToken()
  const isHome = useLocation().pathname === '/'

  // Keep the real <body> background in sync with antd's theme so mobile
  // overscroll/bounce reveals the right color instead of the browser's
  // default white beneath the themed Layout.
  useEffect(() => {
    document.body.style.background = token.colorBgLayout
    document.documentElement.style.colorScheme = dark ? 'dark' : 'light'
  }, [token.colorBgLayout, dark])

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
        <Switch
          checked={dark}
          onChange={toggleDark}
          checkedChildren={<MoonOutlined />}
          unCheckedChildren={<SunOutlined />}
          aria-label="Toggle dark mode"
        />
      </Layout.Header>
      <Layout.Content
        style={
          isHome
            ? { paddingBottom: player.currentSrc ? 80 : 0, width: '100%' }
            : {
                padding: '24px 16px',
                paddingBottom: player.currentSrc ? 80 : 24,
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
