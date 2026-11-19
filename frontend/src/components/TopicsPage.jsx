import { useEffect, useState } from 'react'
import { Link } from '../lib/router'

export default function TopicsPage() {
  const [topics, setTopics] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/topics')
      .then(res => res.json())
      .then(data => {
        setTopics(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  if (loading) return <div className="di-wrap">Loading topics...</div>

  return (
    <div className="di-wrap">
      <div style={{ marginBottom: '1.5rem' }}>
        <Link to="/topics/new" className="di-btn di-btn--lime">Start a New Topic</Link>
      </div>
      
      {topics.length === 0 ? (
        <p>No topics yet. Be the first to start one!</p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {topics.map(t => (
            <li key={t.id} style={{ padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '8px', background: '#fff' }}>
              <Link to={`/topics/${t.id}`} style={{ fontSize: '1.1rem', fontWeight: 'bold', textDecoration: 'none', color: '#111' }}>
                {t.title}
              </Link>
              <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.5rem' }}>
                by {t.author_name || 'Anonymous'} • {new Date(t.created_at).toLocaleDateString()}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}