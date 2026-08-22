export interface Episode {
  filename: string
  label: string
  audioUrl: string
  sizeBytes: number
}

export interface Chapter {
  slug: string
  label: string
  isSpecial: boolean
  episodeCount: number
  episodes: Episode[]
  zipSizeBytes: number | null
}

export interface Book {
  id: string
  name: string
  unit: string
  totalEpisodes: number
  chapters: Chapter[]
  zipSizeBytes: number | null
}

export interface Library {
  books: Book[]
  artworkUrl: string
}

export interface PodcastLink {
  label: string
  url: string
  color: string
  path: string
}

export interface PustakChapter {
  title: string
  page: number
}

export interface PustakBook {
  id: string
  title: string
  subtitle: string
  author: string
  pageCount: number
  thumbnailUrl: string
  chapters: PustakChapter[]
}

export interface PustakList {
  books: PustakBook[]
}

export interface HomeContent {
  tagline: string
  siteDescription: string
  tilakImage: string
  tilakText: string
  heroImage: string
  aboutHeading: string
  aboutText: string
  aboutMeHeading: string
  aboutMePhoto: string
  aboutMeText: string
  podcastLinks: PodcastLink[]
  youtube: {
    channelUrl: string
    channelHandle: string
    videoIds: string[]
  }
}

async function getJSON<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${url} -> ${res.status}`)
  return res.json() as Promise<T>
}

export const fetchLibrary = () => getJSON<Library>('/api/library')
export const fetchHome = () => getJSON<HomeContent>('/api/home')
export const fetchPustake = () => getJSON<PustakList>('/api/pustake')

export interface FeedbackPayload {
  message: string
  contact: string
  // Honeypot — real users never see this field; bots that fill in every
  // field trip it. Always sent empty by the actual form.
  website: string
}

export async function submitFeedback(payload: FeedbackPayload): Promise<void> {
  const res = await fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, source: 'web' }),
  })
  const data = (await res.json().catch(() => ({}))) as { ok?: boolean; error?: string }
  if (!res.ok || !data.ok) {
    throw new Error(data.error || `feedback -> ${res.status}`)
  }
}
