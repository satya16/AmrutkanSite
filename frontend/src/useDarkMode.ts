import { useEffect, useState } from 'react'

const STORAGE_KEY = 'amrutkan-theme'

function getInitial(): boolean {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'dark') return true
  if (stored === 'light') return false
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
}

export function useDarkMode(): [boolean, () => void] {
  const [dark, setDark] = useState(getInitial)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, dark ? 'dark' : 'light')
  }, [dark])

  return [dark, () => setDark((d) => !d)]
}
