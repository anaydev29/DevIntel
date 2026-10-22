import { useAuth } from '../lib/auth'

const btn = 'press cursor-pointer border-[3px] border-ink px-4 py-1.5 font-bold shadow-brut-xs hover:bg-sun'

export default function AccountBar({ onProfile }) {
  const { loading, user, loginEnabled, signOut } = useAuth()
  const failed = new URLSearchParams(window.location.search).get('login') === 'failed'
  return (
    <div className="flex min-h-10 flex-wrap items-center justify-end gap-3">
      {failed && <span className="border-2 border-ink bg-hot px-2 text-sm font-bold" role="alert">Sign-in failed. Please try again.</span>}
      {!loading && user && (
        <>
          <button type="button" onClick={onProfile} className={`${btn} flex items-center gap-2 bg-white`}>
            {user.avatar_url ? (
              <img src={user.avatar_url} alt="" referrerPolicy="no-referrer" className="h-6 w-6 border-2 border-ink" />
            ) : (
              <span className="grid h-6 w-6 place-items-center border-2 border-ink bg-sun text-sm">{(user.name || user.email)[0].toUpperCase()}</span>
            )}
            {user.name || user.email}
          </button>
          <button type="button" onClick={signOut} className={`${btn} bg-white`}>Sign out</button>
        </>
      )}
      {!loading && !user && loginEnabled && <a href="/auth/google/login" className={`${btn} bg-white`}>Sign in with Google</a>}
      {!loading && !user && !loginEnabled && <span className="text-sm">Sign-in is not set up on this server</span>}
    </div>
  )
}
