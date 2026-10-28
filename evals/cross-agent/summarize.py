#!/usr/bin/env python3
"""summarize.py — collect runs/*/run.json into results/summary.md and results/runs.csv."""
import csv, json, sys
from collections import defaultdict
from pathlib import Path

root = Path(__file__).parent
runs = [json.loads(p.read_text()) | {'dir': p.parent.name} for p in sorted((root / 'runs').glob('*/run.json'))]
(root / 'results').mkdir(exist_ok=True)
keys = ['dir', 'agent', 'task', 'score', 'wall_s', 'total_cost_usd', 'num_turns', 'exit_code', 'p0_fail', 'toolkit_commit']
with open(root / 'results/runs.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore'); w.writeheader()
    for r in runs: w.writerow({**r, 'p0_fail': ';'.join(r.get('p0_fail') or [])})
tasks = sorted({r['task'] for r in runs}); agents = sorted({r['agent'] for r in runs})
cell = defaultdict(list)
for r in runs: cell[(r['agent'], r['task'])].append(r)
lines = ['# Cross-agent results', '', 'Mean score (n runs). Full rows in `runs.csv`.', '', '| agent | ' + ' | '.join(tasks) + ' | mean |', '|---|' + '---|' * (len(tasks) + 1)]
for a in agents:
    row, allv = [], []
    for t in tasks:
        v = [x['score'] or 0 for x in cell[(a, t)]]
        allv += v
        row.append(f"{sum(v) / len(v):.1f} ({len(v)})" if v else '—')
    lines.append(f"| {a} | " + ' | '.join(row) + f" | {sum(allv) / len(allv):.1f} |" if allv else '')
(root / 'results/summary.md').write_text('\n'.join(lines) + '\n')
print('\n'.join(lines))
