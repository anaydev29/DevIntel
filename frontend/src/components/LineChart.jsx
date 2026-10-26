const W = 600
const H = 230
const LEFT = 56
const RIGHT = 580
const TOP = 12
const BOTTOM = 182

const fmtDate = (t) => new Date(t).toLocaleDateString('en', { day: 'numeric', month: 'short' })

// Simple line chart. series: [{ name, color, points: [{ date, value }] }]. domain: [min, max], or omitted to fit the data.
export default function LineChart({ series, domain, formatY = (v) => String(Math.round(v)), label, emptyMessage }) {
  const usable = series.filter((s) => s.points.length > 0)
  if (!usable.some((s) => s.points.length >= 2)) {
    return <p className="border-[3px] border-dashed border-ink p-4">{emptyMessage ?? 'The trend line appears after a few days of collected data.'}</p>
  }
  const times = usable.flatMap((s) => s.points.map((p) => new Date(p.date).getTime()))
  const tMin = Math.min(...times)
  const tMax = Math.max(...times)
  const values = usable.flatMap((s) => s.points.map((p) => p.value))
  let [lo, hi] = domain ?? [Math.min(...values), Math.max(...values)]
  if (!domain) {
    const pad = (hi - lo) * 0.1 || Math.abs(hi) * 0.05 || 1
    lo -= pad
    hi += pad
  }
  const x = (d) => LEFT + (tMax === tMin ? 0 : ((new Date(d).getTime() - tMin) / (tMax - tMin)) * (RIGHT - LEFT))
  const y = (v) => BOTTOM - ((v - lo) / (hi - lo || 1)) * (BOTTOM - TOP)
  const ticks = [lo, (lo + hi) / 2, hi]

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full border-[3px] border-ink bg-white" role="img" aria-label={label}>
        <line x1={LEFT} y1={TOP} x2={LEFT} y2={BOTTOM} stroke="#000" strokeWidth="3" />
        <line x1={LEFT} y1={BOTTOM} x2={RIGHT} y2={BOTTOM} stroke="#000" strokeWidth="3" />
        {ticks.map((v, i) => (
          <g key={i}>
            <line x1={LEFT} y1={y(v)} x2={RIGHT} y2={y(v)} stroke="#000" strokeOpacity="0.12" strokeWidth="1" />
            <text x={LEFT - 6} y={y(v) + 4} textAnchor="end" fontSize="12" fontWeight="700">{formatY(v)}</text>
          </g>
        ))}
        <text x={LEFT} y={H - 8} fontSize="12" fontWeight="700">{fmtDate(tMin)}</text>
        <text x={RIGHT} y={H - 8} textAnchor="end" fontSize="12" fontWeight="700">{fmtDate(tMax)}</text>
        {usable.map((s) => (
          <g key={s.name}>
            <polyline fill="none" stroke={s.color} strokeWidth="5" strokeLinejoin="round" points={s.points.map((p) => `${x(p.date)},${y(p.value)}`).join(' ')} />
            {s.points.length <= 40 && s.points.map((p) => <circle key={p.date} cx={x(p.date)} cy={y(p.value)} r="4.5" fill={s.color} stroke="#000" strokeWidth="2" />)}
          </g>
        ))}
      </svg>
      {usable.length > 1 && (
        <p className="mt-2 flex flex-wrap gap-3 text-sm font-bold">
          {usable.map((s) => <span key={s.name} className="flex items-center gap-1.5"><span className="inline-block h-3 w-5 border-2 border-ink" style={{ background: s.color }} />{s.name}</span>)}
        </p>
      )}
    </div>
  )
}
