import { useEffect, useState } from 'react'
import { Link } from '../lib/router'
import AccountBar from './AccountBar'

export const NAV = [
  ['/rankings', 'Rankings'],
  ['/compare', 'Compare'],
  ['/skills', 'Skill gap'],
  ['/news', 'News'],
  ['/blogs', 'Blogs'],
  ['/repos', 'Trending repos'],
]

export default function Nav({ path }) {
  const [open, setOpen] = useState(false)
  useEffect(() => setOpen(false), [path])
  const links = NAV.map(([to, label]) => (
    <Link key={to} to={to} className="di-navlink" aria-current={path === to ? 'page' : undefined}>{label}</Link>
  ))
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
