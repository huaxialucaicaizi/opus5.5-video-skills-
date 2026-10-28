#!/usr/bin/env python3
"""validate_spec.py — lint a project's task.json + storyboard.json before any rendering.

    python3 scripts/validate/validate_spec.py <project_dir> [--json out.json]

Checks (see spec/ACCEPTANCE_CHECKLIST.md): S1 structure, S2 reads, S3 reading speed, S4 beat alignment,
S5 transitions, S6 registered components, L1 asset licences. Exit code 1 if any P0/P1 check fails.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import REPO, check, skip, load_project, reading_time, registered_components, print_checks, summarize

try:
    import jsonschema
except ImportError:  # keep working without it, but say so
    jsonschema = None

def schema_errors(doc, schema_path):
    if jsonschema is None: return None
    schema = json.loads(Path(schema_path).read_text())
    v = jsonschema.Draft202012Validator(schema)
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in sorted(v.iter_errors(doc), key=lambda e: list(e.absolute_path))]

def run(project):
    proj, task, sb, style = load_project(project)
    out = []
    fps = sb['fps']; frame = 1 / fps; tol = frame + 1e-6
    r = style['readability']

    # ---- S1 schema + structure
    errs = schema_errors(sb, REPO / 'templates/storyboard/storyboard.schema.json')
    if errs is None: out.append(skip('S1.schema', 'P0', 'storyboard matches schema', 'jsonschema not installed'))
    else: out.append(check('S1.schema', 'P0', not errs, 'storyboard matches schema', '; '.join(errs[:6])))
    if task is not None:
        terrs = schema_errors(task, REPO / 'spec/video-task.schema.json')
        if terrs is not None: out.append(check('S1.task', 'P0', not terrs, 'task.json matches schema', '; '.join(terrs[:6])))
        mism = [k for k, a, b in [('duration_s', task['duration_s'], sb['duration_s']), ('fps', task['format']['fps'], sb['fps']),
                                  ('width', task['format']['width'], sb['width']), ('height', task['format']['height'], sb['height'])] if abs(a - b) > 1e-6]
        out.append(check('S1.match', 'P0', not mism, 'storyboard format matches task', f'mismatch: {mism}'))
    else:
        out.append(skip('S1.task', 'P0', 'task.json matches schema', 'no task.json'))

    scenes = sorted(sb['scenes'], key=lambda s: s['start'])
    gaps = []
    if abs(scenes[0]['start']) > tol: gaps.append(f"first scene starts at {scenes[0]['start']}")
    for a, b in zip(scenes, scenes[1:]):
        if abs(a['end'] - b['start']) > tol: gaps.append(f"{a['id']}→{b['id']}: {a['end']} vs {b['start']}")
    if abs(scenes[-1]['end'] - sb['duration_s']) > tol: gaps.append(f"last scene ends {scenes[-1]['end']} ≠ duration {sb['duration_s']}")
    bad_len = [f"{s['id']} ({s['end'] - s['start']:.2f}s)" for s in scenes if s['end'] - s['start'] < 1.0]
    out.append(check('S1.contiguous', 'P0', not gaps, 'scenes are contiguous and cover the duration', '; '.join(gaps)))
    out.append(check('S1.scene_len', 'P1', not bad_len, 'every scene ≥ 1.0 s', ', '.join(bad_len)))
    ids = [s['id'] for s in scenes]
    out.append(check('S1.ids', 'P0', len(ids) == len(set(ids)), 'scene ids unique', str(ids)))

    # ---- S2 reads
    probs = []
    for s in scenes:
        reads = sorted(s['reads'], key=lambda x: x['start'])
        for rd in reads:
            if rd['start'] < s['start'] - tol or rd['end'] > s['end'] + tol: probs.append(f"{s['id']}: read '{rd['what'][:14]}' outside scene")
            if rd['end'] - rd['start'] < r['min_read_s'] - 1e-6: probs.append(f"{s['id']}: read '{rd['what'][:14]}' only {rd['end'] - rd['start']:.2f}s")
        for a, b in zip(reads, reads[1:]):
            if b['start'] < a['end'] - tol: probs.append(f"{s['id']}: reads overlap ('{a['what'][:10]}' / '{b['what'][:10]}')")
    out.append(check('S2.reads', 'P1', not probs, f"reads inside scene, ≥{r['min_read_s']}s, non-overlapping", '; '.join(probs)))

    # ---- S3 reading speed
    slow = []
    for s in scenes:
        for tx in s.get('on_screen_text', []):
            need = reading_time(tx['text'], style); have = tx['end'] - tx['start']
            if tx['start'] < s['start'] - tol or tx['end'] > s['end'] + tol: slow.append(f"{s['id']}: '{tx['text'][:12]}' outside scene window")
            elif have + 1e-6 < need: slow.append(f"{s['id']}: '{tx['text'][:12]}' shown {have:.2f}s < needs {need:.2f}s")
    out.append(check('S3.reading', 'P1', not slow, 'every on-screen text is held long enough to read', '; '.join(slow)))

    # ---- S4 beat alignment
    if sb.get('bpm'):
        beat = 60 / sb['bpm']; off = sb.get('beat_offset_s', 0) or 0
        off_grid = []
        for s in scenes[1:]:
            d = ((s['start'] - off) / beat) % 1 * beat
            dist = min(d, beat - d)
            if dist > tol: off_grid.append(f"{s['id']} cut at {s['start']}s is {dist * 1000:.0f} ms off-beat")
        out.append(check('S4.beats', 'P2', not off_grid, 'scene cuts land on the beat grid', '; '.join(off_grid)))
    else:
        out.append(skip('S4.beats', 'P2', 'scene cuts land on the beat grid', 'no bpm'))

    # ---- S5 transitions
    missing = [s['id'] for s in scenes if s['transition_in']['type'] == 'none' and not s['transition_in'].get('note')]
    first_hard = scenes[0]['transition_in']['type'] in ('none', 'smash-cut', 'cut-on-action')
    last_out = scenes[-1].get('transition_out', {}).get('type')
    det = []
    if missing: det.append(f"no transition_in: {missing}")
    if first_hard: det.append('video starts on a hard frame')
    if last_out in (None, 'none'): det.append('video stops without transition_out')
    out.append(check('S5.transitions', 'P1', not det, 'every seam (incl. open/close) has a transition', '; '.join(det)))

    # ---- S6 components
    reg = registered_components()
    if reg is None: out.append(skip('S6.components', 'P0', 'components registered', 'scenes/index.js not found'))
    else:
        unk = sorted({s['component'] for s in scenes} - reg)
        out.append(check('S6.components', 'P0', not unk, 'all scene components are registered', f'unknown: {unk}; known: {sorted(reg)}'))

    # ---- L1 asset licences
    if task is not None:
        bad = []
        for a in task.get('assets', []):
            if not a.get('license') or a['license'].strip().lower() in ('unknown', '?', 'tbd'): bad.append(f"{a['id']}: licence unknown")
            if not a.get('author'): bad.append(f"{a['id']}: no author")
            if not (proj / a['path']).exists(): bad.append(f"{a['id']}: file missing ({a['path']})")
        mus = task.get('audio', {}).get('music', {})
        if mus.get('source') == 'file':
            aid = mus.get('asset_id')
            if not aid or aid not in {a['id'] for a in task.get('assets', [])}: bad.append('music source=file but asset_id not registered in assets[]')
        out.append(check('L1.licences', 'P0', not bad, 'every asset has author + known licence', '; '.join(bad)))
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('project'); ap.add_argument('--json')
    a = ap.parse_args()
    res = run(a.project)
    s = print_checks(res, f'spec: {a.project}')
    if a.json: Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=2))
    return 1 if any(c['status'] == 'fail' for c in res) else 0

if __name__ == '__main__':
    sys.exit(main())
