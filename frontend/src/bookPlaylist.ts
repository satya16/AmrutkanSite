import type { Book } from './api'
import type { PlaylistItem } from './player/PlayerContext'

// Whole-book playlist, chapters flattened in the same order they appear in
// the UI (book.chapters is already server-ordered, incl. सारांश/परिचय-style
// special items) — so playNext/playPrev naturally cross chapter boundaries
// instead of stopping at the end of whichever chapter playback started in.
export function buildBookPlaylist(book: Book): Required<PlaylistItem>[] {
  return book.chapters.flatMap((chapter) =>
    chapter.episodes.map((episode) => ({
      src: episode.audioUrl,
      label: episode.label,
      subtitle: `${book.name} · ${chapter.label}`,
    })),
  )
}
