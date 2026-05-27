#!/usr/bin/env python3
"""
publish-fredericksburg.py — Phase 1: transform the civic-rounds pipeline output
into clean site data the public page can render.

Reads the cron's snapshot (shared-memory/fxbg-civic-latest.json, refreshed 2x/day
by ~/Scripts/fxbg-civic-rounds.sh) and writes data/fredericksburg.json — the live
source of truth the FXBG civic page fetches.

Run by the cron's publish step after each scrape; also runnable by hand:
    python3 publish-fredericksburg.py
"""
import json
import re
import os
from pathlib import Path

REPO = Path(__file__).parent
SRC = Path.home() / '.openclaw' / 'shared-memory' / 'context' / 'fxbg-civic-latest.json'
MINUTES = Path.home() / '.openclaw' / 'shared-memory' / 'context' / 'fxbg-minutes-state.json'  # Phase 3 (2026-05-27): vote outcomes from parsed minutes
SCORECARD_INDEX = Path.home() / '.openclaw' / 'workspace' / 'usmcmin-com' / 'data' / 'search-index.json'  # Phase 4 (2026-05-27): cross-link to RESOLUTE Citizen profiles
OUT = REPO / 'data' / 'fredericksburg.json'
BRIEFS = REPO / 'briefs' / 'fredericksburg.json'   # Phase 2: authored/auto citizen briefs

# Lines that are pure structural noise we don't surface as agenda items
NOISE = {'agenda', 'city council', 'topics', 'call to order', '&nbsp;', ':', 'pm',
         'council chambers', 'a.', 'b.', 'c.', 'd.', 'i.', 'ii.', 'iii.'}


def parse_council(lines):
    """Pull the 'Hon. NAME[, Jr.], ROLE[, WARD]' roster lines into members."""
    members = []
    for ln in lines:
        m = re.match(r'^Hon\.\s+(.+)$', ln.strip())
        if not m:
            continue
        rest = m.group(1).strip()
        parts = [p.strip() for p in rest.split(',')]
        # Re-attach a generational suffix to the name (Jr./Sr./II/III/IV)
        name = parts[0]
        idx = 1
        if idx < len(parts) and re.match(r'^(Jr\.?|Sr\.?|II|III|IV)$', parts[idx], re.I):
            name = f'{name}, {parts[idx]}'
            idx += 1
        role = ', '.join(parts[idx:]).strip()
        if role:
            members.append({'name': name, 'role': role})
    return members


def parse_meeting(na):
    """Best-effort structured summary of the next meeting from agenda lines."""
    lines = [l.strip() for l in (na.get('lines') or [])]

    # Time is often split across lines ("5" / ":" / "30pm"). Join + normalise.
    joined = ' '.join(lines)
    joined = re.sub(r'(\d{1,2})\s*:\s*(\d{2})', r'\1:\2', joined)   # "5 : 30" -> "5:30"
    tm = re.search(r'(\d{1,2}:\d{2}\s*[ap]\.?m\.?)', joined, re.I)
    when_time = tm.group(1).replace(' ', '') if tm else ''

    title = ''
    location = ''
    for l in lines:
        if not title and re.search(r'(work session|regular session|public hearing|meeting)\s+agenda$', l, re.I):
            title = re.sub(r'\s+agenda$', '', l, flags=re.I).strip()
        if 'princess anne' in l.lower():
            location = '715 Princess Anne Street, Council Chambers, Fredericksburg, VA 22401'
    if not title:
        title = 'City Council Session'

    # Substantive agenda items: descriptive topic lines only. Drop boilerplate,
    # the title/address/time fragments, numbering, and short noise.
    items = []
    seen = set()
    drop_re = re.compile(r'^(agenda|city of|hon\.|fredericksburg|council chambers|'
                         r'\d+\s*princess anne|members of the public|joint work session|'
                         r'regular session|public hearing|call to order|topics|'
                         r'\d{1,2}:\d{2}|.*in council chambers$)', re.I)
    for l in lines:
        low = l.lower().strip()
        if len(l) < 25:                       # topics are descriptive; drop fragments
            continue
        if low in NOISE or l.startswith('&nbsp;') or drop_re.match(low):
            continue
        words = [w for w in re.split(r'\s+', l) if w]
        if len(words) < 4:                    # need a real phrase
            continue
        if l in seen:
            continue
        seen.add(l)
        items.append(l)
    return {
        'title': title,
        'date': na.get('date', ''),
        'time': when_time,
        'location': location,
        'agenda_url': na.get('url', ''),
        'items': items[:25],
        'raw_lines': lines,          # kept for Phase 2 brief generation
    }


