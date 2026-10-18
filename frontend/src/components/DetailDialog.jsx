import { useEffect, useRef, useState } from 'react'
import { loadTechnology } from '../lib/api'
import { METRIC_LABELS, categoryName, compact, growthText } from '../lib/format'

function Sticker({ children, color = 'bg-white' }) {
  return <span className={`border-[3px] border-ink px-3 py-0.5 font-bold shadow-brut-xs ${color}`}>{children}</span>
}

export default function DetailDialog({ slug, onClose }) {
  const ref = useRef(null)
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

  return (
    <dialog
      ref={ref}
      aria-labelledby="dlg-title"
      onClose={onClose}
      onClick={(e) => e.target === ref.current && ref.current.close()}
      className="m-auto w-[calc(100%-2rem)] max-w-xl border-[3px] border-ink bg-white p-0 shadow-[10px_10px_0_#000]"
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
                    <dd className="font-bold">{compact.format(tech.latest_metrics[key])}</dd>
                  </div>
                ))}
            </dl>
            {tech.aliases.length > 0 && (
              <p className="mt-4 text-sm">Also known as: {tech.aliases.join(', ')}</p>
            )}
          </>
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
