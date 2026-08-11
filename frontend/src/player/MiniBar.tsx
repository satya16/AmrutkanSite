import { Progress } from 'antd'
import { CloseOutlined, PauseCircleFilled, PlayCircleFilled } from '@ant-design/icons'
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
        padding: '8px 16px calc(8px + env(safe-area-inset-bottom))',
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
        <Progress
          percent={pct}
          showInfo={false}
          size="small"
          strokeColor="#e8935a"
          trailColor="rgba(255,255,255,0.2)"
          style={{ marginTop: 4, lineHeight: 0 }}
        />
      </div>
      <span
        onClick={(e) => {
          e.stopPropagation()
          player.stop()
        }}
        style={{ fontSize: 18, display: 'flex', color: '#fff', opacity: 0.75 }}
        aria-label="Close player"
      >
        <CloseOutlined />
      </span>
    </div>
  )
}
