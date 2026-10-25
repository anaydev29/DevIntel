import { useState } from 'react'
import { addToWatchlist, removeFromWatchlist } from '../lib/api'
import { useAuth } from '../lib/auth'

export default function WatchButton({ slug }) {
  const { authenticated, profile, setProfile } = useAuth()
  const [busy, setBusy] = useState(false)
  if (!authenticated) return <p className="text-sm">Sign in to add this to your watchlist.</p>
  const watching = !!profile?.watchlist.some((w) => w.slug === slug)

  async function toggle() {
    setBusy(true)
    try {
      const list = await (watching ? removeFromWatchlist(slug) : addToWatchlist(slug))
      setProfile({ ...profile, watchlist: list })
    } finally {
      setBusy(false)
    }
  }
  return (
    <button type="button" disabled={busy || !profile} onClick={toggle}
      className="press cursor-pointer border-[3px] border-ink bg-mint px-5 py-1.5 font-bold shadow-brut-sm disabled:opacity-50">
      {watching ? 'Remove from watchlist' : 'Add to watchlist'}
    </button>
  )
}
