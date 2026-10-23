const card = 'border-[3px] border-ink bg-white p-5 shadow-brut'
const h = 'mt-5 mb-1 font-display text-xl'

export function GuidelinesPage() {
  return (
    <article className={`${card} max-w-3xl`}>
      <h2 className="font-display text-3xl leading-tight">Community guidelines</h2>
      <p className="mt-2">DevIntel is a student project. Discussions are here to help people learn about technology, so please keep them useful and kind.</p>
      <h3 className={h}>Do</h3>
      <ul className="list-disc pl-5">
        <li>Be respectful, even when you disagree. Argue with ideas, not people.</li>
        <li>Stay on topic: the technology, article or repository being discussed.</li>
        <li>Share what you know, ask honest questions, and say thanks.</li>
      </ul>
      <h3 className={h}>Do not</h3>
      <ul className="list-disc pl-5">
        <li>Post spam, advertising or repeated links. Comments can contain at most 2 links, and links are not clickable.</li>
        <li>Harass, insult, threaten or discriminate against anyone.</li>
        <li>Share other people's private information, or your own passwords or keys.</li>
        <li>Post illegal content, or anything copied from somewhere else without credit.</li>
      </ul>
      <h3 className={h}>What happens if the rules are broken</h3>
      <ul className="list-disc pl-5">
        <li>Anyone signed in can <b>report</b> a comment. A comment reported by 3 different established accounts is hidden until a moderator reviews it.</li>
        <li>Moderators can keep a comment, remove it, or <b>ban</b> an account. A banned account can still read DevIntel but cannot post, vote or report.</li>
        <li>Every moderator action is recorded in a log, so decisions can be checked.</li>
        <li>You can edit or delete your own comments at any time.</li>
      </ul>
      <p className="mt-5 text-sm">Moderators are people too and can make mistakes. If you think a decision was wrong, contact the project owner.</p>
    </article>
  )
}

export function PrivacyPage() {
  return (
    <article className={`${card} max-w-3xl`}>
      <h2 className="font-display text-3xl leading-tight">Privacy</h2>
      <p className="mt-2">DevIntel is a student project. This page explains in plain words what it keeps. It is not legal advice.</p>
      <h3 className={h}>What we store, only if you sign in</h3>
      <ul className="list-disc pl-5">
        <li>From Google: your Google account ID, email address, name and profile picture link. We never see your Google password.</li>
        <li>What you choose to save: your GitHub username, your skills and your watchlist.</li>
        <li>What you do on the site: your comments, upvotes and reports.</li>
      </ul>
      <p className="mt-2">Browsing DevIntel without signing in stores nothing about you.</p>
      <h3 className={h}>What other people can see</h3>
      <ul className="list-disc pl-5">
        <li>Your comments, shown with your <b>first name and last initial</b> (for example "Anay S.").</li>
        <li>Nothing else. Your email, profile picture, skills, GitHub username and watchlist are private to you. Moderators and the site admin can see your email when managing accounts.</li>
      </ul>
      <h3 className={h}>Cookies</h3>
      <p>One login cookie keeps you signed in for up to 14 days. It is cleared when you sign out. There is no advertising or tracking.</p>
      <h3 className={h}>Where data lives</h3>
      <p>In a hosted database used by this project. Public data about technologies (from GitHub, Stack Overflow, Hacker News and dev.to) is collected through their official APIs and contains no personal accounts of DevIntel users.</p>
      <h3 className={h}>Your choices</h3>
      <ul className="list-disc pl-5">
        <li>Open <b>My profile</b> and choose <b>Delete my account</b>. This permanently deletes your account, saved skills, watchlist, comments, votes and reports.</li>
        <li>Delete or edit any single comment at any time.</li>
        <li>The moderator action log keeps a record of moderation decisions without your email.</li>
      </ul>
      <p className="mt-5 text-sm">Questions: contact the project owner (add the project email here before launch).</p>
    </article>
  )
}
