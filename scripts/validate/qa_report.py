#!/usr/bin/env python3
"""qa_report.py — merge every automatic check plus the reviewer's manual verdicts into one report.

    python3 scripts/validate/qa_report.py <project_dir> [--video <mp4>] [--agent <name>]

Inputs  (all under <project>/out unless noted):
    <task_id>.mp4, layout.json, determinism.json, keyframes/index.json, contact_sheet.jpg
    <project>/review.json   manual checks written by video-quality-reviewer: {"reviewer": "...", "checks": [{id, status, note, evidence}]}
Outputs:
    out/qa_report.json, out/qa_report.md
Verdict:
    FAIL          any P0 fail (auto or manual)
    NEEDS_REVIEW  no P0 fail, but manual P0/P1 checks still pending
    PASS_WITH_WARNINGS / PASS
Exit code: 1 on FAIL, 0 otherwise.
"""
import argparse, datetime, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import load_project, load_json, summarize, skip
import validate_spec, layout_check, probe_video

MANUAL = [
    ('M1', 'P0', '信息正确：无事实错误，示意数据已标注'),
    ('M2', 'P1', '每镜有事件：首末帧有可见变化且与 event 一致'),
    ('M3', 'P1', '焦点清晰：关键帧里一眼看出该看哪'),
    ('M4', 'P1', '风格一致：无禁用效果，配色字体一致'),
    ('M5', 'P2', '首尾呼应：结尾回扣开头母题'),
]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('project'); ap.add_argument('--video'); ap.add_argument('--agent', default='unknown')
    a = ap.parse_args()
    proj, task, sb, style = load_project(a.project)
    out = proj / 'out'; out.mkdir(exist_ok=True)
    video = Path(a.video) if a.video else out / f"{sb['task_id']}.mp4"

    groups = {}
    groups['spec'] = validate_spec.run(proj)
    groups['layout'] = layout_check.run(proj)
    if video.exists():
        groups['video'], meta = probe_video.run(video, proj)
    else:
        groups['video'], meta = [{'id': 'T0.exists', 'level': 'P0', 'status': 'fail', 'title': 'video file exists', 'detail': str(video)}], {}
    det = out / 'determinism.json'
    groups['determinism'] = [ {k: v for k, v in load_json(det).items() if k != 'hashes'} ] if det.exists() else [skip('T4.determinism', 'P0', 'determinism', 'run check_determinism.mjs')]

    rv = load_json(proj / 'review.json') if (proj / 'review.json').exists() else {'reviewer': None, 'checks': []}
    given = {c['id']: c for c in rv.get('checks', [])}
    manual = []
    for cid, lvl, title in MANUAL:
        c = given.get(cid)
        if c: manual.append({'id': cid, 'level': lvl, 'status': c['status'], 'title': title, 'detail': c.get('note', ''), 'evidence': c.get('evidence', [])})
        else: manual.append({'id': cid, 'level': lvl, 'status': 'pending', 'title': title, 'detail': 'not reviewed'})
    groups['manual'] = manual

    allc = [c for g in groups.values() for c in g]
    auto = [c for k, g in groups.items() if k != 'manual' for c in g]
    p0_fail = [c for c in allc if c['status'] == 'fail' and c['level'] == 'P0']
    any_fail = [c for c in allc if c['status'] == 'fail']
    pending = [c for c in manual if c['status'] == 'pending' and c['level'] in ('P0', 'P1')]
    warns = [c for c in allc if c['status'] == 'warn' or (c['status'] == 'fail' and c['level'] != 'P0')]
    verdict = 'FAIL' if p0_fail else 'NEEDS_REVIEW' if pending else 'PASS_WITH_WARNINGS' if warns else 'PASS'
    # P1 auto failures also block a clean pass
    if verdict.startswith('PASS') and any_fail: verdict = 'PASS_WITH_WARNINGS'

    kf = load_json(out / 'keyframes' / 'index.json') if (out / 'keyframes' / 'index.json').exists() else []
    report = {
        'task_id': sb['task_id'], 'generated_at': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
        'agent': a.agent, 'reviewer': rv.get('reviewer'), 'verdict': verdict,
        'summary': {'auto': summarize(auto), 'manual_pending': len([c for c in manual if c['status'] == 'pending'])},
        'video': {'path': str(video.relative_to(proj)) if video.is_relative_to(proj) else str(video), **meta},
        'artifacts': {'contact_sheet': 'out/contact_sheet.jpg' if (out / 'contact_sheet.jpg').exists() else None,
                      'keyframes': [str(Path(k['file']).relative_to(proj)) if Path(k['file']).is_relative_to(proj) else k['file'] for k in kf]},
        'checks': groups,
    }
    (out / 'qa_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))

    icon = {'pass': '✅', 'fail': '❌', 'warn': '⚠️', 'skip': '➖', 'pending': '⏳'}
    md = [f"# QA 报告 · {sb['task_id']}", '',
          f"**结论：{verdict}**　·　生成时间 {report['generated_at']}　·　制作 Agent：{a.agent}　·　审片：{rv.get('reviewer') or '未审'}", '',
          '| 项 | 值 |', '|---|---|',
          f"| 文件 | `{report['video']['path']}` |",
          f"| 时长 / 分辨率 / 帧率 | {meta.get('duration', '—')} s / {meta.get('width')}×{meta.get('height')} / {meta.get('fps')} fps |",
          f"| 体积 / 码率 | {meta.get('size_bytes', 0) / 1e6:.2f} MB / {meta.get('bitrate', 0) / 1e3:.0f} kbps |",
          f"| 自动检查 | 通过 {report['summary']['auto']['pass']} · 失败 {report['summary']['auto']['fail']}（P0 {report['summary']['auto']['p0_fail']}） · 警告 {report['summary']['auto']['warn']} · 跳过 {report['summary']['auto']['skip']} |",
          f"| 人工检查待办 | {report['summary']['manual_pending']} |", '']
    names = {'spec': '分镜与规格', 'layout': '版式（渲染期文字框）', 'video': '成片技术参数', 'determinism': '确定性', 'manual': '人工 / 审片 Agent'}
    for k, g in groups.items():
        md += [f"## {names[k]}", '', '| 状态 | 级别 | ID | 检查 | 说明 |', '|---|---|---|---|---|']
        for c in g:
            md.append(f"| {icon.get(c['status'], c['status'])} | {c['level']} | {c['id']} | {c['title']} | {(str(c.get('detail', '')) if c['status'] != 'pass' or k == 'manual' else '').replace('|', '/').replace(chr(10), ' ')[:300]} |")
        md.append('')
    if report['artifacts']['contact_sheet']: md += ['## 联系表', '', '![contact sheet](contact_sheet.jpg)', '']
    if kf:
        md += ['## 关键帧', '', '| t (s) | 场景 | 文件 |', '|---|---|---|'] + [f"| {k['t']:.2f} | {k['scene']} | `{Path(k['file']).name}` |" for k in kf] + ['']
    (out / 'qa_report.md').write_text('\n'.join(md), encoding='utf-8')
    print(f"QA verdict: {verdict}  ->  {out / 'qa_report.md'}")
    return 1 if verdict == 'FAIL' else 0

if __name__ == '__main__':
    sys.exit(main())
