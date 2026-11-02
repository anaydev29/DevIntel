import { useEffect, useState } from 'react'

// Tiny hash router supporting path, dynamic segments (/tech/:slug, /topic/:ref, /topics/new) and query parameters
export function readRoute() {
  const hash = window.location.hash.replace(/^#\/?/, '')
  const [rawPath = '', rawQuery = ''] = hash.split('?')
  const parts = rawPath.split('/').filter(Boolean).map(decodeURIComponent)
  const path = rawPath ? (rawPath.startsWith('/') ? rawPath : `/${rawPath}`) : '/'
  const query = new URLSearchParams(rawQuery)

  let name = 'page'
  let slug = null
  let ref = null

  if (!parts.length) {
    name = 'home'
  } else if (parts[0] === 'tech' && parts[1]) {
    name = 'tech'
    slug = parts[1]
  } else if (parts[0] === 'topic' && parts[1]) {
    name = 'topic'
    ref = parts[1]
  } else if (parts[0] === 'topics') {
    name = 'topics'
  }

  return {
    path,
    rawPath,
    parts,
    query,
    name,
    slug,
    ref,
    creating: parts[0] === 'topics' && parts[1] === 'new',
    tech: query.get('tech'),
    articleId: query.get('article'),
    about: query.get('about'),
  }
}

export function useRoute() {
  const [route, setRoute] = useState(readRoute)
  useEffect(() => {
    const onChange = () => setRoute(readRoute())
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}

export function Link({ to, children, ...rest }) {
  const href = `#${to.startsWith('/') ? to : `/${to}`}`
  return <a href={href} {...rest}>{children}</a>
}