def main():
    if not SRC.exists():
        raise SystemExit(f'pipeline snapshot not found: {SRC} (run fxbg-civic-rounds.sh first)')
    raw = json.loads(SRC.read_text())
    na = raw.get('next_agenda', {}) or {}
    council = parse_council(na.get('lines', []))
    next_meeting = parse_meeting(na)

    out = {
        'city': 'Fredericksburg',
        'state': 'VA',
        'slug': 'fredericksburg',
        'updated': raw.get('ts', ''),
        'updated_local': raw.get('ts_local', ''),
        'source': (raw.get('sources') or ['fredericksburgva.gov/AgendaCenter'])[0],
        'agenda_center': 'https://www.fredericksburgva.gov/AgendaCenter',
        'council': council,
        'next_meeting': next_meeting,
        'meetings': raw.get('meetings', []),
        'briefs': {},   # Phase 2: filled from briefs/fredericksburg.json below
    }
    # Phase 2 — merge authored/auto citizen briefs (keyed by meeting date)
    if BRIEFS.exists():
        try:
            bdata = json.loads(BRIEFS.read_text())
            out['briefs'] = {k: v for k, v in bdata.items() if not k.startswith('_')}
        except (json.JSONDecodeError, ValueError):
            pass

    # Phase 3 (2026-05-27) — merge parsed-minutes vote outcomes into the
    # matching meeting record (by date + body=City Council). Each meeting
    # may gain `minutes_available: true`, `minutes_url`, `minutes_pages`,
    # `council_present`, `council_absent`, and a `resolutions_voted` list
    # with per-vote ayes/nays/abstain breakdowns. Multiple minutes docs
    # can match one date (Public Hearing + Regular Session) — we attach
    # all of them. Minutes from older meetings NOT in the current agenda
    # snapshot (the agenda center ages out older items) are also injected
    # as standalone historical entries so the page can show vote history
    # going back as far as minutes are available.
    minutes_count = 0
    injected_count = 0
    if MINUTES.exists():
        try:
            mstate = json.loads(MINUTES.read_text())
            # Index by meeting_date for fast lookup. Group multiple
            # docs (e.g., Public Hearing + Regular Session same date).
            by_date: dict[str, list] = {}
            for p in mstate.get('processed', []):
                if p.get('error') or not p.get('meeting_date'):
                    continue
                by_date.setdefault(p['meeting_date'], []).append(p)

            existing_dates = {
                (m.get('date'), (m.get('session_type') or '').lower())
                for m in out.get('meetings', []) if isinstance(m, dict)
            }

            # Pass 1: enrich existing meeting records that match by date.
            for m in out.get('meetings', []):
                if not isinstance(m, dict):
                    continue
                if (m.get('body') or '').lower() != 'city council':
                    continue
                matches = by_date.get(m.get('date'), [])
                if not matches:
                    continue
                pick = matches[0]
                if len(matches) > 1 and m.get('session_type'):
                    aligned = [x for x in matches if (x.get('session_type','').lower() == m['session_type'].lower())]
                    if aligned:
                        pick = aligned[0]
                m['minutes_available'] = True
                m['minutes_url'] = pick.get('url')
                m['minutes_pages'] = pick.get('pages')
                m['council_present'] = pick.get('council_present', [])
                m['council_absent'] = pick.get('council_absent', [])
                m['resolutions_voted'] = pick.get('resolutions', [])
                minutes_count += 1

            # Pass 2: inject historical meetings that no longer appear in
            # the agenda-center snapshot but DO have minutes posted.
            for date_str, minutes_list in by_date.items():
                for p in minutes_list:
                    sess = (p.get('session_type') or '').lower()
                    if (date_str, sess) in existing_dates:
                        continue
                    out['meetings'].append({
                        'date': date_str,
                        'body': 'City Council',
                        'session_type': p.get('session_type'),
                        'url': None,  # agenda is no longer linked from listing
                        'sections': [],
                        'minutes_available': True,
                        'minutes_url': p.get('url'),
                        'minutes_pages': p.get('pages'),
                        'council_present': p.get('council_present', []),
                        'council_absent': p.get('council_absent', []),
                        'resolutions_voted': p.get('resolutions', []),
                        'historical_injection': True,
                    })
                    injected_count += 1
            # Re-sort meetings newest-first after injection
            out['meetings'].sort(key=lambda m: (m.get('date') or '0'), reverse=True)
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

    # Phase 4 (2026-05-27) — cross-link to RESOLUTE Citizen scorecard.
    # Loads usmcmin-com's search-index.json (same-machine local read; no
    # network), filters to City of Fredericksburg jurisdiction, and emits
    # a compact `scorecard_links` dict keyed by surname (lowercase) AND
    # by full name (lowercase). City page JS uses this to:
    #   - wrap council-member name occurrences with <a> links to their
    #     full scorecard profile at usmcmin.com/candidates/<state>/<slug>.html
    #   - render the per-member score badge next to their name everywhere
    #
    # The publisher also produces a `scorecard_by_role` list keyed by
    # office (Mayor / Vice-Mayor / City Council Ward N / etc.) for the
    # "Live Council" UI that wants to show members in office order with
    # their score, grade, and party.
    scorecard_links: dict[str, dict] = {}
    scorecard_by_role: list[dict] = []
    if SCORECARD_INDEX.exists():
        try:
            idx = json.loads(SCORECARD_INDEX.read_text())
            for r in idx.get('rows', []):
                if (r.get('j') or '').lower() != 'city of fredericksburg':
                    continue
                slug = r.get('s', '')
                state = r.get('st', 'va').lower()
                profile_url = f'https://usmcmin.com/candidates/{state}/{slug}.html'
                name = r.get('n', '')
                # Surname = last whitespace-separated token, stripped of
                # Jr./Sr./III/punctuation. Handles "Charlie Frye Jr." →
                # "Frye" not "Jr.".
                parts = name.split()
                if parts:
                    last = parts[-1].rstrip('.,').strip()
                    if last.lower() in ('jr', 'sr', 'ii', 'iii', 'iv') and len(parts) >= 2:
                        last = parts[-2].rstrip('.,').strip()
                else:
                    last = name
                rec = {
                    'slug': slug,
                    'profile_url': profile_url,
                    'name': name,
                    'office': r.get('o', ''),
                    'party': r.get('p', ''),
                    'tier': r.get('tr', ''),
                    'status': r.get('sts', ''),
                    'pct_of_max': r.get('pct', 0),
                    'letter_grade': r.get('lg', ''),
                    'total_score': r.get('ts', 0),
                    'max_possible': r.get('mp', 0),
                    'answered': r.get('ans', 0),
                    'na_count': r.get('na', 0),
                    'god_first': r.get('gf', 0),
                    'america_first': r.get('af', 0),
                }
                # Two keys for fast lookup from the JS render
                scorecard_links[last.lower()] = rec
                scorecard_links[name.lower()] = rec
                scorecard_by_role.append(rec)
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f'WARN: failed to load scorecard cross-references: {e}')
    out['scorecard_links'] = scorecard_links
    out['scorecard_by_role'] = scorecard_by_role

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + '\n')
    print(f'Wrote {OUT.relative_to(REPO)} — {len(council)} council members, '
          f'{len(out["meetings"])} meetings, next: {next_meeting["title"]} {next_meeting["date"]}, '
          f'{len(next_meeting["items"])} agenda items, '
          f'{minutes_count} matched + {injected_count} historical-injected meeting(s) with vote outcomes, '
          f'{len(scorecard_by_role)} cross-linked scorecard profiles')


if __name__ == '__main__':
    main()
