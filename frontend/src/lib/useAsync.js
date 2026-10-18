import { useEffect, useState } from 'react'

// Runs an async loader whenever `deps` change and reports loading / error / data.
export function useAsync(loader, deps) {
  const [state, setState] = useState({ loading: true, error: false, data: null })
  useEffect(() => {
    let cancelled = false
    setState((s) => ({ ...s, loading: true, error: false }))
    loader()
      .then((data) => !cancelled && setState({ loading: false, error: false, data }))
      .catch(() => !cancelled && setState({ loading: false, error: true, data: null }))
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return state
}
