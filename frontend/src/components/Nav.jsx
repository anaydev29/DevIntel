import { useEffect, useState } from 'react'
import { Link } from '../lib/router'
import { useAuth } from '../lib/auth'
import AccountBar from './AccountBar'

export const NAV = [
  ['/rankings', 'Rankings'],
  ['/compare', 'Compare'],
  ['/skills', 'Skill gap'],
  ['/topics', 'Topics'],
  ['/news', 'News'],
  ['/blogs', 'Blogs'],
  ['/repos', 'Trending repos'],
]

export default function Nav({ path }) {
  const { user } = useAuth()
  const isMod = user?.role === 'moderator' || user?.role === 'admin'
  const [open, setOpen] = useState(false)
  useEffect(() => setOpen(false), [path])

  const navItems = isMod ? [...NAV, ['/moderation', 'Moderation']] : NAV

  const links = navItems.map(([to, label]) => {
    const isCurrent = path === to || (to === '/topics' && (path.startsWith('/topic') || path.startsWith('/topics')))
    const isModLink = to === '/moderation'
    return (
      <Link
        key={to}
        to={to}
        className={`di-navlink ${isModLink ? 'di-navlink--mod' : ''}`}
        aria-current={isCurrent ? 'page' : undefined}
      >
        {label}
      </Link>
    )
  })
  return (
    <header className="di-nav">
      <div className="di-wrap di-nav__inner">
        <Link to="/" className="di-logo" aria-label="DevIntel home">DevIntel</Link>
        <nav className="di-links" aria-label="Main">{links}</nav>
        <AccountBar />
        <button
          type="button" className="di-btn di-btn--sm di-burger" aria-expanded={open} aria-controls="di-mobile-nav"
          onClick={() => setOpen((o) => !o)}
        >
          {open ? 'Close' : 'Menu'}
        </button>
      </div>
      {open && <nav id="di-mobile-nav" className="di-mobile" aria-label="Main mobile">{links}</nav>}
    </header>
  )
}
