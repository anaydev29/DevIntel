import { useEffect, useState } from 'react'
import { loadBreakdown } from '../lib/api'
import { METRIC_LABELS, formatMetric } from '../lib/format'
import { scoreFor } from '../lib/score'

// "How the score is made": one bar per signal, and the points add up to the score
export default function ScoreBreakdown({ slug }) {
  const [breakdown, setBreakdown] = useState(null)
  useEffect(() => { loadBreakdown().then(setBreakdown).catch(() => {}) }, [])

  const t = breakdown?.technologies.find((x) => x.slug === slug)
  if (!t || !Object.keys(t.components).length) return null
  const total = Object.keys(t.components).reduce((sum, m) => sum + breakdown.weights[m], 0)
  const rows = Object.entries(t.components).map(([metric, c]) => {
    const share = breakdown.weights[metric] / total
    return { metric, value: c.value, rank: c.rank, share, points: share * c.rank * 100 }
  }).sort((a, b) => b.points - a.points)

  return (
    <div className="mt-6">
      <h3 className="font-display text-xl">How the score is made</h3>
      <p className="mb-3 text-sm">Each bar shows how this technology ranks against all the others on one signal. Signals with a bigger weight add more points.</p>
      <ul className="flex flex-col gap-3">
        {rows.map((r) => (
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
      <p className="mt-3 border-t-2 border-ink pt-2 font-bold">Total: {scoreFor(t.components, breakdown.weights).toFixed(1)} of 100</p>
    </div>
  )
}
