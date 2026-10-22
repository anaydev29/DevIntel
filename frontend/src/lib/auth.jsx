import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { authMe, loadProfile, signOutRequest } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [state, setState] = useState({ loading: true, user: null, loginEnabled: false })
  const [profile, setProfile] = useState(null)

  const refreshProfile = useCallback(async () => setProfile(await loadProfile()), [])

  useEffect(() => {
    authMe()
      .then(async (m) => {
        setState({ loading: false, user: m.user, loginEnabled: m.login_enabled })
        if (m.authenticated) setProfile(await loadProfile())
      })
      .catch(() => setState((s) => ({ ...s, loading: false })))
  }, [])

  const signOut = useCallback(async () => {
    await signOutRequest()
    setState((s) => ({ ...s, user: null }))
    setProfile(null)
  }, [])

  const value = useMemo(
    () => ({ ...state, authenticated: !!state.user, profile, setProfile, refreshProfile, signOut }),
    [state, profile, refreshProfile, signOut],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
