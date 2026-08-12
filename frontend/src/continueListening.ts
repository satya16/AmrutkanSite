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
  | { mode: 'first'; book: Book; chapter: Chapter; episode: Episode }
  | { mode: 'resume'; book: Book; chapter: Chapter; episode: Episode; resumeTime: number }
  | { mode: 'next'; book: Book; chapter: Chapter; episode: Episode }
  | { mode: 'finished' }

// progress is nullable so the caller doesn't need its own separate branch
// for "nothing saved yet" — that's just another state this resolves to
// ('first'), not a precondition for calling it.
export function resolveContinueListening(library: Library, progress: SavedProgress | null): ContinueState | null {
  if (!progress) {
    // Nothing listened to yet: point at the very first episode of the
    // very first book, in library order (ज्ञानेश्वरी) — "पहिला भाग ऐका".
    const firstBook = library.books[0]
    const flat = firstBook ? flattenBook(firstBook) : []
    if (!firstBook || flat.length === 0) return null
    return { mode: 'first', book: firstBook, chapter: flat[0].chapter, episode: flat[0].episode }
  }

  const bookIndex = library.books.findIndex((b) => b.id === progress.bookId)
  if (bookIndex === -1) return null
  const book = library.books[bookIndex]
  const flat = flattenBook(book)
  const idx = flat.findIndex((entry) => entry.episode.filename === progress.filename)
  if (idx === -1) return null

  if (!progress.completed) {
    return { mode: 'resume', book, chapter: flat[idx].chapter, episode: flat[idx].episode, resumeTime: progress.currentTime }
  }
  if (idx < flat.length - 1) {
    const next = flat[idx + 1]
    return { mode: 'next', book, chapter: next.chapter, episode: next.episode }
  }
  // Finished this book's last episode — continue straight into the next
  // book in library order (ज्ञानेश्वरी -> चांगदेव पासष्टी) rather than
  // dead-ending, unless this was already the last book, in which case
  // there's nothing left to suggest.
  const nextBook = library.books[bookIndex + 1]
  const nextFlat = nextBook ? flattenBook(nextBook) : []
  if (nextBook && nextFlat.length > 0) {
    return { mode: 'next', book: nextBook, chapter: nextFlat[0].chapter, episode: nextFlat[0].episode }
  }
  return { mode: 'finished' }
}
