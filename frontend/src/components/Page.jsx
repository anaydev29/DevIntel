// Shared frame for the inner pages: a big title block, then the page content.
export default function Page({ kicker, title, intro, children }) {
  return (
    <div className="di-wrap di-page">
      <header className="di-ph">
        <span className="di-kicker">{kicker}</span>
        <h1>{title}</h1>
        {intro && <p>{intro}</p>}
      </header>
      {children}
    </div>
  )
}
