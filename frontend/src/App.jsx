import { useEffect, useState } from 'react'
import { loadDashboard } from './lib/api'
import Hero from './components/Hero'
import RankingCard from './components/RankingCard'
import EmergingCard from './components/EmergingCard'
import DetailDialog from './components/DetailDialog'
import { BlogsPage, NewsPage, ReposPage } from './components/Feeds'
import ComparePage from './components/ComparePage'
import SkillGapPage from './components/SkillGapPage'
import AccountBar from './components/AccountBar'
import ProfilePage from './components/ProfilePage'
import ModerationPage from './components/ModerationPage'
import { GuidelinesPage, PrivacyPage } from './components/LegalPages'
import { useAuth } from './lib/auth'

const TABS = [
  ['rankings', 'Rankings'],
  ['compare', 'Compare'],
  ['skills', 'Skill gap'],
  ['blogs', 'Blogs'],
  ['news', 'News'],
  ['repos', 'Trending repos'],
  ['profile', 'My profile'],
]

export default function App() {
  const { user, banned } = useAuth()
  const isMod = user?.role === 'moderator' || user?.role === 'admin'
  const [data, setData] = useState(null)
  const [error, setError] = useState(false)
  const [selected, setSelected] = useState(null)
  const [tab, setTab] = useState('rankings')

  useEffect(() => {
    loadDashboard().then(setData).catch(() => setError(true))
  }, [])

  return (
    <div className="mx-auto max-w-[1180px] p-4 sm:p-8">
      <AccountBar onProfile={() => setTab('profile')} />
      <Hero count={data?.items.length ?? 0} runs={data?.runs ?? []} />

      <nav className="mt-8 flex flex-wrap gap-3" role="tablist" aria-label="Sections">
        {[...TABS, ...(isMod ? [['moderation', 'Moderation']] : [])].map(([id, label]) => (
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

      {banned && (
        <div className="mt-6 border-[3px] border-ink bg-hot p-4 font-bold shadow-brut" role="alert">
          Your account is restricted: you can read DevIntel but not post, vote or report. See the community guidelines below.
        </div>
      )}

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
        {tab === 'compare' && <ComparePage technologies={data?.items ?? []} />}
        {tab === 'skills' && <SkillGapPage technologies={data?.items ?? []} />}
        {tab === 'blogs' && <BlogsPage technologies={data?.items ?? []} />}
        {tab === 'news' && <NewsPage />}
        {tab === 'repos' && <ReposPage />}
        {tab === 'moderation' && isMod && <ModerationPage />}
        {tab === 'guidelines' && <GuidelinesPage />}
        {tab === 'privacy' && <PrivacyPage />}
        {tab === 'profile' && <ProfilePage technologies={data?.items ?? []} onSelect={setSelected} />}
      </div>

      <footer className="mt-12 flex flex-wrap gap-4 border-t-[3px] border-ink pt-4 text-sm font-bold">
        <button type="button" className="cursor-pointer underline decoration-2 underline-offset-4 hover:bg-sun" onClick={() => setTab('guidelines')}>Community guidelines</button>
        <button type="button" className="cursor-pointer underline decoration-2 underline-offset-4 hover:bg-sun" onClick={() => setTab('privacy')}>Privacy</button>
      </footer>

      <DetailDialog slug={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
