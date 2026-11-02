import { useEffect, useState } from 'react'
import { timeAgo } from '../lib/format'

const STATUS_BG = { success: 'bg-mint', partial: 'bg-sun', failed: 'bg-hot' }

function Chip({ run, dup }) {
  return (
    <span className={`di-chip ${STATUS_BG[run.status] ?? 'bg-hot'}${dup ? ' di-dup' : ''}`} title={`status: ${run.status}`}>
      <span className="di-dot" style={{ background: '#000' }} />
      {run.source} {timeAgo(run.started_at)}
    </span>
  )
}

// A continuously scrolling ticker with the status of the latest collection run of every source.
// It pauses on hover, and stays still (scrollable) for people who prefer reduced motion.
export default function StatusStrip({ runs, loading }) {
  const [, tick] = useState(0)
  useEffect(() => {
    const id = setInterval(() => tick((n) => n + 1), 60000) // keep "6 h ago" up to date
    return () => clearInterval(id)
  }, [])

  // runs arrive newest first, so the first run per source is its latest
  const latest = [...new Map([...runs].reverse().map((r) => [r.source, r])).values()]
  // Two identical halves make the loop seamless. Each half repeats the list so it is wider than the screen.
  const half = [...latest, ...latest]

  return (
    <div className="di-strip" role="region" aria-label="Data freshness">
      <div className="di-wrap di-strip__inner">
        <span className="di-strip__label"><span className="di-pulse" />Live data</span>
        {loading && <span className="di-chip">connecting to the API...</span>}
        {!loading && latest.length === 0 && <span className="di-chip">no collection runs yet</span>}
        {latest.length > 0 && (
          <>
            <span className="di-sr">
              Latest collection runs: {latest.map((r) => `${r.source} ${r.status} ${timeAgo(r.started_at)}`).join(', ')}.
            </span>
            <div className="di-strip__marquee" aria-hidden="true">
              <div className="di-strip__track">
                {[...half, ...half].map((r, i) => (
                  <Chip key={`${r.source}-${i}`} run={r} dup={i >= latest.length} />
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
