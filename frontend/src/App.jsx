import { useEffect, useState } from 'react'
import { loadDashboard } from './lib/api'
import Hero from './components/Hero'
import RankingCard from './components/RankingCard'
import EmergingCard from './components/EmergingCard'
import DetailDialog from './components/DetailDialog'

export default function App() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(false)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    loadDashboard().then(setData).catch(() => setError(true))
  }, [])

  return (
    <div className="mx-auto max-w-[1180px] p-4 sm:p-8">
      <Hero count={data?.items.length ?? 0} runs={data?.runs ?? []} />
      {error && (
        <div className="mt-6 border-[3px] border-ink bg-hot p-4 font-bold shadow-brut" role="alert">
          Cannot reach the DevIntel API. Start it with: uvicorn app.main:app --reload --reload-dir app
        </div>
      )}
      {data && (
        <div className="mt-9 grid items-start gap-8 md:grid-cols-[minmax(0,1.9fr)_minmax(0,1fr)]">
          <RankingCard items={data.items} categories={data.categories} onSelect={setSelected} />
          <EmergingCard rows={data.emerging} onSelect={setSelected} />
        </div>
      )}
      <DetailDialog slug={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
