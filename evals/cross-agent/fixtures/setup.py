#!/usr/bin/env python3
"""setup.py — create a task's starting state inside an agent workspace.

    python3 evals/cross-agent/fixtures/setup.py <task_id> <workspace_dir>

E1–E3 start empty. E4 plants spec defects, E5 a non-deterministic component, E6 generated clips,
E7 a rendered video with four planted defects (D1–D4, see tasks.json).
"""
import json, shutil, subprocess, sys
from pathlib import Path

def sh(*a, cwd=None):
    subprocess.run(a, check=True, cwd=cwd, stdout=subprocess.DEVNULL)

def example(ws):
    return json.loads((ws / 'examples/ai-explainer-15s/storyboard.json').read_text()), json.loads((ws / 'examples/ai-explainer-15s/task.json').read_text())

def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

def e4(ws):
    sb, task = example(ws); d = ws / 'projects/e4-broken'
    sb['task_id'] = task['id'] = 'e4-broken'
    sc = {s['id']: s for s in sb['scenes']}
    sc['s3_probs']['start'] = 5.8                                   # gap after s2 (S1.contiguous)
    sc['s2_tokens']['reads'][1]['end'] = sc['s2_tokens']['reads'][1]['start'] + 0.3   # read too short (S2)
    sc['s4_loop']['on_screen_text'][-1].update(start=12.0, end=12.5)  # "一遍又一遍" held 0.5 s (S3)
    sc['s3_probs']['component'] = 'fancy-bars'                      # unregistered component (S6)
    sc['s5_takeaway']['transition_out'] = {'type': 'none'}          # video stops hard (S5)
    task['assets'] = [{'id': 'bgm', 'path': 'assets/bgm.mp3', 'author': 'unknown uploader', 'license': 'unknown', 'commercial_use': False}]
    task['audio']['music'] = {'source': 'file', 'asset_id': 'bgm', 'path': 'assets/bgm.mp3'}   # L1 (unknown licence, missing file)
    write(d / 'storyboard.json', sb); write(d / 'task.json', task)

SPARKLE = r"""// sparkle-title: twinkling stars + title rise-in.  (fixture for eval E5: intentionally NON-deterministic)
import { ease, seg, TAU } from '../engine.js';
const stars = [];
export default function sparkleTitle(f, p) {
  const { ctx, u, pal, W, H, lt } = f;
  if (stars.length === 0) for (let i = 0; i < 60; i++) stars.push({ x: Math.random() * W, y: Math.random() * H * 0.8, r: 2 + Math.random() * 4 });
  const now = Date.now() / 1000;
  for (const s of stars) {
    s.y -= 0.4 * u;                                   // drifts a bit every frame (state carried between frames)
    const tw = 0.5 + 0.5 * Math.sin(now * 3 + s.x);
    ctx.fillStyle = `rgba(255,200,140,${0.25 + 0.6 * tw})`;
    ctx.beginPath(); ctx.arc(s.x, s.y, s.r * u * tw, 0, TAU); ctx.fill();
  }
  const k = ease.easeOutCubic(seg(lt, 0.3, 1.0));
  f.text(p.title, W / 2, H * 0.45 + (1 - k) * 60 * u, { role: 'title', align: 'center', alpha: k, maxWidth: f.safe.w, fit: true, id: 'sp:title' });
  if (p.sub) f.text(p.sub, W / 2, H * 0.45 + 140 * u, { role: 'body', align: 'center', color: pal.text_muted, alpha: seg(lt, 0.9, 1.4), id: 'sp:sub', maxWidth: f.safe.w });
}
"""

