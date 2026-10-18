import { useState } from 'react'
import { loadCompare } from '../lib/api'
import { METRIC_LABELS, categoryName, compact, growthText } from '../lib/format'
import { useAsync } from '../lib/useAsync'

const COLORS = [
  { bg: 'bg-sky', hex: '#4D7CFF' },
  { bg: 'bg-hot', hex: '#FF5CA8' },
]

function Picker({ label, value, onChange, options, color }) {
  return (
    <label className="flex flex-1 flex-col gap-1 font-bold">
      <span className={`w-fit border-2 border-ink px-2 text-sm ${color}`}>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} className="cursor-pointer border-[3px] border-ink bg-white px-3 py-2.5 shadow-brut-sm">
        {options.map((t) => <option key={t.slug} value={t.slug}>{t.name}</option>)}
      </select>
    </label>
  )
}

function TrendChart({ techs }) {
  const points = techs.flatMap((t) => t.history.map((h) => new Date(h.date).getTime()))
  const min = Math.min(...points), max = Math.max(...points)
  if (techs.every((t) => t.history.length < 2)) {
    return <p className="border-[3px] border-dashed border-ink p-4">Score trend lines appear after a few days of collected data. The pipeline adds a new point every day.</p>
  }
  const x = (d) => 40 + (max === min ? 0 : ((new Date(d).getTime() - min) / (max - min)) * 540)
  const y = (s) => 180 - s * 1.7
  const fmtDate = (t) => new Date(t).toLocaleDateString('en', { day: 'numeric', month: 'short' })
  return (
    <svg viewBox="0 0 600 220" className="w-full border-[3px] border-ink bg-white" role="img" aria-label="DevIntel Score over time for each technology">
      <line x1="40" y1="10" x2="40" y2="180" stroke="#000" strokeWidth="3" />
      <line x1="40" y1="180" x2="580" y2="180" stroke="#000" strokeWidth="3" />
      {[0, 50, 100].map((v) => <text key={v} x="34" y={y(v) + 4} textAnchor="end" fontSize="12" fontWeight="700">{v}</text>)}
      <text x="40" y="204" fontSize="12" fontWeight="700">{fmtDate(min)}</text>
      <text x="580" y="204" textAnchor="end" fontSize="12" fontWeight="700">{fmtDate(max)}</text>
      {techs.map((t, i) => (
        <g key={t.slug}>
          <polyline fill="none" stroke={COLORS[i].hex} strokeWidth="5" points={t.history.map((h) => `${x(h.date)},${y(h.score)}`).join(' ')} />
          {t.history.map((h) => <circle key={h.date} cx={x(h.date)} cy={y(h.score)} r="5" fill={COLORS[i].hex} stroke="#000" strokeWidth="2" />)}
        </g>
      ))}
    </svg>
  )
}

function verdict(techs, rows) {
  const wins = techs.map(() => 0)
  rows.forEach((r) => {
    const [a, b] = r.values
    if (a != null && b != null && a !== b) wins[a > b ? 0 : 1] += 1
  })
  const counted = wins[0] + wins[1]
  const score = techs.every((t) => t.devintel_score != null)
    ? ` DevIntel Score: ${techs[0].name} ${Math.round(techs[0].devintel_score)}, ${techs[1].name} ${Math.round(techs[1].devintel_score)}.`
    : ''
  if (!counted) return 'Not enough data to compare yet.'
  if (wins[0] === wins[1]) return `Too close to call: each leads on ${wins[0]} signals.${score}`
  const lead = wins[0] > wins[1] ? 0 : 1
  const [gl, gt] = [techs[lead].growth_30d, techs[1 - lead].growth_30d]
  const faster = gl != null && gt != null && gt > gl + 0.1
    ? ` But ${techs[1 - lead].name} is growing faster (${growthText(gt)} vs ${growthText(gl)}).`
    : ''
  return `${techs[lead].name} leads on ${wins[lead]} of ${counted} signals, ${techs[1 - lead].name} on ${wins[1 - lead]}.${faster}${score}`
}

export default function ComparePage({ technologies }) {
  const slugs = technologies.map((t) => t.slug)
  const [a, setA] = useState(slugs.includes('fastapi') ? 'fastapi' : slugs[0])
  const [b, setB] = useState(slugs.includes('django') ? 'django' : slugs[1])
  const state = useAsync(() => (a && b && a !== b ? loadCompare(a, b) : Promise.resolve(null)), [a, b])
  const techs = state.data?.technologies
  const rows = techs
    ? Object.entries(METRIC_LABELS)
        .map(([key, label]) => ({ label, values: techs.map((t) => t.metrics[key] ?? null) }))
        .filter((r) => r.values.some((v) => v != null))
    : []

  return (
    <section className="border-[3px] border-ink bg-white p-5 shadow-brut">
      <h2 className="font-display text-3xl leading-tight">Compare technologies</h2>
      <p className="mb-4 text-[0.95rem]">Pick two technologies to see how they stack up on the same signals.</p>
      <div className="mb-5 flex flex-col gap-4 sm:flex-row">
        <Picker label="First" value={a} onChange={setA} options={technologies} color={COLORS[0].bg} />
        <Picker label="Second" value={b} onChange={setB} options={technologies} color={COLORS[1].bg} />
      </div>

      {a === b && <p className="border-[3px] border-dashed border-ink p-4">Pick two different technologies.</p>}
      {state.error && <p className="border-[3px] border-ink bg-hot p-4 font-bold">Could not load the comparison. Check that the API is running.</p>}
      {state.loading && a !== b && <p>Loading...</p>}

      {techs && (
        <>
          <p className="mb-5 border-[3px] border-ink bg-sun p-4 text-lg font-bold shadow-brut-sm">{verdict(techs, rows)}</p>

          <div className="mb-5 grid grid-cols-2 gap-4">
            {techs.map((t, i) => (
              <div key={t.slug} className={`border-[3px] border-ink p-4 shadow-brut-sm ${COLORS[i].bg}`}>
                <h3 className="font-display text-2xl">{t.name}</h3>
                <p className="mb-2 text-sm font-bold">{categoryName(t.category)}</p>
                <p className="font-display text-4xl">{t.devintel_score != null ? Math.round(t.devintel_score) : 'n/a'}</p>
                <p className="text-sm font-bold">DevIntel Score</p>
                <p className="mt-2 w-fit border-2 border-ink bg-white px-2 text-sm font-bold">
                  {growthText(t.growth_30d) ? `30-day growth ${growthText(t.growth_30d)}` : 'Growth needs 7 days of data'}
                </p>
              </div>
            ))}
          </div>

          <dl className="mb-2 flex flex-col gap-2">
            {rows.map((r) => {
              const [x, y] = r.values
              const lead = x != null && y != null && x !== y ? (x > y ? 0 : 1) : -1
              return (
                <div key={r.label} className="grid grid-cols-2 gap-x-4 gap-y-1 border-b-2 border-ink pb-2">
                  <dt className="col-span-2 font-bold">{r.label}</dt>
                  {r.values.map((v, i) => (
                    <dd key={i} className={`border-2 border-ink px-2 py-1 ${lead === i ? 'bg-mint font-bold' : 'bg-white'}`}>
                      {v == null ? 'no data' : compact.format(v)}
                    </dd>
                  ))}
                </div>
              )
            })}
          </dl>
          <p className="mb-5 text-sm">Higher is highlighted, but bigger is not always better: a newer tool can have fewer questions and still be growing much faster. Check the growth numbers too.</p>

          <h3 className="mb-2 font-display text-2xl">Score over time</h3>
          <TrendChart techs={techs} />
        </>
      )}
    </section>
  )
}
