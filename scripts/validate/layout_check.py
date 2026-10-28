#!/usr/bin/env python3
"""layout_check.py — check text boxes the renderer actually drew (out/layout.json from render.mjs --layout).

    python3 scripts/validate/layout_check.py <project_dir> [--layout <file>]

V1 safe area, V2 minimum font size, V3 no overlapping text. Only "settled" samples are judged for V1/V3
(not inside a transition), and only boxes with effective alpha ≥ 0.5.
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import check, skip, load_project, load_json, print_checks

VIS = 0.5

def overlap(a, b, tol):
    ix = min(a['x'] + a['w'], b['x'] + b['w']) - max(a['x'], b['x'])
    iy = min(a['y'] + a['h'], b['y'] + b['h']) - max(a['y'], b['y'])
    return ix > tol and iy > tol

def run(project, layout_path=None):
    proj, task, sb, style = load_project(project)
    lp = Path(layout_path) if layout_path else proj / 'out' / 'layout.json'
    if not lp.exists():
        return [skip(i, l, t, f'{lp} missing: run render.mjs --layout') for i, l, t in
                [('V1.safe_area', 'P0', 'text inside safe area'), ('V2.min_px', 'P1', 'font size ≥ minimum'), ('V3.overlap', 'P1', 'no overlapping text')]]
    L = load_json(lp)
    W, H = L['width'], L['height']; u = W / style.get('reference_width', 1080)
    sa = style['layout']['safe_area']
    box = (sa['left'] * u, sa['top'] * u, W - sa['right'] * u, H - sa['bottom'] * u)
    min_px = style['typography']['min_px'] * u
    tol = 2 * u

    out_safe, small, ovl = {}, {}, {}
    settled = [s for s in L['samples'] if not s.get('transition')]
    for s in L['samples']:
        for b in s['boxes']:
            if b['alpha'] < VIS: continue
            if b['px'] + 0.5 < min_px: small.setdefault(b['id'], (s['t'], b['px']))
    for s in settled:
        vis = [b for b in s['boxes'] if b['alpha'] >= VIS]
        for b in vis:
            if b['x'] < box[0] - tol or b['y'] < box[1] - tol or b['x'] + b['w'] > box[2] + tol or b['y'] + b['h'] > box[3] + tol:
                out_safe.setdefault(b['id'], (s['t'], [round(b['x']), round(b['y']), round(b['x'] + b['w']), round(b['y'] + b['h'])]))
        for i, a in enumerate(vis):
            for b in vis[i + 1:]:
                if overlap(a, b, tol): ovl.setdefault(tuple(sorted((a['id'], b['id']))), s['t'])
    fmt = lambda d: '; '.join(f'{k} @t={v[0]} {v[1]}' for k, v in list(d.items())[:8])
    n = len(L['samples'])
    return [
        check('V1.safe_area', 'P0', not out_safe, f'text inside safe area ({len(settled)}/{n} settled samples)', f'safe box {[round(x) for x in box]}; ' + fmt(out_safe)),
        check('V2.min_px', 'P1', not small, f'font size ≥ {min_px:.0f}px', fmt(small)),
        check('V3.overlap', 'P1', not ovl, 'no overlapping text boxes', '; '.join(f'{a} × {b} @t={t}' for (a, b), t in list(ovl.items())[:8])),
    ]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('project'); ap.add_argument('--layout')
    a = ap.parse_args()
    res = run(a.project, a.layout)
    print_checks(res, f'layout: {a.project}')
    return 1 if any(c['status'] == 'fail' for c in res) else 0

if __name__ == '__main__':
    sys.exit(main())
