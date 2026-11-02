import { useEffect, useState } from 'react'
import { loadBreakdown } from '../lib/api'
import { METRIC_LABELS, formatMetric } from '../lib/format'
import { DEFAULT_WEIGHTS, loadStoredWeights, onWeightsChange, scoreFor, sharesDiffer } from '../lib/score'

// "How the score is made": one bar per signal, and the points add up to the score
export default function ScoreBreakdown({ slug }) {
  const [breakdown, setBreakdown] = useState(null)
  const [stored, setStored] = useState(() => loadStoredWeights())

  useEffect(() => { loadBreakdown().then(setBreakdown).catch(() => {}) }, [])
  useEffect(() => onWeightsChange(setStored), [])

  const t = breakdown?.technologies.find((x) => x.slug === slug)
  if (!t || !Object.keys(t.components).length) return null

  const isCustom = stored && sharesDiffer(stored, DEFAULT_WEIGHTS)
  const activeWeights = isCustom ? stored : breakdown.weights

  const total = Object.keys(t.components).reduce((sum, m) => sum + (activeWeights[m] ?? 0), 0)
  const rows = Object.entries(t.components).map(([metric, c]) => {
    const w = activeWeights[metric] ?? 0
    const share = total > 0 ? w / total : 0
    return { metric, value: c.value, rank: c.rank, share, points: share * c.rank * 100 }
  }).sort((a, b) => b.points - a.points)

  return (
    <div className="mt-6">
      <div className="flex items-center gap-2">
        <h3 className="font-display text-xl">How the score is made</h3>
        {isCustom && <span className="di-chip bg-hot text-xs font-bold">Custom weights</span>}
      </div>
      <p className="mb-3 text-sm">
        {isCustom
          ? 'Scores are calculated using your custom signal weights. Signals with higher weight add more points.'
          : 'Each bar shows how this technology ranks against all the others on one signal. Signals with a bigger weight add more points.'}
      </p>
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
      <p className="mt-3 border-t-2 border-ink pt-2 font-bold">Total: {scoreFor(t.components, activeWeights).toFixed(1)} of 100</p>
    </div>
  )
}
