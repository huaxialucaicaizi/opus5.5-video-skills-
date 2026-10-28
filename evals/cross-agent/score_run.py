#!/usr/bin/env python3
"""score_run.py — score one agent run on one task, using the HARNESS copy of every validator.

    python3 evals/cross-agent/score_run.py --task E1 --workspace <ws> [--json out.json] [--rerender]

The scorer never trusts files the agent wrote about itself: it re-runs layout capture and determinism
against the workspace's code, probes the workspace's MP4 directly, and checks that validators, schemas
and the default style were not modified (integrity gate).

Score (0–100):
  build/determinism profiles: spec 20 · layout 15 · video 20 · determinism 15 · audio 5 · task-specific 25
  repair: spec 70 · intent preserved 30      footage: technical 40 · requirements 60      review: defect recall 70 · artefacts 30
  Any P0 failure caps the total at 40. Integrity violation -> 0.
"""
import argparse, hashlib, json, os, re, subprocess, sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HARNESS / 'scripts/validate'))
TASKS = {t['id']: t for t in json.loads((Path(__file__).parent / 'tasks.json').read_text())['tasks']}
PROTECTED = ['scripts/validate/common.py', 'scripts/validate/validate_spec.py', 'scripts/validate/layout_check.py', 'scripts/validate/probe_video.py',
             'scripts/validate/qa_report.py', 'scripts/validate/check_determinism.mjs', 'scripts/render/render.mjs', 'scripts/render/lib/browser.mjs',
             'spec/video-task.schema.json', 'templates/storyboard/storyboard.schema.json', 'templates/visual-style/style.default.json']
BASE_COMPONENTS = {'kinetic-title', 'token-split', 'prob-bars', 'append-loop', 'takeaway'}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).exists() else None

def integrity(ws):
    bad = [f for f in PROTECTED if sha(ws / f) != sha(HARNESS / f)]
    return {'ok': not bad, 'modified': bad, 'engine_modified': sha(ws / 'components/html-canvas/engine.js') != sha(HARNESS / 'components/html-canvas/engine.js')}

def run(cmd, env=None, cwd=None, timeout=900):
    p = subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, **(env or {})}, cwd=cwd, timeout=timeout)
    return p.returncode, p.stdout + p.stderr

def frac(checks, levels=('P0', 'P1', 'P2')):
    c = [x for x in checks if x['level'] in levels and x['status'] != 'skip']
    return (sum(x['status'] == 'pass' for x in c) / len(c)) if c else 0.0

def text_blob(*paths):
    out = []
    for p in paths:
        p = Path(p)
        if p.is_file(): out.append(p.read_text(errors='ignore'))
    return '\n'.join(out)

def kw_cover(blob, groups):
    hit = [any(k.lower() in blob.lower() for k in g) for g in groups]
    return sum(hit) / len(groups) if groups else 1.0, hit

