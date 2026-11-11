import { Link } from '../lib/router'

export default function Footer() {
  return (
    <footer className="di-footer">
      <div className="di-wrap di-footer__grid">
        <div>
          <span className="di-logo">DevIntel</span>
          <p>A developer intelligence platform. It turns daily public data into a transparent score, so choosing what to learn is based on evidence.</p>
          <p><span className="di-chip bg-sun" style={{ color: '#000' }}>UN SDG 9: Industry, Innovation and Infrastructure</span></p>
        </div>
        <div>
          <h2>Explore</h2>
          <ul>
            <li><Link to="/rankings">Rankings</Link></li>
            <li><Link to="/compare">Compare</Link></li>
            <li><Link to="/skills">Skill gap</Link></li>
            <li><Link to="/news">News</Link></li>
            <li><Link to="/repos">Trending repos</Link></li>
            <li><Link to="/hub">AI hub</Link></li>
          </ul>
        </div>
        <div>
          <h2>Project</h2>
          <ul>
            <li><a href="https://github.com/anaydev29/DevIntel" target="_blank" rel="noopener noreferrer">Source code on GitHub</a></li>
            <li><a href="/docs" target="_blank" rel="noopener noreferrer">API documentation</a></li>
            <li>Built by Anay Shivhare at MITS Gwalior</li>
            <li>Guide: Prof. Jigyasa Mishra</li>
          </ul>
        </div>
      </div>
      <div className="di-wrap di-footer__legal">
        Data comes from public APIs (GitHub, Stack Overflow, Hacker News, Dev.to, Hugging Face, Kaggle). Every source has its own bias, so growth is always shown next to size.
      </div>
    </footer>
  )
}
