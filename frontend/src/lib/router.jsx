import { useEffect, useState } from 'react'

// A tiny hash router: pages live at /#/rankings, /#/news ... so it works with the
// single-server build (FastAPI only has to serve index.html) and needs no extra package.
function readPath() {
  const raw = window.location.hash.replace(/^#/, '').split('?')[0]
  if (!raw) return '/'
  return raw.startsWith('/') ? raw : `/${raw}`
}

export function useRoute() {
  const [path, setPath] = useState(readPath)
  useEffect(() => {
    const onChange = () => setPath(readPath())
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return path
}

export function Link({ to, children, ...rest }) {
  return <a href={`#${to}`} {...rest}>{children}</a>
}