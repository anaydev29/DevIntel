import { useEffect, useState } from 'react'
import './redesign.css'
import { loadDashboard } from './lib/api'
import { Link, useRoute } from './lib/router'
import Nav from './components/Nav'
import StatusStrip from './components/StatusStrip'
import Footer from './components/Footer'
import Page from './components/Page'
import Home from './components/Home'
import RankingsPage from './components/RankingsPage'
import { BlogsPage, NewsPage, ReposPage } from './components/Feeds'
import HubPage from './components/HubPage'
import ComparePage from './components/ComparePage'
import SkillGapPage from './components/SkillGapPage'
import ProfilePage from './components/ProfilePage'
import DetailDialog from './components/DetailDialog'

const TITLES = {
  '/': 'DevIntel: what developers use, and what is taking off',
  '/rankings': 'Rankings',
  '/compare': 'Compare',
  '/skills': 'Skill gap',
  '/news': 'News',
  '/blogs': 'Blogs',
  '/repos': 'Trending repos',
  '/hub': 'AI hub',
  '/profile': 'My profile',
}

export default function App() {
  const path = useRoute()
  const [data, setData] = useState(null)
  const [error, setError] = useState(false)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    loadDashboard().then(setData).catch(() => setError(true))
  }, [])

  useEffect(() => {
    window.scrollTo(0, 0)
    const title = TITLES[path]
    document.title = path === '/' ? title : `${title ?? 'Page not found'} | DevIntel`
  }, [path])

  const technologies = data?.items ?? []
  let page
  switch (path) {
    case '/':
      page = <Home data={data} onSelect={setSelected} />
      break
    case '/rankings':
      page = <RankingsPage data={data} onSelect={setSelected} />
      break
    case '/compare':
      page = <Page kicker="Page 02" title="Compare" intro="Put two technologies side by side and see which one leads on each signal."><ComparePage technologies={technologies} /></Page>
      break
    case '/skills':
      page = <Page kicker="Page 03" title="Skill gap" intro="Tell DevIntel what you already know, or give a GitHub username, and get ranked advice on what to learn next."><SkillGapPage technologies={technologies} /></Page>
      break
    case '/news':
      page = <NewsPage />
      break
    case '/blogs':
      page = <BlogsPage technologies={technologies} />
      break
    case '/repos':
      page = <ReposPage />
      break
    case '/hub':
      page = <HubPage />
      break
    case '/profile':
      page = <Page kicker="Account" title="My profile" intro="Your saved skills, GitHub username and watchlist."><ProfilePage technologies={technologies} onSelect={setSelected} /></Page>
      break
    default:
      page = (
        <Page kicker="404" title="Page not found" intro="That page does not exist.">
          <Link to="/" className="di-btn di-btn--lime">Back to the home page</Link>
        </Page>
      )
  }

  return (
    <div className="di-app">
      <a href="#main" className="di-skip" onClick={(e) => { e.preventDefault(); document.getElementById('main')?.focus() }}>Skip to content</a>
      <Nav path={path} />
      <StatusStrip runs={data?.runs ?? []} loading={!data && !error} />
      {error && (
        <div className="di-wrap">
          <div className="di-alert" role="alert">Cannot reach the DevIntel API. Start it with: uvicorn app.main:app --reload --reload-dir app</div>
        </div>
      )}
      <main id="main" tabIndex={-1} className="di-main" style={{ outline: 'none' }}>{page}</main>
      <Footer />
      <DetailDialog slug={selected} onClose={() => setSelected(null)} />
    </div>
  )
}