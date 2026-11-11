import { useMemo, useState } from 'react'
import { compact, timeAgo } from '../lib/format'
import { useAsync } from '../lib/useAsync'
import Page from './Page'

const loadHub = () =>
  fetch('/hub/items?limit=20').then((r) => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    return r.json()
  })

const SOURCES = {
  huggingface: {
    label: 'Hugging Face',
    kinds: [['model', 'Models'], ['dataset', 'Datasets'], ['space', 'Spaces']],
    command: 'python run_pipeline.py --source huggingface',
  },
  kaggle: {
    label: 'Kaggle',
    kinds: [['dataset', 'Datasets'], ['notebook', 'Notebooks'], ['competition', 'Competitions']],
    command: 'python run_pipeline.py --source kaggle',
  },
}

// Kaggle sends dates such as "2030-01-01 00:00:00" without a time zone. They are UTC.
function formatDate(value) {
  if (!value) return null
  const text = String(value)
  const iso = /^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?(\.\d+)?$/.test(text) ? `${text.replace(' ', 'T')}Z` : text
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? null : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })
}

// The small labels under each card depend on what kind of item it is
function Chips({ item }) {
  const x = item.extra ?? {}
  const chips = []
  if (item.source === 'huggingface') {
    if (item.kind === 'model') {
      if (x.pipeline_tag) chips.push(['bg-lilac', x.pipeline_tag])
      if (x.library) chips.push(['', x.library])
    }
    if (item.kind === 'dataset' && x.task) chips.push(['bg-lilac', x.task])
    if (item.kind === 'space' && x.sdk) chips.push(['bg-lilac', x.sdk])
    if (item.downloads) chips.push(['bg-mint', `${compact.format(item.downloads)} downloads, 30 days`])
    chips.push(['bg-sun', `${compact.format(item.likes)} likes`])
    if (item.trending_score != null) chips.push(['', `trending ${Math.round(item.trending_score)}`])
  } else {
    if (item.kind === 'dataset') {
      chips.push(['bg-sun', `${compact.format(item.likes)} votes`])
      if (item.downloads) chips.push(['bg-mint', `${compact.format(item.downloads)} downloads`])
      if (x.usability != null) chips.push(['', `usability ${Number(x.usability).toFixed(2)}`])
    }
    if (item.kind === 'notebook') {
      chips.push(['bg-sun', `${compact.format(item.likes)} votes`])
      if (x.language) chips.push(['bg-lilac', x.language])
      if (x.last_run) chips.push(['', `ran ${timeAgo(x.last_run)}`])
    }
    if (item.kind === 'competition') {
      if (x.reward) chips.push(['bg-sun', x.reward])
      if (x.teams) chips.push(['bg-mint', `${compact.format(x.teams)} teams`])
      if (formatDate(x.deadline)) chips.push(['', `deadline ${formatDate(x.deadline)}`])
      if (x.category) chips.push(['bg-lilac', x.category])
    }
  }
  if (item.technology) chips.push(['bg-hot', `tracked: ${item.technology}`])
  return chips.map(([color, text], i) => <span key={i} className={`di-chip ${color}`}>{text}</span>)
}

export default function HubPage() {
  const state = useAsync(loadHub, [])
  const [source, setSource] = useState('huggingface')
  const [kind, setKind] = useState('model')

  const groups = useMemo(() => {
    const map = {}
    for (const item of state.data ?? []) (map[`${item.source}/${item.kind}`] ??= []).push(item)
    return map
  }, [state.data])

  const cfg = SOURCES[source]
  const items = groups[`${source}/${kind}`] ?? []
  const day = items[0]?.captured_on

  function pickSource(key) {
    setSource(key)
    setKind(SOURCES[key].kinds[0][0])
  }

  return (
    <Page kicker="Page 07" title="AI hub" intro="What is trending in open-source AI on Hugging Face, and the datasets, notebooks and competitions that are popular on Kaggle. Collected once a day.">
      <div className="di-filter" role="group" aria-label="Source">
        {Object.entries(SOURCES).map(([key, s]) => (
          <button key={key} type="button" className="di-btn" aria-pressed={source === key} onClick={() => pickSource(key)}>{s.label}</button>
        ))}
      </div>
      <div className="di-filter" role="group" aria-label="What to show">
        {cfg.kinds.map(([k, label]) => (
          <button key={k} type="button" className="di-btn di-btn--sm" aria-pressed={kind === k} onClick={() => setKind(k)}>
            {label} <span className="di-chip">{(groups[`${source}/${k}`] ?? []).length}</span>
          </button>
        ))}
      </div>

      {state.loading && <p className="di-empty">Loading...</p>}
      {state.error && <p className="di-alert" style={{ margin: 0 }}>Could not load the AI hub. Update the backend, restart it and run the new collectors.</p>}
      {state.data && items.length === 0 && (
        <p className="di-empty">
          Nothing collected for this list yet. Run <code style={{ fontWeight: 700 }}>{cfg.command}</code> in the backend folder.
          {source === 'kaggle' && kind !== 'dataset' && ' Notebooks and competitions also need your Kaggle credentials in backend/.env.'}
        </p>
      )}
      {items.length > 0 && (
        <>
          <p className="di-count">Snapshot from {formatDate(day) ?? 'today'}, ranked by {source === 'huggingface' ? 'Hugging Face trending score' : kind === 'competition' ? 'number of teams' : kind === 'notebook' ? 'hotness' : 'hotness'}.</p>
          <ol className="di-grid2">
            {items.map((it) => (
              <li key={`${it.kind}-${it.rank}-${it.title}`}>
                <article className="di-card di-repo di-lift">
                  <span className={`di-rank di-rank--${it.rank <= 3 ? it.rank : 'x'}`}>{it.rank}</span>
                  <div>
                    <a href={it.url} target="_blank" rel="noopener noreferrer" className="di-repo__name di-link-plain">{it.title}</a>
                    {it.author && <p style={{ margin: '2px 0 0', fontSize: '0.9rem' }}>by {it.author}</p>}
                    {it.description && <p>{it.description}</p>}
                    <div className="di-post__foot" style={{ marginTop: 10 }}><Chips item={it} /></div>
                  </div>
                </article>
              </li>
            ))}
          </ol>
        </>
      )}
    </Page>
  )
}
