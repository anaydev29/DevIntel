import { lazy, Suspense, useEffect, useState } from 'react'
import { loadDashboard } from './lib/api'
import Hero from './components/Hero'
import RankingCard from './components/RankingCard'
import EmergingCard from './components/EmergingCard'
import AccountBar from './components/AccountBar'
import { useAuth } from './lib/auth'
import { useRoute } from './lib/route'

// Tabs are loaded the first time they are opened (and prefetched when the browser is idle), so the first page stays small
const DetailDialog = lazy(() => import('./components/DetailDialog'))
const ComparePage = lazy(() => import('./components/ComparePage'))
const SkillGapPage = lazy(() => import('./components/SkillGapPage'))
const ProfilePage = lazy(() => import('./components/ProfilePage'))
const ModerationPage = lazy(() => import('./components/ModerationPage'))
const BlogsPage = lazy(() => import('./components/Feeds').then((m) => ({ default: m.BlogsPage })))
const NewsPage = lazy(() => import('./components/Feeds').then((m) => ({ default: m.NewsPage })))
const ReposPage = lazy(() => import('./components/Feeds').then((m) => ({ default: m.ReposPage })))
const TopicsPage = lazy(() => import('./components/TopicsPage'))
const TopicPage = lazy(() => import('./components/TopicPage'))
const TechnologyPage = lazy(() => import('./components/TechnologyPage'))
const GuidelinesPage = lazy(() => import('./components/LegalPages').then((m) => ({ default: m.GuidelinesPage })))
const PrivacyPage = lazy(() => import('./components/LegalPages').then((m) => ({ default: m.PrivacyPage })))

const prefetchTabs = () => {
  import('./components/DetailDialog')
  import('./components/ComparePage')
  import('./components/SkillGapPage')
  import('./components/Feeds')
  import('./components/ProfilePage')
  import('./components/TopicsPage')
  import('./components/TechnologyPage')
}

const TABS = [
  ['rankings', 'Rankings'],
  ['compare', 'Compare'],
  ['skills', 'Skill gap'],
  ['topics', 'Topics'],
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
  const route = useRoute()
  // A link like #/tech/python replaces the tabs with that page; picking a tab always goes back to the tabs
  const activeTab = route ? (route.name === 'topics' || route.name === 'topic' ? 'topics' : null) : tab
  const openTab = (id) => {
    setTab(id)
    window.location.hash = id === 'topics' ? '#/topics' : ''
  }

  useEffect(() => {
    loadDashboard().then(setData).catch(() => setError(true))
    const schedule = window.requestIdleCallback ?? ((fn) => setTimeout(fn, 1500))
    schedule(prefetchTabs)
  }, [])

  return (
    <div className="mx-auto max-w-[1180px] p-4 sm:p-8">
      <AccountBar onProfile={() => openTab('profile')} />
      <Hero count={data?.items.length ?? 0} runs={data?.runs ?? []} />

      <nav className="mt-8 flex flex-wrap gap-3" role="tablist" aria-label="Sections">
        {[...TABS, ...(isMod ? [['moderation', 'Moderation']] : [])].map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={activeTab === id}
            onClick={() => openTab(id)}
            className={`press cursor-pointer border-[3px] border-ink px-5 py-2 text-lg font-bold shadow-brut-sm hover:bg-sun hover:text-ink ${
              activeTab === id ? 'bg-ink text-white' : 'bg-white'
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

      <Suspense fallback={<p className="mt-8 border-[3px] border-ink bg-white p-4 font-bold">Loading...</p>}>
      <div className="mt-8">
        {route?.name === 'tech' && <TechnologyPage slug={route.slug} />}
        {route?.name === 'topic' && <TopicPage refKey={route.ref} />}
        {route?.name === 'topics' && <TopicsPage technologies={data?.items ?? []} route={route} />}
        {!route && tab === 'rankings' && data && (
          <div className="grid items-start gap-8 md:grid-cols-[minmax(0,1.9fr)_minmax(0,1fr)]">
            <RankingCard items={data.items} categories={data.categories} onSelect={setSelected} />
            <EmergingCard rows={data.emerging} onSelect={setSelected} />
          </div>
        )}
        {!route && tab === 'compare' && <ComparePage technologies={data?.items ?? []} />}
        {!route && tab === 'skills' && <SkillGapPage technologies={data?.items ?? []} />}
        {!route && tab === 'blogs' && <BlogsPage technologies={data?.items ?? []} />}
        {!route && tab === 'news' && <NewsPage />}
        {!route && tab === 'repos' && <ReposPage />}
        {!route && tab === 'moderation' && isMod && <ModerationPage />}
        {!route && tab === 'guidelines' && <GuidelinesPage />}
        {!route && tab === 'privacy' && <PrivacyPage />}
        {!route && tab === 'profile' && <ProfilePage technologies={data?.items ?? []} onSelect={setSelected} />}
      </div>

      </Suspense>

      <footer className="mt-12 flex flex-wrap gap-4 border-t-[3px] border-ink pt-4 text-sm font-bold">
        <button type="button" className="cursor-pointer underline decoration-2 underline-offset-4 hover:bg-sun" onClick={() => openTab('guidelines')}>Community guidelines</button>
        <button type="button" className="cursor-pointer underline decoration-2 underline-offset-4 hover:bg-sun" onClick={() => openTab('privacy')}>Privacy</button>
      </footer>

      {selected && (
        <Suspense fallback={null}>
          <DetailDialog slug={selected} onClose={() => setSelected(null)} />
        </Suspense>
      )}
    </div>
  )
}
