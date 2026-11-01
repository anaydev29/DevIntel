# DevIntel frontend v2 (landing page, 3D hero, separate pages)

## Install
Unzip over your DEVINTEL folder (it only touches `frontend/src`). Then, in the `frontend` folder:

```powershell
npm install three
npm run dev
```

If the fonts ever fail to resolve, also run: `npm install @fontsource/archivo-black @fontsource/space-grotesk`

## What is new
- `/#/` Landing page: new hero, live stats from your API, a Three.js scene that tilts with the mouse (click it to spin it),
  a ticker of the top technologies, a live leaderboard, "How a score is made", and links to every page.
- Separate pages with a sticky navigation bar: `/#/rankings` (search, category filter, sort, pagination),
  `/#/compare`, `/#/skills`, `/#/news`, `/#/blogs`, `/#/repos`, `/#/profile`.
- The old components (Compare, Skill gap, Profile, detail popup) are reused inside the new layout.
- New files: `redesign.css`, `lib/router.jsx`, and in `components/`: `Nav`, `StatusStrip`, `Footer`, `Page`, `Home`, `HeroScene`,
  `SceneFallback`, `RankingsPage`. Replaced: `App.jsx`, `components/AccountBar.jsx`, `components/Feeds.jsx`.
- No longer used (you can delete them): `components/Hero.jsx`, `components/RankingCard.jsx`, `components/EmergingCard.jsx`.

## Notes
- Pages use hash routes (`/#/rankings`), so the single-server build needs no extra server settings.
- The Three.js scene is loaded in the background. If WebGL is not available or the file fails to load, a static illustration
  is shown instead. It stays still for visitors who prefer reduced motion, and it pauses when scrolled out of view.
- The score weights shown on the landing page are written in `components/Home.jsx` (`WEIGHTS`). Keep them in sync with
  `backend/app/analysis.py` if you change the backend.
- Every number on the landing page comes from the API. Nothing is hard-coded except the documented weights.
