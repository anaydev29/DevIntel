import { useMemo } from 'react'
import { categoryName } from '../lib/format'

// Technology chips grouped by category; click to toggle.
export default function SkillPicker({ technologies, picked, onToggle }) {
  const groups = useMemo(() => {
    const map = new Map()
    technologies.forEach((t) => map.set(t.category, [...(map.get(t.category) ?? []), t]))
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b))
      .map(([cat, list]) => [cat, [...list].sort((x, y) => x.name.localeCompare(y.name))])
  }, [technologies])

  return (
    <div className="flex flex-col gap-3">
      {groups.map(([cat, list]) => (
        <div key={cat}>
          <p className="mb-1 text-sm font-bold">{categoryName(cat)}</p>
          <div className="flex flex-wrap gap-2">
            {list.map((t) => (
              <button key={t.slug} type="button" aria-pressed={picked.has(t.slug)} onClick={() => onToggle(t.slug)}
                className={`press cursor-pointer border-[3px] border-ink px-3 py-0.5 font-bold shadow-brut-xs hover:bg-sun hover:text-ink ${picked.has(t.slug) ? 'bg-ink text-white' : 'bg-white'}`}>
                {t.name}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
