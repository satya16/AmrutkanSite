import type { Book, Chapter, Episode, Library } from './api'
import type { SavedProgress } from './player/PlayerContext'

const PROGRESS_KEY = 'ak_progress'

export function loadProgress(): SavedProgress | null {
  try {
    const saved = JSON.parse(localStorage.getItem(PROGRESS_KEY) || 'null')
    if (!saved || !saved.bookId || !saved.filename) return null
    return saved as SavedProgress
  } catch {
    return null
  }
}

interface FlatEntry {
  chapter: Chapter
  episode: Episode
}

function flattenBook(book: Book): FlatEntry[] {
  return book.chapters.flatMap((chapter) => chapter.episodes.map((episode) => ({ chapter, episode })))
}

export type ContinueState =
  | { mode: 'resume'; book: Book; chapter: Chapter; episode: Episode; resumeTime: number }
  | { mode: 'next'; book: Book; chapter: Chapter; episode: Episode }
  | { mode: 'finished'; book: Book }

export function resolveContinueListening(library: Library, progress: SavedProgress): ContinueState | null {
  const book = library.books.find((b) => b.id === progress.bookId)
  if (!book) return null
  const flat = flattenBook(book)
  const idx = flat.findIndex((entry) => entry.episode.filename === progress.filename)
  if (idx === -1) return null

  if (!progress.completed) {
    return { mode: 'resume', book, chapter: flat[idx].chapter, episode: flat[idx].episode, resumeTime: progress.currentTime }
  }
  if (idx >= flat.length - 1) {
    return { mode: 'finished', book }
  }
  const next = flat[idx + 1]
  return { mode: 'next', book, chapter: next.chapter, episode: next.episode }
}
