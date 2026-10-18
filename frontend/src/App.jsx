import { useEffect, useState } from 'react'
import { loadDashboard } from './lib/api'
import Hero from './components/Hero'
import RankingCard from './components/RankingCard'
import EmergingCard from './components/EmergingCard'
import DetailDialog from './components/DetailDialog'
import { BlogsPage, NewsPage, ReposPage } from './components/Feeds'

const TABS = [
  ['rankings', 'Rankings'],
  ['blogs', 'Blogs'],
  ['news', 'News'],
  ['repos', 'Trending repos'],
]

export default function App() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(false)
  const [selected, setSelected] = useState(null)
  const [tab, setTab] = useState('rankings')

  useEffect(() => {
    loadDashboard().then(setData).catch(() => setError(true))
  }, [])

  return (
    <div className="mx-auto max-w-[1180px] p-4 sm:p-8">
      <Hero count={data?.items.length ?? 0} runs={data?.runs ?? []} />

      <nav className="mt-8 flex flex-wrap gap-3" role="tablist" aria-label="Sections">
        {TABS.map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={`press cursor-pointer border-[3px] border-ink px-5 py-2 text-lg font-bold shadow-brut-sm hover:bg-sun hover:text-ink ${
              tab === id ? 'bg-ink text-white' : 'bg-white'
            }`}
          >
            {label}
          </button>
        ))}
      </nav>

      {error && (
        <div className="mt-6 border-[3px] border-ink bg-hot p-4 font-bold shadow-brut" role="alert">
          Cannot reach the DevIntel API. Start it with: uvicorn app.main:app --reload --reload-dir app
        </div>
      )}

      <div className="mt-8">
        {tab === 'rankings' && data && (
          <div className="grid items-start gap-8 md:grid-cols-[minmax(0,1.9fr)_minmax(0,1fr)]">
            <RankingCard items={data.items} categories={data.categories} onSelect={setSelected} />
            <EmergingCard rows={data.emerging} onSelect={setSelected} />
          </div>
        )}
        {tab === 'blogs' && <BlogsPage technologies={data?.items ?? []} />}
        {tab === 'news' && <NewsPage />}
        {tab === 'repos' && <ReposPage />}
      </div>

      <DetailDialog slug={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