def e5(ws):
    (ws / 'components/html-canvas/scenes/sparkle-title.js').write_text(SPARKLE)
    idx = ws / 'components/html-canvas/scenes/index.js'; s = idx.read_text()
    s = s.replace("import takeaway from './takeaway.js';", "import takeaway from './takeaway.js';\nimport sparkleTitle from './sparkle-title.js';")
    s = s.replace("  'takeaway': takeaway,", "  'takeaway': takeaway,\n  'sparkle-title': sparkleTitle,")
    idx.write_text(s)
    d = ws / 'projects/e5-sparkle'
    sb = {'schema_version': '1.0', 'task_id': 'e5-sparkle', 'duration_s': 6, 'fps': 30, 'width': 1080, 'height': 1920, 'bpm': 120,
          'style': '../../templates/visual-style/style.default.json', 'logline': '星点闪烁中，标题升起：AI 小科普开场。',
          'scenes': [{'id': 's1', 'start': 0, 'end': 6, 'purpose': 'opening', 'event': '标题升起、副标题出现，星点持续闪烁', 'visual': '星点 + 大标题',
                      'component': 'sparkle-title', 'params': {'title': 'AI 小科普', 'sub': '今天聊聊大模型'},
                      'on_screen_text': [{'text': 'AI 小科普', 'start': 0.3, 'end': 6, 'role': 'title'}, {'text': '今天聊聊大模型', 'start': 0.9, 'end': 6, 'role': 'body'}],
                      'reads': [{'start': 0.3, 'end': 1.4, 'what': '这是 AI 科普'}, {'start': 1.4, 'end': 5.8, 'what': '今天讲大模型'}],
                      'transition_in': {'type': 'fade', 'duration': 0.4}, 'transition_out': {'type': 'fade', 'duration': 0.4}}]}
    task = {'schema_version': '1.0', 'id': 'e5-sparkle', 'title': 'AI 小科普开场', 'goal': '看完知道这是 AI 科普系列的开场。', 'audience': '短视频用户',
            'language': 'zh-CN', 'duration_s': 6, 'format': {'width': 1080, 'height': 1920, 'fps': 30}, 'renderer': 'html-canvas',
            'style': '../../templates/visual-style/style.default.json', 'audio': {'music': {'source': 'synth', 'bpm': 120}, 'target_lufs': -14},
            'assets': [], 'deliverables': ['mp4', 'qa_report']}
    write(d / 'storyboard.json', sb); write(d / 'task.json', task)

def e6(ws):
    d = ws / 'projects/e6-pip/inputs'; d.mkdir(parents=True, exist_ok=True)
    sh('ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=1080x1920:rate=30:duration=8', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(d / 'broll.mp4'))
    sh('ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'smptebars=size=1280x720:rate=25:duration=6.4', '-f', 'lavfi', '-i', 'sine=frequency=220:duration=6.4',
       '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', str(d / 'talk.mp4'))
    (d / 'subs.srt').write_text('1\n00:00:00,400 --> 00:00:02,600\n大家好，今天聊聊大模型\n\n2\n00:00:03,000 --> 00:00:06,000\n它每次只猜下一个词\n', encoding='utf-8')
    (d / 'LICENSES.txt').write_text('All three inputs were generated by evals/cross-agent/fixtures/setup.py (ffmpeg lavfi test sources). No third-party licence.\n')

def e7(ws):
    sb, task = example(ws); d = ws / 'projects/e7-review'
    sb['task_id'] = task['id'] = 'e7-review'
    sc = {s['id']: s for s in sb['scenes']}
    sc['s3_probs']['params']['options'] = [{'label': '好', 'p': 0.62}, {'label': '热', 'p': 0.30}, {'label': '冷', 'p': 0.20}, {'label': '差', 'p': 0.09}]  # D1: sums to 121 %
    sc['s3_probs']['on_screen_text'][3]['text'] = '好 62% 热 30% 冷 20% 差 9%'
    sc['s3_probs']['params']['note'] = '概率仅为示意：真实模型会给词表里成千上万个候选词都打分，这里只画出了排名最靠前的四个候选词'  # D3: wraps into the bottom UI zone
    sc['s3_probs']['on_screen_text'][4]['text'] = sc['s3_probs']['params']['note']
    sc['s4_loop']['on_screen_text'][-1].update(start=12.0, end=12.5)  # D4: held 0.5 s
    task['audio']['target_lufs'] = -24                                  # D2: rendered quiet; reviewer should compare to platform norm (-14)
    task['notes'] = '平台要求：响度 -14 LUFS。'
    write(d / 'storyboard.json', sb); write(d / 'task.json', task)
    # render it as-is (the defects are the point)
    sh('python3', 'scripts/render/synth_music.py', str(d), '--lufs', '-24', cwd=ws)
    sh('node', 'scripts/render/render.mjs', f'--project={d.relative_to(ws)}', '--mp4', f'--audio={d}/out/audio.wav', cwd=ws)
    shutil.rmtree(d / 'out/frames', ignore_errors=True)
    task['audio']['target_lufs'] = -14   # the spec the video should have met
    write(d / 'task.json', task)

def main():
    tid, ws = sys.argv[1], Path(sys.argv[2]).resolve()
    {'E1': lambda w: None, 'E2': lambda w: None, 'E3': lambda w: None, 'E4': e4, 'E5': e5, 'E6': e6, 'E7': e7}[tid](ws)
    print(f'fixture {tid} ready in {ws}')

if __name__ == '__main__':
    main()
