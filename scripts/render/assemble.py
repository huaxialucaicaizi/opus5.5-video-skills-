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
  "style": {"series": "AI小白课 · 01", "hook": "AI 总给你一堆【废话】？", "name_tag": "前腾讯增长 8 年 · 深大 AI 老师",
            "end": {"text": "关注我", "sub": "下期：AI Skill 是什么"}},      # shared packaging (see content-ops STYLE.md)
  "line_times": [[0.3, 2.1], ...],                       # optional: manual caption timing instead of pause detection
  "segments": [ {"lines": [1, 2], "mode": "talk"},
                {"lines": [3, 6], "mode": "pip",   "broll": "anim",   "broll_in": 2.5, "broll_len": 1.2, "chapter": "第1步 · 角色"},
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
    w = [weight(plain(l)) for l in lines]; W = sum(w)
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

KW = re.compile(r'【([^】]+)】')
def plain(l): return KW.sub(r'\1', l)

FONTS = Path(__file__).resolve().parents[2] / 'assets' / 'fonts'
BRAND = {'text': '#F6F0E6', 'accent': '#C8FF3C', 'ink': '#161616', 'display_font': 'ZCOOL KuaiLe'}   # see content-ops/STYLE.md

def ass_color(hex6, alpha=0):  # '#RRGGBB' -> ASS &HAABBGGRR
    h = hex6.lstrip('#'); return f'&H{alpha:02X}{h[4:6]}{h[2:4]}{h[0:2]}'.upper().replace('&H', '&H')

def write_captions(lines, bounds, offset, W, H, srt_path, ass_path, segs=None, S=None, total=None):
    """Captions + the shared packaging layer (series label, name tag, hook, chapter cards, end card).
    Everything is ASS so every video gets exactly the same look. 【关键词】 in the script turns orange."""
    S = S or {}; segs = segs or []
    with open(srt_path, 'w', encoding='utf-8') as f:
        for i, (l, (a, b)) in enumerate(zip(lines, bounds), 1):
            f.write(f'{i}\n{fmt_ts(a - offset)} --> {fmt_ts(b - offset)}\n{plain(l)}\n\n')
    k = W / 1080
    B = {**BRAND, **((S or {}).get('colors') or {})}
    TXT, ACC, INK, WHT = ass_color(B['text']), ass_color(B['accent']), ass_color(B['ink']), ass_color('#FFFFFF')
    SER = ass_color((S or {}).get('series_color') or B['accent'])          # series tag colour: 小白课 = lime, AI观察 = pink
    SER_TXT = WHT if (S or {}).get('series_color') else ACC
    SER_BOX = SER if (S or {}).get('series_color') else INK
    DF = B['display_font']
    hl = lambda l, base=TXT: KW.sub(lambda m: '{\\c' + ACC + '&}' + m.group(1) + '{\\c' + base + '&}', l)
    fs = round(60 * k); mv = round(H * 0.215)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Noto Sans CJK SC,{fs},{TXT},{TXT},{INK},&H64000000,-1,0,0,0,100,100,0,0,1,{max(3, round(fs / 13))},0,2,90,90,{mv},1
Style: Series,{DF},{round(40 * k)},{SER_TXT},{SER_TXT},{SER_BOX},{SER_BOX},0,0,0,0,100,100,1,-3,3,{round(12 * k)},0,7,0,0,0,1
Style: Tag,Noto Sans CJK SC,{round(38 * k)},{INK},{INK},{WHT},{WHT},-1,0,0,0,100,100,0,-2,3,{round(12 * k)},0,1,0,0,0,1
Style: Hook,{DF},{round(120 * k)},{WHT},{WHT},{INK},&H60000000,0,0,0,0,100,100,2,-4,1,{round(9 * k)},{round(5 * k)},5,60,60,0,1
Style: Chapter,{DF},{round(50 * k)},{INK},{INK},{ACC},{ACC},0,0,0,0,100,100,1,-3,3,{round(14 * k)},0,7,0,0,0,1
Style: EndBig,{DF},{round(130 * k)},{ACC},{ACC},{INK},&H00000000,0,0,0,0,100,100,2,-4,1,{round(8 * k)},0,5,0,0,0,1
Style: EndSub,{DF},{round(58 * k)},{WHT},{WHT},{INK},&H00000000,0,0,0,0,100,100,0,0,1,{round(5 * k)},0,5,0,0,0,1
Style: Shade,Noto Sans CJK SC,10,{INK},{INK},{INK},{INK},0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    T = lambda t: fmt_ts(t, True)
    total = total or (bounds[-1][1] - offset if bounds else 0)
    ev = []
    x0, top = round(72 * k), round(232 * k)
    if S.get('series'):   # only while the presenter is full-screen: B-roll carries its own top caption
        for sg in segs:
            if sg['mode'] == 'talk':
                ev.append(f"Dialogue: 2,{T(sg['st'] - offset)},{T(sg['en'] - offset)},Series,,0,0,0,,{{\\an7\\pos({x0},{top})}}{S['series']}")
    if S.get('hook'):
        ev.append(f"Dialogue: 3,{T(0.15)},{T(S.get('hook_s', 2.6))},Hook,,0,0,0,,{{\\an5\\pos({W // 2},{round(H * 0.34)})\\fad(120,260)}}{hl(S['hook'])}")
    talk0 = next((sg for sg in segs if sg['mode'] == 'talk'), None)
    if S.get('name_tag') and talk0:
        a = talk0['st'] - offset + (S.get('hook_s', 2.6) if S.get('hook') else 0.3)
        b = min(talk0['en'] - offset, a + 3.2)
        if b - a > 1.0:
            ev.append(f"Dialogue: 3,{T(a)},{T(b)},Tag,,0,0,0,,{{\\an1\\pos({x0},{round(H * 0.62)})\\fad(200,200)}}{S['name_tag']}")
    cap_top = H - round(H * 0.215) - round(fs * 1.25)          # top edge of the caption band
    for sg in segs:
        if sg.get('chapter'):
            a = sg['st'] - offset + 0.1; b = min(sg['en'] - offset, a + 2.4)
            pos = (f"\\an7\\pos({x0},{top + round(70 * k)})" if sg['mode'] == 'talk'      # under the series label
                   else f"\\an1\\pos({x0},{cap_top - round(16 * k)})")                        # bottom-left, just above captions
            ev.append(f"Dialogue: 3,{T(a)},{T(b)},Chapter,,0,0,0,,{{{pos}\\fad(150,200)}}{sg['chapter']}")
    E = S.get('end')
    end_from = total - E.get('seconds', 2.4) if E else total + 1
    if E:
        ev.append(f"Dialogue: 4,{T(end_from)},{T(total)},Shade,,0,0,0,,{{\\an7\\pos(0,0)\\alpha&H40&\\fad(250,0)\\p1}}m 0 0 l {W} 0 {W} {H} 0 {H}{{\\p0}}")
        ev.append(f"Dialogue: 5,{T(end_from)},{T(total)},EndBig,,0,0,0,,{{\\an5\\pos({W // 2},{round(H * 0.40)})\\fad(250,0)}}{E.get('text', '关注我')}")
        if E.get('sub'):
            ev.append(f"Dialogue: 5,{T(end_from + 0.2)},{T(total)},EndSub,,0,0,0,,{{\\an5\\pos({W // 2},{round(H * 0.47)})\\fad(250,0)}}{E['sub']}")
    for l, (a, b) in zip(lines, bounds):
        a, b = a - offset, b - offset
        if a >= end_from: continue
        ev.append(f'Dialogue: 1,{T(a)},{T(min(b, end_from))},Cap,,0,0,0,,{hl(l)}')
    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write(head + '\n'.join(ev) + '\n')

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
    if E.get('line_times'):   # demo / manual timing: trust the given times
        speech = [[E['line_times'][0][0], E['line_times'][-1][1]]]
    if not speech: sys.exit('no speech detected — check the recording or silence.noise_db')
    T0, T1 = max(0.0, speech[0][0] - 0.25), min(T['dur'], speech[-1][1] + 0.5)

    report = {'speech_regions': len(speech), 'script_lines': len(lines), 'trim': [round(T0, 2), round(T1, 2)]}
    if lines and E.get('line_times'):
        bounds, errs = [tuple(x) for x in E['line_times']], []
        report['caption_snap'] = 'manual line_times'
    elif lines:
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
    if lines: write_captions(lines, bounds, T0, W, H, srt, ass, segs, E.get('style'), T1 - T0)
    print(json.dumps({k: v for k, v in report.items() if k != 'lines'}, ensure_ascii=False, indent=2))
    (out.with_suffix('.edit.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if a.dry_run: return

    # ---- render each segment to its own file (constant memory regardless of the number of cuts)
    work = Path(tempfile.mkdtemp(prefix='assemble-', dir=str(out.parent)))
    broll = {name: base / path for name, path in (E.get('broll') or {}).items()}
    # PiP layout: B-roll band between the series-label zone and the caption band; circle overlaps its lower-right corner
    P = E.get('pip', {}); d = int(round(W * P.get('size', 0.28) / 2) * 2)
    box_y = int(round(H * P.get('top', 0.156) / 2) * 2); box_h = int(round(H * P.get('box_h', 0.552) / 2) * 2)
    m = int(W * 0.05); cx, cy = W - d - m, box_y + box_h - int(d * 0.80)
    r = d / 2
    circle = (f"crop='min(iw,ih)':'min(iw,ih)',scale={d}:{d},format=rgba,"
              f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lte(hypot(X-{r},Y-{r}),{r - 1.5}),255,if(lte(hypot(X-{r},Y-{r}),{r}),110,0))'")
    _a = {**BRAND, **((E.get('style') or {}).get('colors') or {})}['accent'].lstrip('#'); RING = tuple(int(_a[i:i + 2], 16) for i in (0, 2, 4))
    rw = max(6, int(d * 0.035)); D = d + 2 * rw; R = D / 2
    enc = ['-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '15', '-pix_fmt', 'yuv420p', '-r', str(fps)]
    parts = []
    for i, s in enumerate(segs):
        seg = work / f'seg{i:03d}.mp4'; dur = s['dur']
        talk_in = ['-ss', f"{s['st']:.3f}", '-t', f'{dur:.3f}', '-i', str(talk)]
        if s['mode'] == 'talk':
            sh(['ffmpeg', '-y', '-v', 'error', *talk_in, '-vf', f'fps={fps},{cover(W, H)},format=yuv420p', '-t', f'{dur:.3f}', *enc, str(seg)])
        else:
            if s.get('broll') not in broll: sys.exit(f"segment {i}: unknown broll '{s.get('broll')}'")
            bi = float(s.get('broll_in', 0)); bl = min(dur, float(s.get('broll_len', dur)))   # broll_len: play N s, then hold
            b_in = ['-ss', f'{bi:.3f}', '-t', f'{bl:.3f}', '-i', str(broll[s['broll']])]
            bt = f"fps={fps},tpad=stop_mode=clone:stop_duration={dur:.3f},trim=duration={dur:.3f},setpts=PTS-STARTPTS"
            if s['mode'] == 'broll':
                sh(['ffmpeg', '-y', '-v', 'error', *b_in, '-vf', f'{bt},{fit(W, H, bg)},format=yuv420p', '-t', f'{dur:.3f}', *enc, str(seg)])
            elif s['mode'] == 'pip':
                # portrait B-roll (our 9:16 animations): drop the empty platform-UI bands so the content fills the band
                pb = probe(broll[s['broll']]); crop = 'crop=iw:ih*0.75:0:ih*0.094,' if pb['h'] and pb['h'] > pb['w'] else ''
                fg = (f"[0:v]{bt},{crop}{fit(W, box_h, bg)},pad={W}:{H}:0:{box_y}:color={bg}[b];"
                      f"[1:v]fps={fps},setpts=PTS-STARTPTS,{circle}[c];"
                      f"color=c=0x{RING[0]:02X}{RING[1]:02X}{RING[2]:02X}:s={D}x{D}:r={fps}:d={dur:.3f},format=rgba,"
                      f"geq=r='{RING[0]}':g='{RING[1]}':b='{RING[2]}':a='if(between(hypot(X-{R},Y-{R}),{R - rw - 1},{R}),255,0)'[ring];"
                      f"[b][ring]overlay={cx - rw}:{cy - rw}:format=auto[br];[br][c]overlay={cx}:{cy}:format=auto,format=yuv420p[v]")
                sh(['ffmpeg', '-y', '-v', 'error', *b_in, *talk_in, '-filter_complex', fg, '-map', '[v]', '-t', f'{dur:.3f}', *enc, str(seg)])
            else: sys.exit(f"unknown mode {s['mode']}")
        parts.append(seg)
    lst = work / 'list.txt'; lst.write_text(''.join(f"file '{p.name}'\n" for p in parts))
    # ---- join, burn captions + packaging, mix audio
    vf = []
    if lines and E.get('captions', 'burn') == 'burn':
        vf.append(f"subtitles='{str(ass).replace(chr(92), '/').replace(':', chr(92) + ':')}':fontsdir='{FONTS}'")
    inputs = ['-f', 'concat', '-safe', '0', '-i', str(lst), '-ss', f'{T0:.3f}', '-t', f'{T1 - T0:.3f}', '-i', str(talk)]
    fc = [f"[0:v]{','.join(vf) if vf else 'null'}[vout]",
          "[1:a]asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo[voice]"]
    aout = '[voice]'
    if E.get('music'):
        inputs += ['-stream_loop', '-1', '-i', str(base / E['music'])]
        fc.append(f"[2:a]atrim=0:{T1 - T0:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,volume={E.get('music_db', -22)}dB,"
                  f"afade=t=out:st={max(0, T1 - T0 - 1.2):.3f}:d=1.2[mus]")
        fc.append("[voice][mus]amix=inputs=2:duration=first:normalize=0[mix]"); aout = '[mix]'
    tmp = out.with_suffix('.premaster.mp4')
    sh(['ffmpeg', '-y', '-v', 'error', *inputs, '-filter_complex', ';'.join(fc), '-map', '[vout]', '-map', aout,
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', str(fps),
        '-c:a', 'aac', '-b:a', '192k', '-t', f'{T1 - T0:.3f}', '-movflags', '+faststart', str(tmp)])
    import shutil; shutil.rmtree(work, ignore_errors=True)
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
