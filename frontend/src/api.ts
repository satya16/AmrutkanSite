export interface Episode {
  filename: string
  label: string
  audioUrl: string
}

export interface Chapter {
  slug: string
  label: string
  isSpecial: boolean
  episodeCount: number
  episodes: Episode[]
}

export interface Book {
  id: string
  name: string
  unit: string
  totalEpisodes: number
  chapters: Chapter[]
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

export interface HomeContent {
  tagline: string
  siteDescription: string
  heroImage: string
  aboutText: string
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
