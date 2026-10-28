#!/usr/bin/env python3
"""footage.py — FFmpeg wrappers for editing existing footage. Never modifies inputs.

    footage.py probe    <in>
    footage.py trim     <in> --start S --end E -o out.mp4
    footage.py concat   <a> <b> [...] -o out.mp4 [--size WxH] [--fps N]
    footage.py pip      <background> <foreground> -o out.mp4 [--corner br|bl|tr|tl] [--size 0.32] [--margin 0.05]
                        [--circle] [--audio fg|bg|mix|none] [--bottom-safe 0.30]
    footage.py pip-region <WxH> [--corner br] [--size 0.32]      -> JSON for storyboard.reserved_regions
    footage.py subs     <in> <subs.srt> -o out.mp4 [--burn] [--font "Noto Sans CJK SC"] [--fontsize 54]
    footage.py audio    <in> <audio> -o out.mp4 [--mode replace|mix] [--music-db -18]
    footage.py frames   <in> -o <dir> [--fps 30]
    footage.py loudnorm <in> -o out.mp4 [--lufs -14]
"""
import argparse, json, subprocess, sys, tempfile
from pathlib import Path

ENC_V = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart']
ENC_A = ['-c:a', 'aac', '-b:a', '192k', '-ar', '48000']

def sh(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode: sys.exit(f"ffmpeg failed ({p.returncode}):\n{' '.join(cmd)}\n{p.stderr[-2000:]}")
    return p

def probe(path):
    p = sh(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)])
    j = json.loads(p.stdout)
    v = next((s for s in j['streams'] if s['codec_type'] == 'video'), None)
    a = next((s for s in j['streams'] if s['codec_type'] == 'audio'), None)
    subs = [s for s in j['streams'] if s['codec_type'] == 'subtitle']
    return {'path': str(path), 'duration': float(j['format']['duration']),
            'video': v and {'codec': v['codec_name'], 'width': v['width'], 'height': v['height'], 'fps': v['r_frame_rate'], 'avg_fps': v.get('avg_frame_rate'), 'pix_fmt': v.get('pix_fmt')},
            'audio': a and {'codec': a['codec_name'], 'channels': a.get('channels'), 'rate': a.get('sample_rate')},
            'subtitles': len(subs), 'vfr': bool(v and v['r_frame_rate'] != v.get('avg_frame_rate'))}

def guard(inp, out):
    if Path(inp).resolve() == Path(out).resolve(): sys.exit('refusing to overwrite an input file')

def cmd_trim(a):
    guard(a.input, a.o)
    sh(['ffmpeg', '-y', '-v', 'error', '-ss', str(a.start), '-i', a.input, '-t', str(a.end - a.start), *ENC_V, *ENC_A, a.o])

def cmd_concat(a):
    for i in a.inputs: guard(i, a.o)
    p0 = probe(a.inputs[0])
    W, H = (map(int, a.size.split('x')) if a.size else (p0['video']['width'], p0['video']['height']))
    fps = a.fps or round(eval(p0['video']['fps']))
    parts, labels = [], []
    for i, f in enumerate(a.inputs):
        has_a = probe(f)['audio'] is not None
        parts.append(f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p[v{i}]")
        parts.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo[a{i}]" if has_a else
                     f"anullsrc=r=48000:cl=stereo,atrim=duration={probe(f)['duration']}[a{i}]")
        labels.append(f"[v{i}][a{i}]")
    fc = ';'.join(parts) + f";{''.join(labels)}concat=n={len(a.inputs)}:v=1:a=1[v][a]"
    cmd = ['ffmpeg', '-y', '-v', 'error']
    for f in a.inputs: cmd += ['-i', f]
    sh(cmd + ['-filter_complex', fc, '-map', '[v]', '-map', '[a]', *ENC_V, *ENC_A, a.o])

def cmd_pip(a):
    guard(a.background, a.o); guard(a.foreground, a.o)
    bg = probe(a.background); W, H = bg['video']['width'], bg['video']['height']
    b = pip_box(W, H, a.corner, a.size, a.margin, a.bottom_safe)  # same box `pip-region` reports
    d, x, y = b['w'], b['x'], b['y']
    fg = f"[1:v]crop='min(iw,ih)':'min(iw,ih)',scale={d}:{d},format=rgba"
    if a.circle:
        r = d / 2
        fg += f",geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lte(hypot(X-{r},Y-{r}),{r - 1}),255,if(lte(hypot(X-{r},Y-{r}),{r}),128,0))'"
    fg += '[fg]'
    fc = f"{fg};[0:v][fg]overlay={x}:{y}:shortest=1:format=auto,format=yuv420p[v]"
    amap = {'fg': ['-map', '1:a?'], 'bg': ['-map', '0:a?'], 'none': ['-an'], 'mix': []}[a.audio]
    if a.audio == 'mix':
        fc += ';[0:a][1:a]amix=inputs=2:duration=shortest:normalize=0[a]'; amap = ['-map', '[a]']
    dur = min(bg['duration'], probe(a.foreground)['duration'])
    sh(['ffmpeg', '-y', '-v', 'error', '-i', a.background, '-i', a.foreground, '-filter_complex', fc, '-map', '[v]', *amap,
        '-t', f'{dur:.3f}', *ENC_V, *(ENC_A if a.audio != 'none' else []), a.o])

def pip_box(W, H, corner='br', size=0.32, margin=0.05, bottom_safe=0.30):
    d = int(round(W * size / 2) * 2); m = int(W * margin); bottom = int(H * bottom_safe)
    x = W - d - m if corner in ('br', 'tr') else m
    y = H - d - bottom if corner in ('br', 'bl') else int(H * 0.12)
    return {'x': x, 'y': y, 'w': d, 'h': d, 'label': f'pip-{corner}'}

