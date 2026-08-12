import { Button, Typography, theme as antdTheme } from 'antd'
import { CheckCircleFilled, PlayCircleFilled } from '@ant-design/icons'
import type { Library } from '../api'
import { usePlayer } from '../player/PlayerContext'
import { loadProgress, resolveContinueListening } from '../continueListening'
import { buildBookPlaylist } from '../bookPlaylist'

export default function ContinueListening({ library }: { library: Library }) {
  const player = usePlayer()
  const { token } = antdTheme.useToken()

  // Deliberately recomputed on every render rather than cached in useState —
  // usePlayer() re-renders this component whenever playback state changes
  // (e.g. auto-advancing to the next episode), and ak_progress in
  // localStorage is already up to date by then since PlayerContext writes it
  // synchronously before that re-render happens. Caching it in state at mount
  // time made this button go stale the moment playback moved on without a
  // navigation to remount the component.
  const progress = loadProgress()
  const state = progress ? resolveContinueListening(library, progress) : null

  if (!state) return null

  if (state.mode === 'finished') {
    return (
      <div
        style={{
          margin: '32px auto 0',
          width: '100%',
          maxWidth: 420,
          padding: '16px 20px',
          borderRadius: 12,
          background: token.colorFillTertiary,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}
      >
        <CheckCircleFilled style={{ fontSize: 22, color: token.colorTextSecondary }} />
        <Typography.Text type="secondary">तुम्ही {state.book.name} पूर्ण ऐकले आहे</Typography.Text>
      </div>
    )
  }

  const isResume = state.mode === 'resume'
  const caption = isResume ? 'ऐकणे सुरू ठेवा' : 'पुढचा भाग ऐका'
  const playlist = buildBookPlaylist(state.book)
  const index = playlist.findIndex((p) => p.src === state.episode.audioUrl)

  const handleClick = () => {
    player.play(state.episode.audioUrl, state.episode.label, {
      subtitle: `${state.book.name} · ${state.chapter.label}`,
      playlist,
      index,
      bookId: state.book.id,
      resumeTime: isResume ? state.resumeTime : undefined,
    })
  }

  return (
    <Button
      type="primary"
      onClick={handleClick}
      style={{
        margin: '32px auto 0',
        height: 'auto',
        width: '100%',
        maxWidth: 420,
        padding: '14px 20px',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        textAlign: 'left',
      }}
    >
      <PlayCircleFilled style={{ fontSize: 26 }} />
      <span style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.4 }}>
        <span style={{ fontSize: 12, opacity: 0.85 }}>{caption}</span>
        <span style={{ fontSize: 15, fontWeight: 600 }}>{state.episode.label}</span>
      </span>
    </Button>
  )
}
