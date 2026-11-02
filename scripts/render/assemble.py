#!/usr/bin/env python3
"""assemble.py — cut a talking-head recording against B-roll from an edit list (EDL), with captions and music.

    python3 scripts/render/assemble.py <edl.json> [--dry-run]

Two templates (set per segment with "mode"):
  talk   full-screen talking head                                   (观点类 A / 教程类开头结尾)
  broll  full-screen B-roll, presenter's voice continues            (观点类 A：讲概念、数据时切画面)
  pip    B-roll in the upper area + presenter in a corner circle    (教程类 B：录屏/演示 + 右下角圆形)

The presenter's audio is the master timeline. Segment boundaries are given by script line numbers, so cuts
land in the pauses between sentences. Caption timing comes from the script too: speech regions are found with
silence detection and script lines are mapped onto them by character count (no speech recognition needed —
the presenter must read the script; check captions in the contact sheet).

EDL (paths relative to the EDL file):
{
  "talk": "talk.mp4", "script": "script.txt",            # one caption line per line of text
  "broll": {"anim": "broll.mp4", "screen": "rec.mp4"},
  "segments": [ {"lines": [1, 2], "mode": "talk"},
                {"lines": [3, 6], "mode": "pip",   "broll": "anim",   "broll_in": 2.5},
                {"lines": [7, 8], "mode": "broll", "broll": "screen", "broll_in": 0} ],
  "size": "1080x1920", "fps": 30, "bg": "#0F1115",
  "music": "music.wav", "music_db": -22, "lufs": -14,
  "captions": "burn",                                    # burn | srt | none  (an .srt is always written)
  "pip": {"size": 0.28, "box_h": 0.70},                  # circle diameter (fraction of width); B-roll area height
  "silence": {"noise_db": -32, "min_s": 0.30},
  "out": "final.mp4"
}
"""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path

def sh(cmd, quiet=True):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode: sys.exit(f"command failed ({p.returncode}):\n{' '.join(map(str, cmd))[:600]}\n{p.stderr[-2500:]}")
    return p

def probe(path):
    j = json.loads(sh(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)]).stdout)
    v = next((s for s in j['streams'] if s['codec_type'] == 'video'), None)
    return {'dur': float(j['format']['duration']), 'w': v and v['width'], 'h': v and v['height'],
            'audio': any(s['codec_type'] == 'audio' for s in j['streams']), 'rot': int((v or {}).get('tags', {}).get('rotate', 0) or 0)}

# ---------------------------------------------------------------- speech + captions
def speech_regions(path, noise_db, min_s, dur):
    err = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-af', f'silencedetect=noise={noise_db}dB:d={min_s}', '-vn', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', err)]
    ends = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', err)]
    sil = list(zip(starts, ends + [dur] * (len(starts) - len(ends))))
    out, t = [], 0.0
    for s, e in sil:
        if s - t > 0.08: out.append([t, s])
        t = e
    if dur - t > 0.08: out.append([t, dur])
    return out

CJK = re.compile(r'[㐀-鿿]')
def weight(line):  # spoken length proxy: CJK chars count 1, latin words ~1.6, digits ~0.6
    return max(1.0, len(CJK.findall(line)) + 1.6 * len(re.findall(r'[A-Za-z]+', line)) + 0.6 * len(re.findall(r'\d', line)))

def align(lines, speech):
    """Map script lines onto speech regions. Returns [(t0, t1)] per line and per-boundary snap error (s)."""
    total = sum(e - s for s, e in speech)
    def at(frac):  # position on the speech-only timeline -> real time
        x = frac * total
        for s, e in speech:
            if x <= e - s: return s + x
            x -= e - s
        return speech[-1][1]
    gaps = [(speech[i][1], speech[i + 1][0]) for i in range(len(speech) - 1)]
    w = [weight(l) for l in lines]; W = sum(w)
    cuts, errs, acc = [], [], 0.0
    used = set()
    for i in range(len(lines) - 1):
        acc += w[i]; t = at(acc / W)
        # snap to the nearest unused pause
        best = min((g for g in range(len(gaps)) if g not in used), key=lambda g: abs((gaps[g][0] + gaps[g][1]) / 2 - t), default=None)
        if best is not None and abs((gaps[best][0] + gaps[best][1]) / 2 - t) < 1.2:
            used.add(best); errs.append(abs((gaps[best][0] + gaps[best][1]) / 2 - t)); cuts.append(gaps[best])
        else:
            errs.append(None); cuts.append((t, t))
    bounds = []
    t0 = speech[0][0]
    for i in range(len(lines)):
        t1 = cuts[i][0] if i < len(cuts) else speech[-1][1]
        bounds.append((t0, t1))
        if i < len(cuts): t0 = cuts[i][1]
    return bounds, errs