def cmd_pip_region(a):
    W, H = map(int, a.size_px.split('x'))
    print(json.dumps(pip_box(W, H, a.corner, a.size, a.margin, a.bottom_safe)))

def cmd_subs(a):
    guard(a.input, a.o)
    if a.burn:
        style = f"FontName={a.font},FontSize={a.fontsize},Outline=2,Shadow=0,MarginV=60"
        sub = a.subs.replace('\\', '/').replace(':', '\\:').replace("'", "\\'")
        sh(['ffmpeg', '-y', '-v', 'error', '-i', a.input, '-vf', f"subtitles='{sub}':force_style='{style}'", *ENC_V, '-c:a', 'copy', a.o])  # ENC_V already sets +faststart
    else:
        sh(['ffmpeg', '-y', '-v', 'error', '-i', a.input, '-i', a.subs, '-map', '0', '-map', '1', '-c', 'copy', '-c:s', 'mov_text', '-movflags', '+faststart',
            '-metadata:s:s:0', f'language={a.lang}', a.o])

def cmd_audio(a):
    guard(a.input, a.o)
    if a.mode == 'replace':
        sh(['ffmpeg', '-y', '-v', 'error', '-i', a.input, '-i', a.audio, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', *ENC_A, '-shortest', '-movflags', '+faststart', a.o])
    else:
        fc = f"[1:a]volume={a.music_db}dB[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]"
        sh(['ffmpeg', '-y', '-v', 'error', '-i', a.input, '-i', a.audio, '-filter_complex', fc, '-map', '0:v', '-map', '[a]', '-c:v', 'copy', *ENC_A, '-movflags', '+faststart', a.o])

def cmd_frames(a):
    Path(a.o).mkdir(parents=True, exist_ok=True)
    sh(['ffmpeg', '-y', '-v', 'error', '-i', a.input, '-vf', f'fps={a.fps}', '-q:v', '2', str(Path(a.o) / 'f%05d.jpg')])

def cmd_loudnorm(a):
    guard(a.input, a.o)
    import re
    p = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', a.input, '-af', f'loudnorm=I={a.lufs}:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True)
    m = json.loads(re.findall(r'\{[^{}]*"input_i"[^{}]*\}', p.stderr)[-1])
    af = (f"loudnorm=I={a.lufs}:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    sh(['ffmpeg', '-y', '-v', 'error', '-i', a.input, '-af', af, '-c:v', 'copy', *ENC_A, '-movflags', '+faststart', '-t', str(probe(a.input)['duration']), a.o])

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('probe'); s.add_argument('input')
    s = sp.add_parser('trim'); s.add_argument('input'); s.add_argument('--start', type=float, required=True); s.add_argument('--end', type=float, required=True); s.add_argument('-o', required=True)
    s = sp.add_parser('concat'); s.add_argument('inputs', nargs='+'); s.add_argument('-o', required=True); s.add_argument('--size'); s.add_argument('--fps', type=int)
    s = sp.add_parser('pip'); s.add_argument('background'); s.add_argument('foreground'); s.add_argument('-o', required=True)
    s.add_argument('--corner', default='br', choices=['br', 'bl', 'tr', 'tl']); s.add_argument('--size', type=float, default=0.32); s.add_argument('--margin', type=float, default=0.05)
    s.add_argument('--circle', action='store_true'); s.add_argument('--audio', default='fg', choices=['fg', 'bg', 'mix', 'none']); s.add_argument('--bottom-safe', type=float, default=0.30, help='distance from bottom as fraction of H; default leaves the subtitle band (≈0.19–0.27 H) clear')
    s = sp.add_parser('pip-region', help='print the reserved_regions entry a later `pip` call will cover')
    s.add_argument('size_px', help='WxH of the background video'); s.add_argument('--corner', default='br', choices=['br', 'bl', 'tr', 'tl'])
    s.add_argument('--size', type=float, default=0.32); s.add_argument('--margin', type=float, default=0.05); s.add_argument('--bottom-safe', type=float, default=0.30)
    s = sp.add_parser('subs'); s.add_argument('input'); s.add_argument('subs'); s.add_argument('-o', required=True); s.add_argument('--burn', action='store_true')
    s.add_argument('--font', default='Noto Sans CJK SC'); s.add_argument('--fontsize', type=int, default=18); s.add_argument('--lang', default='chi')
    s = sp.add_parser('audio'); s.add_argument('input'); s.add_argument('audio'); s.add_argument('-o', required=True); s.add_argument('--mode', default='replace', choices=['replace', 'mix']); s.add_argument('--music-db', type=float, default=-18)
    s = sp.add_parser('frames'); s.add_argument('input'); s.add_argument('-o', required=True); s.add_argument('--fps', type=float, default=30)
    s = sp.add_parser('loudnorm'); s.add_argument('input'); s.add_argument('-o', required=True); s.add_argument('--lufs', type=float, default=-14)
    a = ap.parse_args()
    if a.cmd == 'probe': print(json.dumps(probe(a.input), ensure_ascii=False, indent=2)); return
    if a.cmd == 'pip-region': cmd_pip_region(a); return
    globals()[f'cmd_{a.cmd}'](a)
    if hasattr(a, 'o') and a.cmd != 'frames': print(json.dumps({'wrote': a.o, **{k: v for k, v in probe(a.o).items() if k in ('duration', 'video', 'audio', 'subtitles')}}, ensure_ascii=False))
    else: print(f'wrote {a.o}')

if __name__ == '__main__':
    main()
