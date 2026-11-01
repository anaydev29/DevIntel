import { Link } from '../lib/router'
import { useAuth } from '../lib/auth'

// Sign-in controls shown on the right of the navigation bar.
export default function AccountBar() {
  const { loading, user, loginEnabled, signOut } = useAuth()
  const failed = new URLSearchParams(window.location.search).get('login') === 'failed'
  return (
    <div className="di-account">
      {failed && <span className="di-chip bg-hot" role="alert">Sign-in failed. Please try again.</span>}
      {!loading && user && (
        <>
          <Link to="/profile" className="di-btn di-btn--sm" aria-label="My profile">
            {user.avatar_url ? (
              <img src={user.avatar_url} alt="" referrerPolicy="no-referrer" width="22" height="22" style={{ border: '2px solid #000' }} />
            ) : (
              <span className="di-chip bg-sun">{(user.name || user.email)[0].toUpperCase()}</span>
            )}
            <span className="di-account__name">{user.name || user.email}</span>
          </Link>
          <button type="button" onClick={signOut} className="di-btn di-btn--sm">Sign out</button>
        </>
      )}
      {!loading && !user && loginEnabled && <a href="/auth/google/login" className="di-btn di-btn--sm di-btn--lime"><span className="di-hide-sm">Sign in with Google</span><span className="di-show-sm">Sign in</span></a>}
    </div>
  )
}
