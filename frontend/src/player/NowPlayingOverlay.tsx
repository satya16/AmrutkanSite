import { Button, Drawer, Dropdown, Popover, Slider, Space, Typography, theme as antdTheme } from 'antd'
import type { MenuProps } from 'antd'
import type { ReactNode } from 'react'
import {
  DownloadOutlined,
  MinusOutlined,
  PauseCircleFilled,
  PlayCircleFilled,
  QuestionCircleOutlined,
  RedoOutlined,
  StepBackwardFilled,
  StepForwardFilled,
  UndoOutlined,
} from '@ant-design/icons'

const SKIP_SECONDS = 30

function SkipIcon({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <span style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', lineHeight: 1 }}>
      {icon}
      <span style={{ fontSize: 10, marginTop: 2 }}>{label}</span>
    </span>
  )
}
import { SPEED_PRESETS, formatTime, usePlayer } from './PlayerContext'

const SLEEP_OPTIONS: { value: 'episode' | number | 'off'; label: string }[] = [
  { value: 'episode', label: 'भाग संपल्यावर' },
  { value: 15, label: '१५ मिनिटे' },
  { value: 30, label: '३० मिनिटे' },
  { value: 45, label: '४५ मिनिटे' },
  { value: 60, label: '६० मिनिटे' },
  { value: 'off', label: 'बंद' },
]

export default function NowPlayingOverlay() {
  const player = usePlayer()
  const { token } = antdTheme.useToken()
  if (!player.currentSrc) return null

  const bufferedPct = player.duration ? (player.buffered / player.duration) * 100 : 0

  const speedMenu: MenuProps = {
    selectedKeys: [String(player.speed)],
    items: SPEED_PRESETS.map((v) => ({ key: String(v), label: `${v}×`, onClick: () => player.setSpeed(v) })),
  }
  const sleepSelectedKey =
    player.sleepMode === null ? 'off' : player.sleepMode === 'episode' ? 'episode' : String(player.sleepMode)
  const sleepMenu: MenuProps = {
    selectedKeys: [sleepSelectedKey],
    items: SLEEP_OPTIONS.map((opt) => ({
      key: String(opt.value),
      label: opt.label,
      onClick: () => player.setSleepOption(opt.value),
    })),
  }

  const filename = decodeURIComponent(player.currentSrc.split('/').pop() || '')

  return (
    <Drawer
      placement="bottom"
      height="100%"
      open={player.overlayOpen}
      onClose={player.closeOverlay}
      closable={false}
      title="आता वाजत आहे"
      extra={
        <Button
          type="text"
          icon={<MinusOutlined />}
          onClick={player.closeOverlay}
          aria-label="Minimize player"
        />
      }
      styles={{ body: { display: 'flex', flexDirection: 'column', padding: '16px 24px' } }}
    >
      <div style={{ textAlign: 'center', margin: '24px 0' }}>
        <img
          src="/static/mauli.jpg?v=2"
          alt=""
          style={{ width: 200, height: 200, borderRadius: 16, objectFit: 'cover' }}
        />
      </div>

      <div style={{ textAlign: 'center', marginBottom: 16 }}>
        <Typography.Title level={4} style={{ marginBottom: 0 }}>
          {player.currentLabel}
        </Typography.Title>
        {player.subtitle && <Typography.Text type="secondary">{player.subtitle}</Typography.Text>}
      </div>

      <div style={{ maxWidth: 480, width: '100%', margin: '0 auto' }}>
        <Slider
          min={0}
          max={player.duration || 0}
          value={player.currentTime}
          tooltip={{ formatter: (v) => formatTime(v ?? 0) }}
          onChange={(v) => player.seekTo(v)}
          styles={{
            // The played portion draws on top via the Slider's own track
            // (colorPrimary) up to `value`; this gradient just paints what's
            // underneath it — buffered-but-unplayed vs not-yet-loaded —
            // YouTube's "how much has loaded" bar, without extra DOM nodes.
            rail: {
              background: `linear-gradient(to right, ${token.colorFillSecondary} 0%, ${token.colorFillSecondary} ${bufferedPct}%, ${token.colorFillTertiary} ${bufferedPct}%, ${token.colorFillTertiary} 100%)`,
            },
          }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
          <span>{formatTime(player.currentTime)}</span>
          <span>{formatTime(player.duration)}</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 20, margin: '24px 0' }}>
          <Button
            type="text"
            icon={<SkipIcon icon={<UndoOutlined style={{ fontSize: 20 }} />} label={String(SKIP_SECONDS)} />}
            onClick={() => player.seekTo(Math.max(0, player.currentTime - SKIP_SECONDS))}
            aria-label={`${SKIP_SECONDS} सेकंद मागे`}
          />
          <Button
            type="text"
            icon={<StepBackwardFilled style={{ fontSize: 28 }} />}
            disabled={!player.playlist || player.currentIndex <= 0}
            onClick={player.playPrev}
            aria-label="Previous track"
          />
          <Button
            type="text"
            icon={
              player.isPlaying ? (
                <PauseCircleFilled style={{ fontSize: 56 }} />
              ) : (
                <PlayCircleFilled style={{ fontSize: 56 }} />
              )
            }
            onClick={player.togglePlay}
            aria-label="Play or pause"
          />
          <Button
            type="text"
            icon={<StepForwardFilled style={{ fontSize: 28 }} />}
            disabled={!player.playlist || player.currentIndex >= player.playlist.length - 1}
            onClick={player.playNext}
            aria-label="Next track"
          />
          <Button
            type="text"
            icon={<SkipIcon icon={<RedoOutlined style={{ fontSize: 20 }} />} label={String(SKIP_SECONDS)} />}
            onClick={() => player.seekTo(Math.min(player.duration || 0, player.currentTime + SKIP_SECONDS))}
            aria-label={`${SKIP_SECONDS} सेकंद पुढे`}
          />
        </div>

        <Space wrap style={{ justifyContent: 'center', width: '100%', display: 'flex' }}>
          <Dropdown menu={speedMenu} trigger={['click']}>
            <Button>गती {player.speed}×</Button>
          </Dropdown>
          <Dropdown menu={sleepMenu} trigger={['click']}>
            <Button>{player.sleepLabel}</Button>
          </Dropdown>
          <Button icon={<DownloadOutlined />} href={player.currentSrc} download={filename}>
            डाउनलोड
          </Button>
          <Popover
            title="मदत"
            trigger="click"
            content={
              <div style={{ maxWidth: 240 }}>
                <p>
                  <strong>गती</strong> — निरूपणाची गती
                </p>
                <p>
                  <strong>टायमर</strong> — निरूपण बंद करायचा टायमर
                </p>
                <p style={{ marginBottom: 0 }}>
                  <strong>डाउनलोड</strong> — भाग डाउनलोड करा
                </p>
              </div>
            }
          >
            <Button icon={<QuestionCircleOutlined />} aria-label="मदत" />
          </Popover>
        </Space>
      </div>
    </Drawer>
  )
}
