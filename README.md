# RESOLUTE Local

The **local civic-engagement arm** of the [RESOLUTE Citizen](https://usmcmin.com/citizen.html)
framework (U.S.M.C. Ministries). Equips Christians to know what their city council is
deciding and to show up where it counts — starting with **Fredericksburg, VA**.

Live site: GitHub Pages (`adamljohns.github.io/resolute-local`, custom domain TBD).

## How it works

```
city AgendaCenter (fredericksburgva.gov)
   │  scraped 2×/day by ~/Scripts/fxbg-civic-rounds.sh (cron com.moop.fxbg-civic-rounds)
   ▼
~/.openclaw/shared-memory/context/fxbg-civic-latest.json   (raw snapshot)
   │  publish-fredericksburg.py  (transform → clean site data)
   ▼
data/fredericksburg.json   (committed + pushed → GitHub Pages)
   │  fetched client-side
   ▼
city/fredericksburg.html   (renders the live next meeting, agenda, council)
```

## Structure
- `index.html` — landing + multi-city directory
- `city/fredericksburg.html` — Fredericksburg civic hub (live next meeting + curated content)
- `city/fredericksburg-council-notes.html` — Council Watch meeting notes
- `data/<city>.json` — per-city live civic data (published by the pipeline)
- `publish-<city>.py` — transform script (shared-memory snapshot → site data)
- `assets/` — shared CSS/JS (mirrors usmcmin.com design)

## Build phases
- **Phase 1 (done):** live agenda data wired into the page + cron publish step.
- **Phase 2:** agenda → plain-English citizen briefs (what's decided / why it matters / how to weigh in).
- **Phase 3:** activism tools (comment deadlines, draft-a-comment, .ics calendar, contact council).

## Adding a city
1. Add a `publish-<city>.py` for that locality's agenda source.
2. Generate `data/<city>.json`.
3. Copy `city/fredericksburg.html` → `city/<city>.html`, point its fetch at the new data.
4. Add a card to `index.html`.

## Maintenance
The scrape cron runs 2×/day; the publish step writes + pushes the data so the live site
self-updates. See the parent `MAINTENANCE.md` pattern in usmcmin-com.
