import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useReducer,
  useRef,
} from 'react'
import type { ReactNode } from 'react'
import { formatTime } from './format'
import { toDevanagari } from '../devanagari'

export interface PlaylistItem {
  src: string
  label: string
  // Per-item subtitle so playNext/playPrev show the right book/chapter
  // as the queue crosses chapter boundaries (a whole-book playlist mixes
  // items from several chapters — see bookPlaylist.ts).
  subtitle?: string
}

export type SleepMode = 'episode' | number | null

interface PlaySnapshot {
  currentSrc: string | null
  currentLabel: string
  subtitle: string
  playlist: PlaylistItem[] | null
  currentIndex: number
  bookId: string
  isPlaying: boolean
  currentTime: number
  duration: number
  buffered: number
  speed: number
  sleepMode: SleepMode
  sleepRemainingMin: number | null
  overlayOpen: boolean
}

interface PlayOpts {
  subtitle?: string
  playlist?: PlaylistItem[]
  index?: number
  bookId?: string
  // Only meaningful when switching to a new src (e.g. the "continue
  // listening" button resuming a paused episode from a previous visit).
  resumeTime?: number
}

export const SPEED_PRESETS = [0.75, 1, 1.25, 1.5, 1.75, 2]
const SPEED_KEY = 'ak_speed'
const PLAYBACK_KEY = 'ak_playback'
// Book-level "continue listening" progress — separate from PLAYBACK_KEY
// (which is playlist/chapter-scoped) since this needs to survive across
// chapter boundaries so Home can resolve "resume" vs "next episode" vs
// "book finished" without depending on whatever playlist happens to be
// loaded right now.
const PROGRESS_KEY = 'ak_progress'

export interface SavedProgress {
  bookId: string
  filename: string
  completed: boolean
  currentTime: number
}

function filenameFromSrc(src: string): string {
  const marker = '/audio/'
  const i = src.indexOf(marker)
  return i === -1 ? src : decodeURIComponent(src.slice(i + marker.length))
}

interface PlayerContextValue extends PlaySnapshot {
  play: (src: string, label: string, opts?: PlayOpts) => void
  togglePlay: () => void
  playPrev: () => void
  playNext: () => void
  seekTo: (time: number) => void
  setSpeed: (value: number) => void
  setSleepOption: (value: 'off' | 'episode' | number) => void
  openOverlay: () => void
  closeOverlay: () => void
  stop: () => void
  sleepLabel: string
}

const PlayerContext = createContext<PlayerContextValue | null>(null)

function initialSpeed(): number {
  const saved = parseFloat(localStorage.getItem(SPEED_KEY) || '')
  return SPEED_PRESETS.includes(saved) ? saved : 1
}

function loadSavedPlayback(): Partial<PlaySnapshot> & { resumeTime: number } | null {
  try {
    const saved = JSON.parse(localStorage.getItem(PLAYBACK_KEY) || 'null')
    if (!saved || !saved.src) return null
    return {
      currentSrc: saved.src,
      currentLabel: saved.label || '',
      subtitle: saved.subtitle || '',
      playlist: saved.playlist || null,
      currentIndex: typeof saved.index === 'number' ? saved.index : -1,
      resumeTime: saved.currentTime || 0,
    }
  } catch {
    return null
  }
}