def score_build(task, ws, proj, rerender):
    env = {'AVS_WORKSPACE': str(ws)}  # main() already exported it before importing validators
    import validate_spec, layout_check, probe_video
    res = {'components': {}}
    if not (proj / 'storyboard.json').exists():
        return {'total': 0, 'reason': 'no storyboard.json', 'components': {}}
    spec = validate_spec.run(proj)
    sb = json.loads((proj / 'storyboard.json').read_text())
    # Re-capture layout + determinism from the workspace code with the harness renderer.
    rel = proj.relative_to(ws)
    lay_out = proj / 'out' / '_scorer'; lay_out.mkdir(parents=True, exist_ok=True)
    rc_l, log_l = run(['node', str(HARNESS / 'scripts/render/render.mjs'), f'--project={rel}', '--layout', f'--out={lay_out}'], env)
    layout = layout_check.run(proj, lay_out / 'layout.json') if rc_l == 0 else [{'id': 'V0.render', 'level': 'P0', 'status': 'fail', 'title': 'workspace renders', 'detail': log_l[-400:]}]
    rc_d, log_d = run(['node', str(HARNESS / 'scripts/validate/check_determinism.mjs'), f'--project={rel}', f'--out={lay_out / "determinism.json"}'], env)
    det = json.loads((lay_out / 'determinism.json').read_text()) if (lay_out / 'determinism.json').exists() else {'status': 'fail', 'detail': log_d[-400:]}
    mp4 = proj / 'out' / f"{sb['task_id']}.mp4"
    if not mp4.exists():
        cands = sorted((proj / 'out').glob('*.mp4')) if (proj / 'out').exists() else []
        mp4 = cands[0] if cands else mp4
    video, meta = probe_video.run(mp4, proj) if mp4.exists() else ([{'id': 'T0.exists', 'level': 'P0', 'status': 'fail', 'title': 'mp4 exists', 'detail': str(mp4)}], {})
    audio = [c for c in video if c['id'].startswith('A1')]
    vtech = [c for c in video if not c['id'].startswith('A1')]
    c = res['components']
    if task['profile'] == 'determinism':
        f = ws / task['expect']['component_file']; src = f.read_text() if f.exists() else ''
        pats = [q for q in ['Math.random', 'Date.now', 'performance.now', 'setTimeout', 'setInterval'] if q in src]
        c['determinism'] = 40 if det.get('status') == 'pass' else 0
        c['no_forbidden_patterns'] = 0 if pats or not src else 15
        c['video'] = round(20 * frac(vtech), 2)
        c['qa_report'] = 5 if (proj / 'out' / 'qa_report.json').exists() else 0
        c['layout'] = round(10 * frac(layout), 2); c['spec'] = round(10 * frac(spec), 2)
        res['forbidden_patterns'] = pats
        checks = spec + layout + vtech + [{'id': 'T4.determinism', 'level': 'P0', 'status': det.get('status', 'fail'), 'title': 'determinism', 'detail': ''}]
        res['p0_fail'] = [x['id'] for x in checks if x['status'] == 'fail' and x['level'] == 'P0']
        res['fail'] = [f"{x['id']}: {str(x.get('detail', ''))[:120]}" for x in checks if x['status'] == 'fail']
        return res
    c['spec'] = round(20 * frac(spec), 2)
    c['layout'] = round(15 * frac(layout), 2)
    c['video'] = round(20 * frac(vtech), 2)
    c['determinism'] = 15 if det.get('status') == 'pass' else 0
    c['audio'] = round(5 * frac(audio), 2) if audio else 0
    # task-specific (25): format match 5, keyword coverage 10, review evidence 5, (new component | qa report) 5
    exp = task['expect']; ts = 0
    if sb.get('width') == exp.get('width') and sb.get('height') == exp.get('height') and sb.get('fps') == exp.get('fps') and abs(sb.get('duration_s', 0) - exp.get('duration_s', -1)) < 1e-6: ts += 5
    blob = json.dumps(sb, ensure_ascii=False)
    cov, hits = kw_cover(blob, exp.get('keywords_any', [])); ts += 10 * cov
    rv = proj / 'review.json'
    rv_ok = rv.exists() and len(json.loads(rv.read_text()).get('checks', [])) >= 4
    ts += 5 if rv_ok else 0
    if exp.get('new_component'):
        used = {s['component'] for s in sb['scenes']}
        from common import registered_components
        reg = registered_components() or set()
        new = (used & reg) - BASE_COMPONENTS
        ts += 5 if new else 0; res['new_components'] = sorted(new)
    else:
        ts += 5 if (proj / 'out' / 'qa_report.json').exists() else 0
    c['task'] = round(ts, 2); res['keyword_hits'] = hits; res['review_present'] = rv_ok
    checks = spec + layout + vtech + audio + [{'id': 'T4.determinism', 'level': 'P0', 'status': det.get('status', 'fail'), 'title': 'determinism', 'detail': det.get('detail', '')}]
    res['p0_fail'] = [x['id'] for x in checks if x['status'] == 'fail' and x['level'] == 'P0']
    res['fail'] = [f"{x['id']}: {str(x.get('detail', ''))[:120]}" for x in checks if x['status'] == 'fail']
    res['video_meta'] = meta
    return res

def score_repair(task, ws, proj):
    import validate_spec
    spec = validate_spec.run(proj)
    sb = json.loads((proj / 'storyboard.json').read_text())
    exp = task['expect']
    planted = ['S1.contiguous', 'S2.reads', 'S3.reading', 'S5.transitions', 'S6.components', 'L1.licences']
    st = {x['id']: x['status'] for x in spec}
    fixed = sum(st.get(i) == 'pass' for i in planted) / len(planted)
    ids_ok = [s['id'] for s in sorted(sb['scenes'], key=lambda s: s['start'])] == exp['scene_ids']
    dur_ok = abs(sb['duration_s'] - exp['duration_s']) < 1e-6 and sb['width'] == 1080 and sb['height'] == 1920
    # intent: each scene keeps its component family and its key on-screen text
    ref = json.loads((HARNESS / 'examples/ai-explainer-15s/storyboard.json').read_text())
    rmap = {s['id']: s for s in ref['scenes']}
    kept = sum(1 for s in sb['scenes'] if s['id'] in rmap and rmap[s['id']]['on_screen_text'][0]['text'] in json.dumps(s, ensure_ascii=False))
    intent = ((10 if ids_ok else 0) + (10 if dur_ok else 0) + 10 * kept / len(exp['scene_ids'])) * fixed  # no credit for doing nothing
    fails = [f"{x['id']}: {x['detail'][:120]}" for x in spec if x['status'] == 'fail']
    return {'components': {'planted_fixed': round(70 * fixed, 2), 'intent': round(intent, 2)}, 'planted': {i: st.get(i) for i in planted},
            'p0_fail': [x['id'] for x in spec if x['status'] == 'fail' and x['level'] == 'P0'], 'fail': fails}