def fmt_ts(t, ass=False):
    t = max(0, t); h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f'{h}:{m:02d}:{s:05.2f}' if ass else f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s % 1) * 1000)) % 1000:03d}'

def write_captions(lines, bounds, offset, W, H, srt_path, ass_path):
    with open(srt_path, 'w', encoding='utf-8') as f:
        for i, (l, (a, b)) in enumerate(zip(lines, bounds), 1):
            f.write(f'{i}\n{fmt_ts(a - offset)} --> {fmt_ts(b - offset)}\n{l}\n\n')
    fs = round(60 * W / 1080); mv = round(H * 0.215)   # sits above the 9:16 platform UI band, below a corner PiP
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Noto Sans CJK SC,{fs},&H00F2EFE9,&H00F2EFE9,&H00151110,&H64000000,-1,0,0,0,100,100,0,0,1,{max(3, fs // 14)},0,2,90,90,{mv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write(head)
        for l, (a, b) in zip(lines, bounds):
            f.write(f'Dialogue: 0,{fmt_ts(a - offset, True)},{fmt_ts(b - offset, True)},Cap,,0,0,0,,{l}\n')

# ---------------------------------------------------------------- video graph
def cover(W, H): return f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1'
def fit(W, H, bg): return f'scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={bg},setsar=1'

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('edl'); ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    ep = Path(a.edl).resolve(); base = ep.parent; E = json.loads(ep.read_text(encoding='utf-8'))
    W, H = map(int, E.get('size', '1080x1920').split('x')); fps = E.get('fps', 30); bg = E.get('bg', '#0F1115').replace('#', '0x')
    talk = base / E['talk']; T = probe(talk)
    if not T['audio']: sys.exit('talk video has no audio track')
    lines = [l.strip() for l in (base / E['script']).read_text(encoding='utf-8').splitlines() if l.strip()] if E.get('script') else []
    sil = E.get('silence', {})
    speech = speech_regions(talk, sil.get('noise_db', -32), sil.get('min_s', 0.30), T['dur'])
    if not speech: sys.exit('no speech detected — check the recording or silence.noise_db')
    T0, T1 = max(0.0, speech[0][0] - 0.25), min(T['dur'], speech[-1][1] + 0.5)

    report = {'speech_regions': len(speech), 'script_lines': len(lines), 'trim': [round(T0, 2), round(T1, 2)]}
    if lines:
        bounds, errs = align(lines, speech)
        report['caption_snap'] = {'snapped': sum(e is not None for e in errs), 'unsnapped': sum(e is None for e in errs),
                                  'max_snap_err_s': round(max([e for e in errs if e is not None] or [0]), 2)}
        report['lines'] = [{'n': i + 1, 't': [round(x - T0, 2) for x in b], 'text': l} for i, (l, b) in enumerate(zip(lines, bounds))]
    # ---- resolve segment times on the talk timeline
    segs = []
    for i, s in enumerate(E['segments']):
        if 'lines' in s:
            i0, i1 = s['lines']; st = bounds[i0 - 1][0]; en = bounds[i1 - 1][1]
        else:
            st, en = s['start'], s['end']
        segs.append({**s, 'st': st, 'en': en})
    segs.sort(key=lambda s: s['st'])
    # make contiguous: each cut sits mid-pause; first starts at T0, last ends at T1
    for i, s in enumerate(segs):
        s['st'] = T0 if i == 0 else (segs[i - 1]['en_raw'] + s['st']) / 2
        s['en_raw'] = s['en']
    for i, s in enumerate(segs):
        s['en'] = segs[i + 1]['st'] if i + 1 < len(segs) else T1
        s['dur'] = round(s['en'] - s['st'], 3)
    report['segments'] = [{'mode': s['mode'], 'broll': s.get('broll'), 't': [round(s['st'] - T0, 2), round(s['en'] - T0, 2)]} for s in segs]
    out = base / E.get('out', 'final.mp4'); out.parent.mkdir(parents=True, exist_ok=True)
    srt = out.with_suffix('.srt'); ass = out.with_suffix('.ass')
    if lines: write_captions(lines, bounds, T0, W, H, srt, ass)
    print(json.dumps({k: v for k, v in report.items() if k != 'lines'}, ensure_ascii=False, indent=2))
    (out.with_suffix('.edit.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if a.dry_run: return

    # ---- inputs
    inputs = ['-i', str(talk)]; bidx = {}
    for name, path in (E.get('broll') or {}).items():
        bidx[name] = len(bidx) + 1; inputs += ['-i', str(base / path)]
    P = E.get('pip', {}); d = int(round(W * P.get('size', 0.28) / 2) * 2); box_h = int(round(H * P.get('box_h', 0.70) / 2) * 2)
    m = int(W * 0.05); cx, cy = W - d - m, box_h - int(d * 0.62)          # circle straddles the bottom edge of the B-roll area
    r = d / 2
    circle = (f"crop='min(iw,ih)':'min(iw,ih)',scale={d}:{d},format=rgba,"
              f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lte(hypot(X-{r},Y-{r}),{r - 1.5}),255,if(lte(hypot(X-{r},Y-{r}),{r}),110,0))'")
    fc, labels = [], []
    for i, s in enumerate(segs):
        tt = f"trim={s['st']:.3f}:{s['en']:.3f},setpts=PTS-STARTPTS,fps={fps}"
        if s['mode'] == 'talk':
            fc.append(f"[0:v]{tt},{cover(W, H)},format=yuv420p[v{i}]")
        else:
            k = bidx[s['broll']]; bi = float(s.get('broll_in', 0))
            bt = f"trim={bi:.3f}:{bi + s['dur']:.3f},setpts=PTS-STARTPTS,fps={fps},tpad=stop_mode=clone:stop_duration={s['dur']:.3f},trim=duration={s['dur']:.3f}"
            if s['mode'] == 'broll':
                fc.append(f"[{k}:v]{bt},{fit(W, H, bg)},format=yuv420p[v{i}]")
            elif s['mode'] == 'pip':
                fc.append(f"[{k}:v]{bt},{fit(W, box_h, bg)},pad={W}:{H}:0:0:color={bg}[b{i}]")
                fc.append(f"[0:v]{tt},{circle}[c{i}]")
                fc.append(f"[b{i}][c{i}]overlay={cx}:{cy}:format=auto,format=yuv420p[v{i}]")
            else: sys.exit(f"unknown mode {s['mode']}")
        labels.append(f'[v{i}]')
    fc.append(f"{''.join(labels)}concat=n={len(segs)}:v=1:a=0[vcat]")
    vout = '[vcat]'
    if lines and E.get('captions', 'burn') == 'burn':
        fc.append(f"[vcat]subtitles='{str(ass).replace(chr(92), '/').replace(':', chr(92) + ':')}'[vsub]"); vout = '[vsub]'
    fc.append(f"[0:a]atrim={T0:.3f}:{T1:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo[voice]")
    aout = '[voice]'
    if E.get('music'):
        inputs += ['-stream_loop', '-1', '-i', str(base / E['music'])]
        mi = len(bidx) + 1
        fc.append(f"[{mi}:a]atrim=0:{T1 - T0:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,volume={E.get('music_db', -22)}dB,"
                  f"afade=t=out:st={max(0, T1 - T0 - 1.2):.3f}:d=1.2[mus]")
        fc.append("[voice][mus]amix=inputs=2:duration=first:normalize=0[mix]"); aout = '[mix]'
    tmp = out.with_suffix('.premaster.mp4')
    sh(['ffmpeg', '-y', '-v', 'error', *inputs, '-filter_complex', ';'.join(fc), '-map', vout, '-map', aout,
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', str(fps),
        '-c:a', 'aac', '-b:a', '192k', '-t', f'{T1 - T0:.3f}', '-movflags', '+faststart', str(tmp)])
    # two-pass loudness normalisation (video copied)
    lufs = E.get('lufs', -14)
    err = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(tmp), '-af', f'loudnorm=I={lufs}:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    mm = json.loads(re.findall(r'\{[^{}]*"input_i"[^{}]*\}', err)[-1])
    af = (f"loudnorm=I={lufs}:TP=-1.5:LRA=11:measured_I={mm['input_i']}:measured_TP={mm['input_tp']}:measured_LRA={mm['input_lra']}:"
          f"measured_thresh={mm['input_thresh']}:offset={mm['target_offset']}:linear=true")
    sh(['ffmpeg', '-y', '-v', 'error', '-i', str(tmp), '-af', af, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
        '-t', f'{T1 - T0:.3f}', '-movflags', '+faststart', str(out)])
    tmp.unlink()
    print(f'wrote {out} ({T1 - T0:.1f}s) + {srt.name}')

if __name__ == '__main__':
    main()
