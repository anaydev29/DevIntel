import { useEffect, useState } from 'react'

// Tiny hash router, so pages have links that can be shared and bookmarked and that need no server setup:
//   #/tech/python       a technology's own page
//   #/topics            the list of topics        #/topics/new?tech=react&article=12&about=Title   (start a topic)
//   #/topic/abc123      one topic
export function parseRoute(hash = window.location.hash) {
  const [path, query = ''] = hash.replace(/^#\/?/, '').split('?')
  const parts = path.split('/').filter(Boolean).map(decodeURIComponent)
  const params = new URLSearchParams(query)
  if (parts[0] === 'tech' && parts[1]) return { name: 'tech', slug: parts[1] }
  if (parts[0] === 'topic' && parts[1]) return { name: 'topic', ref: parts[1] }
  if (parts[0] === 'topics') {
    return { name: 'topics', creating: parts[1] === 'new', tech: params.get('tech'), articleId: params.get('article'), about: params.get('about') }
  }
  return null
}

export function useRoute() {
  const [route, setRoute] = useState(parseRoute)
  useEffect(() => {
    const onChange = () => setRoute(parseRoute())
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}

export const goHome = () => { window.location.hash = '' }
export const techLink = (slug) => `#/tech/${encodeURIComponent(slug)}`
export const topicLink = (ref) => `#/topic/${encodeURIComponent(ref)}`
export const newTopicLink = ({ tech, articleId, about } = {}) => {
  const q = new URLSearchParams()
  if (tech) q.set('tech', tech)
  if (articleId) q.set('article', articleId)
  if (about) q.set('about', about)
  return `#/topics/new${q.toString() ? `?${q}` : ''}`
}