def score_footage(task, ws, proj):
    import probe_video
    sys.path.insert(0, str(HARNESS / 'scripts/render')); import footage
    exp = task['expect']; out = ws / exp['output']
    if not out.exists(): return {'components': {'technical': 0, 'requirements': 0}, 'p0_fail': ['T0.exists'], 'fail': [f'missing {out}']}
    video, meta = probe_video.run(out)
    tech = 40 * frac([c for c in video if not c['id'].startswith('A1')])
    p = footage.probe(out); src = footage.probe(ws / exp['duration_from'])
    req = 0; notes = []
    if abs(p['duration'] - src['duration']) <= 1 / 25 + 0.05: req += 15
    else: notes.append(f"duration {p['duration']} vs talk {src['duration']}")
    if p['video'] and p['video']['width'] == exp['width'] and p['video']['height'] == exp['height']: req += 10
    else: notes.append('wrong frame size')
    if p['audio']: req += 10
    else: notes.append('no audio')
    if p['subtitles'] >= 1: req += 15
    else: notes.append('no subtitle track')
    inputs_ok = all(sha(ws / 'projects/e6-pip/inputs' / f) == sha(Path(os.environ.get('AVS_FIXTURE_REF', '')) / f) for f in ['broll.mp4', 'talk.mp4', 'subs.srt']) if os.environ.get('AVS_FIXTURE_REF') else True
    req += 10 if inputs_ok else 0
    if not inputs_ok: notes.append('inputs modified')
    return {'components': {'technical': round(tech, 2), 'requirements': req}, 'p0_fail': [] if req >= 35 else ['requirements'], 'fail': notes, 'video_meta': meta}

def score_review(task, ws, proj):
    blob = text_blob(proj / 'review.json', proj / 'FIXES.md', proj / 'out/qa_report.md')
    found = {d: any(k.lower() in blob.lower() for k in kws) for d, kws in task['expect']['defects'].items()}
    recall = sum(found.values()) / len(found)
    arte = (10 if (proj / 'review.json').exists() else 0) + (10 if (proj / 'FIXES.md').exists() else 0) + (10 if (proj / 'out/qa_report.md').exists() else 0)
    untouched = sha(proj / 'storyboard.json') is not None
    return {'components': {'recall': round(70 * recall, 2), 'artefacts': arte}, 'defects_found': found, 'p0_fail': [], 'fail': [d for d, v in found.items() if not v],
            'note': 'keyword-based recall: a reviewer can mention a keyword without diagnosing the defect; spot-check FIXES.md by hand'}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--task', required=True); ap.add_argument('--workspace', required=True); ap.add_argument('--json'); ap.add_argument('--rerender', action='store_true')
    a = ap.parse_args()
    task = TASKS[a.task]; ws = Path(a.workspace).resolve(); proj = ws / task['project']
    os.environ['AVS_WORKSPACE'] = str(ws)   # before any validator import: they resolve components from here
    integ = integrity(ws)
    if not integ['ok']:
        res = {'components': {}, 'total': 0, 'reason': 'integrity violation', 'p0_fail': ['INTEGRITY'], 'fail': integ['modified']}
    else:
        prof = task['profile']
        res = (score_build(task, ws, proj, a.rerender) if prof in ('build', 'determinism') else
               score_repair(task, ws, proj) if prof == 'repair' else
               score_footage(task, ws, proj) if prof == 'footage' else score_review(task, ws, proj))
        raw = sum(res['components'].values())
        res['total'] = round(min(raw, 40) if res.get('p0_fail') else raw, 2)
    res.update({'task': a.task, 'integrity': integ, 'profile': task['profile']})
    out = json.dumps(res, ensure_ascii=False, indent=2)
    if a.json: Path(a.json).write_text(out)
    print(out)

if __name__ == '__main__':
    main()
