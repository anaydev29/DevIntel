import { useEffect, useState } from 'react'
import './redesign.css'
import { loadDashboard } from './lib/api'
import { Link } from './lib/router'
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
import TopicsPage from './components/TopicsPage'
import TopicPage from './components/TopicPage'
import NewTopicPage from './components/NewTopicPage'
import ModerationPage from './components/ModerationPage'
import BacktestPage from './components/BacktestPage'
import TechnologyPage from './components/TechnologyPage'
import { GuidelinesPage, PrivacyPage } from './components/LegalPages'

const TITLES = {
  rankings: 'Rankings', compare: 'Compare', skills: 'Skill gap', news: 'News',
  blogs: 'Blogs', repos: 'Trending repos', hub: 'AI hub', topics: 'Topics',
  profile: 'My profile', moderation: 'Moderation', backtest: 'Backtest',
  guidelines: 'Community guidelines', privacy: 'Privacy', tech: 'Technology', topic: 'Topic',
}

// Unified hash parser: understands BOTH the simple top pages (#/rankings)
// and the structured links used by the components (#/tech/:slug, #/topic/:ref, #/topics/new?...).
function useHash() {
  const [hash, setHash] = useState(window.location.hash)
  useEffect(() => {
    const on = () => setHash(window.location.hash)
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  const raw = hash.replace(/^#\/?/, '')
  const [p, q = ''] = raw.split('?')
  const parts = p.split('/').filter(Boolean).map(decodeURIComponent)
  return { parts, params: new URLSearchParams(q), path: '/' + parts.join('/') }
}

export default function App() {
  const { parts, params, path } = useHash()
  const [data, setData] = useState(null)
  const [error, setError] = useState(false)
  const [selected, setSelected] = useState(null)

  useEffect(() => { loadDashboard().then(setData).catch(() => setError(true)) }, [])

  useEffect(() => {
    window.scrollTo(0, 0)
    const root = parts[0]
    const title = parts.length === 0
      ? 'DevIntel: what developers use, and what is taking off'
      : (TITLES[root] ?? 'Page not found')
    document.title = parts.length === 0 ? title : `${title} | DevIntel`
  }, [path])

  const technologies = data?.items ?? []
  const root = parts[0]
  let page

  if (parts.length === 0) {
    page = <Home data={data} onSelect={setSelected} />
  } else if (root === 'rankings') {
    page = <RankingsPage data={data} onSelect={setSelected} />
  } else if (root === 'compare') {
    page = <Page kicker="Page 02" title="Compare" intro="Put two technologies side by side and see which one leads on each signal."><ComparePage technologies={technologies} /></Page>
  } else if (root === 'skills') {
    page = <Page kicker="Page 03" title="Skill gap" intro="Tell DevIntel what you already know, or give a GitHub username, and get ranked advice on what to learn next."><SkillGapPage technologies={technologies} /></Page>
  } else if (root === 'news') {
    page = <NewsPage />
  } else if (root === 'blogs') {
    page = <BlogsPage technologies={technologies} />
  } else if (root === 'repos') {
    page = <ReposPage />
  } else if (root === 'hub') {
    page = <HubPage />
  } else if (root === 'profile') {
    page = <Page kicker="Account" title="My profile" intro="Your saved skills, GitHub username and watchlist."><ProfilePage technologies={technologies} onSelect={setSelected} /></Page>
  } else if (root === 'topics') {
    if (parts[1] === 'new') {
      page = <Page kicker="Community" title="Start a topic" intro="Open a discussion. Optionally link it to a technology or an article."><NewTopicPage tech={params.get('tech')} articleId={params.get('article')} about={params.get('about')} /></Page>
    } else {
      page = <Page kicker="Community" title="Topics" intro="Discussions started by the community. Sign in to start one."><TopicsPage /></Page>
    }
  } else if (root === 'topic' && parts[1]) {
    page = <div className="di-wrap"><TopicPage refKey={parts[1]} /></div>
  } else if (root === 'tech' && parts[1]) {
    page = <div className="di-wrap"><TechnologyPage slug={parts[1]} /></div>
  } else if (root === 'moderation') {
    page = <div className="di-wrap"><ModerationPage /></div>
  } else if (root === 'backtest') {
    page = <div className="di-wrap"><BacktestPage /></div>
  } else if (root === 'guidelines') {
    page = <div className="di-wrap"><GuidelinesPage /></div>
  } else if (root === 'privacy') {
    page = <div className="di-wrap"><PrivacyPage /></div>
  } else {
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