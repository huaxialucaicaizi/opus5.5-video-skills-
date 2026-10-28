"""Shared helpers for validators. Every check yields a dict:
    {id, level: P0|P1|P2, status: pass|fail|warn|skip, title, detail}
A P0 'fail' blocks delivery. 'warn' is used for P2 failures and soft findings.
"""
import json, re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

def check(cid, level, ok, title, detail='', soft=False):
    status = 'pass' if ok else ('warn' if soft or level == 'P2' else 'fail')
    return {'id': cid, 'level': level, 'status': status, 'title': title, 'detail': detail}

def skip(cid, level, title, why):
    return {'id': cid, 'level': level, 'status': 'skip', 'title': title, 'detail': why}

def load_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def load_project(project):
    proj = Path(project).resolve()
    sb = load_json(proj / 'storyboard.json')
    task = load_json(proj / 'task.json') if (proj / 'task.json').exists() else None
    style_rel = sb.get('style') or (task or {}).get('style') or '../../templates/visual-style/style.default.json'
    style_path = (proj / style_rel).resolve()
    style = load_json(style_path)
    return proj, task, sb, style

CJK_RE = re.compile(r'[㐀-鿿豈-﫿]')
WORD_RE = re.compile(r'[A-Za-z0-9]+(?:[\'’-][A-Za-z0-9]+)*')

def reading_time(text, style):
    """Seconds a viewer needs for this string: CJK chars at zh_chars_per_s + latin words at en_words_per_s."""
    r = style['readability']
    zh = len(CJK_RE.findall(text))
    en = len(WORD_RE.findall(text))
    return max(r['min_text_hold_s'], zh / r['zh_chars_per_s'] + en / r['en_words_per_s'])

def registered_components():
    idx = REPO / 'components/html-canvas/scenes/index.js'
    if not idx.exists(): return None
    return set(re.findall(r"^\s*'([a-z0-9-]+)'\s*:", idx.read_text(), re.M))

def summarize(checks):
    fails = [c for c in checks if c['status'] == 'fail']
    p0 = [c for c in fails if c['level'] == 'P0']
    warns = [c for c in checks if c['status'] == 'warn']
    return {'p0_fail': len(p0), 'fail': len(fails), 'warn': len(warns), 'pass': sum(c['status'] == 'pass' for c in checks),
            'skip': sum(c['status'] == 'skip' for c in checks)}

def print_checks(checks, title):
    icon = {'pass': '✓', 'fail': '✗', 'warn': '!', 'skip': '-'}
    print(f'== {title}')
    for c in checks:
        print(f"  {icon[c['status']]} [{c['level']}] {c['id']} {c['title']}" + (f" — {c['detail']}" if c['detail'] and c['status'] != 'pass' else ''))
    s = summarize(checks)
    print(f"  => pass {s['pass']}  fail {s['fail']} (P0 {s['p0_fail']})  warn {s['warn']}  skip {s['skip']}")
    return s
