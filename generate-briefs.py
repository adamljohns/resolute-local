#!/usr/bin/env python3
"""
generate-briefs.py — Phase 2 engine: auto-generate plain-English citizen briefs
from a meeting agenda using the local LLM (Hermes/Qwen on :1235).

For each upcoming meeting that lacks a brief in briefs/fredericksburg.json, sends
the agenda to the LLM and asks for {summary, why, how}. Merges the result back
into briefs/fredericksburg.json (never overwrites a manual/existing brief unless
--force). Then re-run publish-fredericksburg.py to push to the live site.

Robust: short timeout, graceful skip if the LLM is down, strict JSON extraction.

Usage:
    python3 generate-briefs.py           # fill missing briefs for upcoming meetings
    python3 generate-briefs.py --force   # regenerate even if a brief exists
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).parent
DATA = REPO / 'data' / 'fredericksburg.json'
BRIEFS = REPO / 'briefs' / 'fredericksburg.json'
LLM_URL = 'http://127.0.0.1:1235/v1/chat/completions'
MODEL = 'qwen3.6-35b-a3b'

SYSTEM = (
    "You write short, factual, non-partisan civic briefs for Christian citizens who want to "
    "engage their local city council. You are accurate and concrete, never sensational. "
    "You explain plainly what a meeting agenda actually decides and how an ordinary resident "
    "can weigh in. Output ONLY valid JSON."
)

USER_TMPL = (
    "City: Fredericksburg, VA. Meeting: {title} on {date} at {time}, {location}.\n\n"
    "Raw agenda lines:\n{agenda}\n\n"
    "Return ONLY a JSON object with exactly these keys:\n"
    '{{"summary": "2-3 sentences: what this meeting is actually deciding, in plain English",\n'
    '  "why": "2-3 sentences: why it matters to local families (tax base, zoning, schools, '
    'public safety, business mix) — values-aware but factual, no partisan labels",\n'
    '  "how": "2-3 sentences: concretely how a resident can weigh in — attend, public comment, '
    'email council, deadlines. Use the meeting time/location given."}}\n'
    "No preamble, no markdown, just the JSON."
)


def call_llm(title, date, time, location, agenda_lines, timeout=90):
    prompt = USER_TMPL.format(
        title=title or 'City Council Session', date=date or 'TBD',
        time=time or 'TBD', location=location or 'Council Chambers',
        agenda='\n'.join('- ' + l for l in agenda_lines[:40]) or '(no detailed agenda yet)')
    body = json.dumps({
        'model': MODEL,
        'messages': [{'role': 'system', 'content': SYSTEM},
                     {'role': 'user', 'content': prompt}],
        'temperature': 0.3, 'max_tokens': 600,
    }).encode()
    req = urllib.request.Request(LLM_URL, data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read())
    text = resp['choices'][0]['message']['content']
    # Strip thinking tags / markdown fences; extract the first {...} JSON object
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.S)
    text = text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
    m = re.search(r'\{.*\}', text, re.S)
    if not m:
        raise ValueError('no JSON object in LLM output')
    obj = json.loads(m.group(0))
    return {k: str(obj.get(k, '')).strip() for k in ('summary', 'why', 'how')}


def main():
    force = '--force' in sys.argv
    if not DATA.exists():
        raise SystemExit('run publish-fredericksburg.py first (no data/fredericksburg.json)')
    data = json.loads(DATA.read_text())
    briefs = {}
    if BRIEFS.exists():
        briefs = json.loads(BRIEFS.read_text())

    # Candidate meetings to brief: the parsed next_meeting (has agenda lines).
    nm = data.get('next_meeting', {})
    targets = []
    if nm.get('date'):
        targets.append((nm['date'], nm))

    generated = 0
    for date, m in targets:
        existing = briefs.get(date)
        if existing and not force and existing.get('summary'):
            print(f'  {date}: brief exists — skip (use --force to regenerate)')
            continue
        # Don't clobber a hand-authored ('manual') brief unless forced
        if existing and existing.get('source') == 'manual' and not force:
            print(f'  {date}: manual brief — preserved')
            continue
        agenda = m.get('items') or m.get('raw_lines') or []
        try:
            brief = call_llm(m.get('title'), date, m.get('time'), m.get('location'), agenda)
        except Exception as e:
            print(f'  {date}: LLM generation skipped ({type(e).__name__}: {e})')
            continue
        brief['source'] = 'auto-llm'
        brief['model'] = MODEL
        briefs[date] = brief
        generated += 1
        print(f'  {date}: brief generated ({len(brief["summary"])} char summary)')

    if generated:
        BRIEFS.write_text(json.dumps(briefs, indent=2) + '\n')
        print(f'Wrote {generated} brief(s) to {BRIEFS.relative_to(REPO)}')
    else:
        print('No briefs generated.')


if __name__ == '__main__':
    main()
