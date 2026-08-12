// "Resume where you left off" for the book reader — same idea as the
// audio player's ak_playback (see player/PlayerContext.tsx), just scoped
// to page number instead of playback time. One JSON object keyed by book
// id, not a per-book key, so it's a single small localStorage entry
// regardless of how many books exist.
const PUSTAK_PROGRESS_KEY = 'ak_pustak_progress'

function loadAll(): Record<string, number> {
  try {
    const saved = JSON.parse(localStorage.getItem(PUSTAK_PROGRESS_KEY) || '{}')
    return saved && typeof saved === 'object' ? saved : {}
  } catch {
    return {}
  }
}

export function loadPustakPage(bookId: string | undefined): number | null {
  if (!bookId) return null
  const page = loadAll()[bookId]
  return typeof page === 'number' && page >= 1 ? page : null
}

export function savePustakPage(bookId: string, page: number): void {
  const all = loadAll()
  all[bookId] = page
  localStorage.setItem(PUSTAK_PROGRESS_KEY, JSON.stringify(all))
}