export function PlayerProvider({ children }: { children: ReactNode }) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [, forceRender] = useReducer((x: number) => x + 1, 0)
  const stateRef = useRef<PlaySnapshot>({
    currentSrc: null,
    currentLabel: '',
    subtitle: '',
    playlist: null,
    currentIndex: -1,
    bookId: '',
    isPlaying: false,
    currentTime: 0,
    duration: 0,
    buffered: 0,
    speed: initialSpeed(),
    sleepMode: 'episode',
    sleepRemainingMin: null,
    overlayOpen: false,
  })
  const resumeTimeRef = useRef(0)
  const lastSaveAtRef = useRef(0)
  const sleepEndAtRef = useRef(0)

  const update = useCallback((patch: Partial<PlaySnapshot>) => {
    stateRef.current = { ...stateRef.current, ...patch }
    forceRender()
  }, [])

  const saveProgress = useCallback((completed: boolean) => {
    const s = stateRef.current
    if (!s.currentSrc || !s.bookId) return
    localStorage.setItem(
      PROGRESS_KEY,
      JSON.stringify({
        bookId: s.bookId,
        filename: filenameFromSrc(s.currentSrc),
        completed,
        currentTime: completed ? 0 : (audioRef.current?.currentTime ?? 0),
      } satisfies SavedProgress),
    )
  }, [])

  const savePlayback = useCallback(() => {
    const s = stateRef.current
    if (!s.currentSrc || !audioRef.current) return
    lastSaveAtRef.current = Date.now()
    localStorage.setItem(
      PLAYBACK_KEY,
      JSON.stringify({
        src: s.currentSrc,
        label: s.currentLabel,
        subtitle: s.subtitle,
        playlist: s.playlist,
        index: s.currentIndex,
        currentTime: audioRef.current.currentTime,
      }),
    )
    saveProgress(false)
  }, [saveProgress])

  const play = useCallback(
    (src: string, label: string, opts: PlayOpts = {}) => {
      const audio = audioRef.current
      if (!audio) return
      const s = stateRef.current
      const patch: Partial<PlaySnapshot> = {}
      if (s.currentSrc !== src) {
        audio.src = src
        audio.playbackRate = s.speed
        patch.currentSrc = src
        patch.currentLabel = label
        patch.bookId = opts.bookId ?? ''
        resumeTimeRef.current = opts.resumeTime || 0
      }
      if (opts.subtitle !== undefined) patch.subtitle = opts.subtitle
      if (opts.playlist !== undefined) {
        patch.playlist = opts.playlist
        patch.currentIndex = opts.index ?? -1
      }
      update(patch)
      audio.play()
      savePlayback()
    },
    [update, savePlayback],
  )

  const togglePlay = useCallback(() => {
    const audio = audioRef.current
    if (!audio || !stateRef.current.currentSrc) return
    if (audio.paused) audio.play()
    else audio.pause()
  }, [])

  const playPrev = useCallback(() => {
    const s = stateRef.current
    if (!s.playlist || s.currentIndex <= 0) return
    const item = s.playlist[s.currentIndex - 1]
    play(item.src, item.label, {
      subtitle: item.subtitle ?? s.subtitle,
      playlist: s.playlist,
      index: s.currentIndex - 1,
      bookId: s.bookId,
    })
  }, [play])

  const playNext = useCallback(() => {
    const s = stateRef.current
    if (!s.playlist || s.currentIndex >= s.playlist.length - 1) return
    const item = s.playlist[s.currentIndex + 1]
    play(item.src, item.label, {
      subtitle: item.subtitle ?? s.subtitle,
      playlist: s.playlist,
      index: s.currentIndex + 1,
      bookId: s.bookId,
    })
  }, [play])

  const seekTo = useCallback((time: number) => {
    const audio = audioRef.current
    if (!audio) return
    audio.currentTime = time
    update({ currentTime: time })
  }, [update])

  const setSpeed = useCallback(
    (value: number) => {
      const audio = audioRef.current
      if (audio) audio.playbackRate = value
      localStorage.setItem(SPEED_KEY, String(value))
      update({ speed: value })
    },
    [update],
  )

  const setSleepOption = useCallback(
    (value: 'off' | 'episode' | number) => {
      if (value === 'off') {
        sleepEndAtRef.current = 0
        update({ sleepMode: null, sleepRemainingMin: null })
      } else if (value === 'episode') {
        sleepEndAtRef.current = 0
        update({ sleepMode: 'episode', sleepRemainingMin: null })
      } else {
        sleepEndAtRef.current = Date.now() + value * 60000
        update({ sleepMode: value, sleepRemainingMin: value })
      }
    },
    [update],
  )

  const openOverlay = useCallback(() => {
    if (!stateRef.current.currentSrc) return
    update({ overlayOpen: true })
  }, [update])
  const closeOverlay = useCallback(() => update({ overlayOpen: false }), [update])

  const stop = useCallback(() => {
    const audio = audioRef.current
    if (audio) {
      audio.pause()
      audio.removeAttribute('src')
      audio.load()
    }
    sleepEndAtRef.current = 0
    localStorage.removeItem(PLAYBACK_KEY)
    if ('mediaSession' in navigator) {
      navigator.mediaSession.metadata = null
      navigator.mediaSession.playbackState = 'none'
    }
    update({
      currentSrc: null,
      currentLabel: '',
      subtitle: '',
      playlist: null,
      currentIndex: -1,
      isPlaying: false,
      currentTime: 0,
      duration: 0,
      buffered: 0,
      sleepMode: 'episode',
      sleepRemainingMin: null,
      overlayOpen: false,
    })
  }, [update])

  // Wire up the <audio> element's events once.
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const onTimeUpdate = () => {
      update({ currentTime: audio.currentTime })
      const s = stateRef.current
      if (typeof s.sleepMode === 'number' && sleepEndAtRef.current) {
        const remainingMs = sleepEndAtRef.current - Date.now()
        if (remainingMs <= 0) {
          audio.pause()
          sleepEndAtRef.current = 0
          update({ sleepMode: null, sleepRemainingMin: null })
        } else {
          const remainingMin = Math.ceil(remainingMs / 60000)
          if (remainingMin !== stateRef.current.sleepRemainingMin) {
            update({ sleepRemainingMin: remainingMin })
          }
        }
      }
      if (Date.now() - lastSaveAtRef.current > 5000) savePlayback()
    }
    const onLoadedMetadata = () => {
      update({ duration: audio.duration || 0 })
      if (resumeTimeRef.current) {
        audio.currentTime = resumeTimeRef.current
        resumeTimeRef.current = 0
      }
    }
    // Fires repeatedly as the browser downloads more of the file — used to
    // draw the "how much has loaded" portion of the seek bar, YouTube-style.
    const onProgress = () => {
      const ranges = audio.buffered
      update({ buffered: ranges.length ? ranges.end(ranges.length - 1) : 0 })
    }
    const onPlay = () => update({ isPlaying: true })
    const onPause = () => {
      update({ isPlaying: false })
      savePlayback()
    }
    const onEnded = () => {
      audio.currentTime = 0
      saveProgress(true)
      const s = stateRef.current
      if (s.sleepMode === 'episode') {
        update({ sleepMode: null })
        return
      }
      playNext()
    }

    audio.addEventListener('timeupdate', onTimeUpdate)
    audio.addEventListener('loadedmetadata', onLoadedMetadata)
    audio.addEventListener('progress', onProgress)
    audio.addEventListener('play', onPlay)
    audio.addEventListener('pause', onPause)
    audio.addEventListener('ended', onEnded)
    const onPageHide = () => savePlayback()
    window.addEventListener('pagehide', onPageHide)

    return () => {
      audio.removeEventListener('timeupdate', onTimeUpdate)
      audio.removeEventListener('loadedmetadata', onLoadedMetadata)
      audio.removeEventListener('progress', onProgress)
      audio.removeEventListener('play', onPlay)
      audio.removeEventListener('pause', onPause)
      audio.removeEventListener('ended', onEnded)
      window.removeEventListener('pagehide', onPageHide)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Restore last-played track (not autoplaying) on first mount.
  useEffect(() => {
    const saved = loadSavedPlayback()
    const audio = audioRef.current
    if (!saved || !audio) return
    audio.src = saved.currentSrc!
    audio.playbackRate = stateRef.current.speed
    resumeTimeRef.current = saved.resumeTime
    update({
      currentSrc: saved.currentSrc!,
      currentLabel: saved.currentLabel,
      subtitle: saved.subtitle,
      playlist: saved.playlist ?? null,
      currentIndex: saved.currentIndex ?? -1,
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // MediaSession (lock-screen controls) — registered once, always reads live refs.
  useEffect(() => {
    if (!('mediaSession' in navigator)) return
    const audio = audioRef.current
    if (!audio) return
    navigator.mediaSession.setActionHandler('play', () => audio.play())
    navigator.mediaSession.setActionHandler('pause', () => audio.pause())
    navigator.mediaSession.setActionHandler('previoustrack', () => playPrev())
    navigator.mediaSession.setActionHandler('nexttrack', () => playNext())
    navigator.mediaSession.setActionHandler('seekbackward', (details) => {
      audio.currentTime = Math.max(0, audio.currentTime - (details.seekOffset || 10))
    })
    navigator.mediaSession.setActionHandler('seekforward', (details) => {
      audio.currentTime = Math.min(audio.duration || Infinity, audio.currentTime + (details.seekOffset || 10))
    })
    navigator.mediaSession.setActionHandler('seekto', (details) => {
      if (details.seekTime !== undefined) audio.currentTime = details.seekTime
    })
    return () => {
      navigator.mediaSession.setActionHandler('play', null)
      navigator.mediaSession.setActionHandler('pause', null)
      navigator.mediaSession.setActionHandler('previoustrack', null)
      navigator.mediaSession.setActionHandler('nexttrack', null)
      navigator.mediaSession.setActionHandler('seekbackward', null)
      navigator.mediaSession.setActionHandler('seekforward', null)
      navigator.mediaSession.setActionHandler('seekto', null)
    }
  }, [playPrev, playNext])

  // MediaSession metadata + playbackState, kept in sync with state.
  const { currentLabel, subtitle, isPlaying, duration, currentTime, speed } = stateRef.current
  useEffect(() => {
    if (!('mediaSession' in navigator) || !stateRef.current.currentSrc) return
    navigator.mediaSession.metadata = new MediaMetadata({
      title: currentLabel,
      artist: 'अमृतकण',
      album: subtitle || '',
      artwork: [{ src: '/static/mauli.jpg?v=2', sizes: '512x512', type: 'image/jpeg' }],
    })
  }, [currentLabel, subtitle])
  useEffect(() => {
    if (!('mediaSession' in navigator)) return
    navigator.mediaSession.playbackState = isPlaying ? 'playing' : 'paused'
  }, [isPlaying])
  useEffect(() => {
    if (!('mediaSession' in navigator) || !('setPositionState' in navigator.mediaSession)) return
    if (!duration) return
    try {
      navigator.mediaSession.setPositionState({ duration, playbackRate: speed, position: currentTime })
    } catch {
      // duration/position can be transiently inconsistent right after a track change
    }
  }, [duration, currentTime, speed])

  const sleepLabel =
    stateRef.current.sleepMode === 'episode'
      ? 'भाग अखेर'
      : typeof stateRef.current.sleepMode === 'number'
        ? `${toDevanagari(stateRef.current.sleepRemainingMin ?? stateRef.current.sleepMode)} मि`
        : 'टायमर'

  const value: PlayerContextValue = {
    ...stateRef.current,
    play,
    togglePlay,
    playPrev,
    playNext,
    seekTo,
    setSpeed,
    setSleepOption,
    openOverlay,
    closeOverlay,
    stop,
    sleepLabel,
  }

  return (
    <PlayerContext.Provider value={value}>
      {children}
      <audio ref={audioRef} preload="metadata" />
    </PlayerContext.Provider>
  )
}

export function usePlayer(): PlayerContextValue {
  const ctx = useContext(PlayerContext)
  if (!ctx) throw new Error('usePlayer must be used within a PlayerProvider')
  return ctx
}

export { formatTime }
