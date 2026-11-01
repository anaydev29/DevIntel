import { timeAgo } from '../lib/format'

const STATUS_BG = { success: 'bg-mint', partial: 'bg-sun', failed: 'bg-hot' }

// One label per data source with the status of its latest collection run.
export default function StatusStrip({ runs, loading }) {
  // runs arrive newest first, so the first run per source is its latest
  const latest = [...new Map([...runs].reverse().map((r) => [r.source, r])).values()]
  return (
    <div className="di-strip" aria-live="polite">
      <div className="di-wrap di-strip__inner">
        <span className="di-strip__label">Live data</span>
        {loading && <span className="di-chip">connecting to the API...</span>}
        {!loading && latest.length === 0 && <span className="di-chip">no collection runs yet</span>}
        {latest.map((r) => (
          <span key={r.source} className={`di-chip ${STATUS_BG[r.status] ?? 'bg-hot'}`} title={`status: ${r.status}`}>
            <span className="di-dot" style={{ background: '#000' }} />
            {r.source} {timeAgo(r.started_at)}
          </span>
        ))}
      </div>
    </div>
  )
}
