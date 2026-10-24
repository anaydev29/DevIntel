import { useEffect, useRef, useState } from 'react'
import { addToWatchlist, loadBreakdown, loadTechnology, removeFromWatchlist } from '../lib/api'
import { useAuth } from '../lib/auth'
import DiscussionPanel from './DiscussionPanel'
import { METRIC_LABELS, categoryName, formatMetric, growthText } from '../lib/format'
import { scoreFor } from '../lib/score'

function Sticker({ children, color = 'bg-white' }) {
  return <span className={`border-[3px] border-ink px-3 py-0.5 font-bold shadow-brut-xs ${color}`}>{children}</span>
}

export default function DetailDialog({ slug, onClose }) {
  const ref = useRef(null)
  const { authenticated, profile, setProfile } = useAuth()
  const [busy, setBusy] = useState(false)
  const [breakdown, setBreakdown] = useState(null)

  useEffect(() => { loadBreakdown().then(setBreakdown).catch(() => {}) }, [])
  const [tech, setTech] = useState(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!slug) return
    let cancelled = false
    setTech(null)
    setFailed(false)
    if (!ref.current.open) ref.current.showModal()
    loadTechnology(slug)
      .then((t) => !cancelled && setTech(t))
      .catch(() => !cancelled && setFailed(true))
    return () => { cancelled = true }
  }, [slug])

  const growth = tech && growthText(tech.growth_30d)
  const parts = (() => {
    const t = breakdown?.technologies.find((x) => x.slug === tech?.slug)
    if (!t || !Object.keys(t.components).length) return null
    const total = Object.keys(t.components).reduce((sum, m) => sum + breakdown.weights[m], 0)
    const rows = Object.entries(t.components).map(([metric, c]) => {
      const share = breakdown.weights[metric] / total
      return { metric, value: c.value, rank: c.rank, share, points: share * c.rank * 100 }
    }).sort((a, b) => b.points - a.points)
    return { rows, score: scoreFor(t.components, breakdown.weights) }
  })()
  const watching = !!tech && !!profile?.watchlist.some((w) => w.slug === tech.slug)

  async function toggleWatch() {
    setBusy(true)
    try {
      const list = await (watching ? removeFromWatchlist(tech.slug) : addToWatchlist(tech.slug))
      setProfile({ ...profile, watchlist: list })
    } finally {
      setBusy(false)
    }
  }

  return (
    <dialog
      ref={ref}
      aria-labelledby="dlg-title"
      onClose={onClose}
      onClick={(e) => e.target === ref.current && ref.current.close()}
      className="m-auto max-h-[90vh] w-[calc(100%-2rem)] max-w-xl overflow-y-auto border-[3px] border-ink bg-white p-0 shadow-[10px_10px_0_#000]"
    >
      <div className="p-6">
        {failed && <p>Could not load this technology. Check that the API is running.</p>}
        {!failed && !tech && <p>Loading...</p>}
        {tech && (
          <>
            <h2 id="dlg-title" className="font-display text-4xl leading-tight">{tech.name}</h2>
            <div className="my-3 flex flex-wrap gap-3">
              <Sticker>{categoryName(tech.category)}</Sticker>
              {tech.devintel_score != null && <Sticker>Score {Math.round(tech.devintel_score)} of 100</Sticker>}
              <Sticker color={tech.is_emerging ? 'bg-hot' : 'bg-white'}>
                {growth ? `30-day growth ${growth}` : 'Growth needs 7 days of data'}
              </Sticker>
            </div>
            <dl className="grid gap-2">
              {Object.entries(METRIC_LABELS)
                .filter(([key]) => tech.latest_metrics[key] != null)
                .map(([key, label]) => (
                  <div key={key} className="flex justify-between gap-4 border-b-2 border-ink pb-1.5">
                    <dt>{label}</dt>
                    <dd className="font-bold">{formatMetric(key, tech.latest_metrics[key])}</dd>
                  </div>
                ))}
            </dl>
            {parts && (
              <div className="mt-6">
                <h3 className="font-display text-xl">How the score is made</h3>
                <p className="mb-3 text-sm">Each bar shows how this technology ranks against all the others on one signal. Signals with a bigger weight add more points.</p>
                <ul className="flex flex-col gap-3">
                  {parts.rows.map((r) => (
                    <li key={r.metric}>
                      <div className="flex justify-between gap-3 text-sm font-bold">
                        <span>{METRIC_LABELS[r.metric] ?? r.metric}: {formatMetric(r.metric, r.value)}</span>
                        <span>+{r.points.toFixed(1)} points</span>
                      </div>
                      <div className="my-1 h-4 border-[3px] border-ink bg-white" role="img" aria-label={`Ahead of ${Math.round(r.rank * 100)} percent of technologies`}>
                        <div className="h-full border-r-[3px] border-ink bg-sky" style={{ width: `${Math.max(1, r.rank * 100)}%` }} />
                      </div>
                      <p className="text-xs">Ahead of {Math.round(r.rank * 100)}% of technologies. This signal counts for {Math.round(r.share * 100)}% of the score.</p>
                    </li>
                  ))}
                </ul>
                <p className="mt-3 border-t-2 border-ink pt-2 font-bold">Total: {parts.score.toFixed(1)} of 100</p>
              </div>
            )}
            {tech.aliases.length > 0 && (
              <p className="mt-4 text-sm">Also known as: {tech.aliases.join(', ')}</p>
            )}
            {authenticated ? (
              <button type="button" disabled={busy || !profile} onClick={toggleWatch}
                className="press mt-4 mr-3 cursor-pointer border-[3px] border-ink bg-mint px-5 py-1.5 font-bold shadow-brut-sm disabled:opacity-50">
                {watching ? 'Remove from watchlist' : 'Add to watchlist'}
              </button>
            ) : (
              <p className="mt-4 text-sm">Sign in to add this to your watchlist.</p>
            )}
          </>
        )}
        {tech && (
          <div className="mt-6 border-t-[3px] border-ink pt-4">
            <h3 className="mb-3 font-display text-2xl">Discussion</h3>
            <DiscussionPanel kind="technology" refKey={tech.slug} />
          </div>
        )}
        <button
          type="button"
          onClick={() => ref.current.close()}
          className="press mt-5 cursor-pointer border-[3px] border-ink bg-sun px-5 py-1.5 font-bold shadow-brut-sm"
        >
          Close
        </button>
      </div>
    </dialog>
  )
}
