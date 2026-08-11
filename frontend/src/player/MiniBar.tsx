import { PauseCircleFilled, PlayCircleFilled } from '@ant-design/icons'
import { usePlayer } from './PlayerContext'

export default function MiniBar() {
  const player = usePlayer()
  if (!player.currentSrc) return null

  const pct = player.duration ? (player.currentTime / player.duration) * 100 : 0

  return (
    <div
      onClick={player.openOverlay}
      style={{
        position: 'fixed',
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 100,
        background: '#1f1f1f',
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '8px 16px',
        cursor: 'pointer',
      }}
    >
      <span
        onClick={(e) => {
          e.stopPropagation()
          player.togglePlay()
        }}
        style={{ fontSize: 32, display: 'flex', color: '#fff' }}
        aria-label="Play or pause"
      >
        {player.isPlaying ? <PauseCircleFilled /> : <PlayCircleFilled />}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            fontSize: 14,
          }}
        >
          {player.currentLabel}
        </div>
        <div style={{ height: 3, background: 'rgba(255,255,255,0.2)', borderRadius: 2, marginTop: 4 }}>
          <div style={{ height: '100%', width: `${pct}%`, background: '#e8935a', borderRadius: 2 }} />
        </div>
      </div>
    </div>
  )
}
