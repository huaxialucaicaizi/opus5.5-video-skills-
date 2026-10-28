#!/usr/bin/env python3
"""probe_video.py — technical checks on a rendered MP4 with ffprobe/ffmpeg only.

    python3 scripts/validate/probe_video.py <video.mp4> [--project <dir>] [--lufs -14]

T1 duration, T2 resolution/fps, T3 codec/pix_fmt/faststart, T5 black segments, T6 frozen segments, A1 loudness.
Without --project only absolute checks run (T3, T5, T6, A1 vs --lufs).
"""
import argparse, json, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import check, skip, load_project, print_checks

def ffprobe(path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)], capture_output=True, text=True, check=True)
    return json.loads(p.stdout)

def ff_filter(path, vf=None, af=None):
    cmd = ['ffmpeg', '-hide_banner', '-nostats', '-i', str(path)]
    if vf: cmd += ['-vf', vf, '-an']
    if af: cmd += ['-af', af, '-vn']
    cmd += ['-f', 'null', '-']
    return subprocess.run(cmd, capture_output=True, text=True).stderr

def faststart(path):
    # moov atom before mdat?  Read the top-level box order.
    with open(path, 'rb') as f:
        order = []
        while len(order) < 8:
            hdr = f.read(8)
            if len(hdr) < 8: break
            size = int.from_bytes(hdr[:4], 'big'); typ = hdr[4:8].decode('latin1')
            order.append(typ)
            if size == 1: size = int.from_bytes(f.read(8), 'big'); f.seek(size - 16, 1)
            elif size == 0: break
            else: f.seek(size - 8, 1)
    return 'moov' in order and 'mdat' in order and order.index('moov') < order.index('mdat'), order

def run(video, project=None, lufs=None):
    video = Path(video); out = []
    if not video.exists():
        return [check('T0.exists', 'P0', False, 'video file exists', str(video))]
    info = ffprobe(video)
    v = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
    a = next((s for s in info['streams'] if s['codec_type'] == 'audio'), None)
    dur = float(info['format']['duration'])
    fps = eval(v['r_frame_rate']) if v else 0  # "30/1"
    task = sb = None
    if project:
        _, task, sb, _ = load_project(project)
    exp_dur = (task or {}).get('duration_s') or (sb or {}).get('duration_s')
    if exp_dur:
        out.append(check('T1.duration', 'P0', abs(dur - exp_dur) <= 1 / max(fps, 1) + 0.05, f'duration {dur:.3f}s (expected {exp_dur}s)', f'{dur:.3f}s'))
    else: out.append(skip('T1.duration', 'P0', 'duration matches spec', 'no project given'))
    if sb:
        ok = v and v['width'] == sb['width'] and v['height'] == sb['height'] and abs(fps - sb['fps']) < 1e-6
        out.append(check('T2.format', 'P0', bool(ok), f"{v['width']}x{v['height']} @{fps:g}fps (expected {sb['width']}x{sb['height']} @{sb['fps']})"))
    else: out.append(skip('T2.format', 'P0', 'resolution/fps match spec', 'no project given'))
    fs, order = faststart(video)
    det = []
    if not v or v['codec_name'] != 'h264': det.append(f"video codec {v and v['codec_name']}")
    if v and v.get('pix_fmt') != 'yuv420p': det.append(f"pix_fmt {v.get('pix_fmt')}")
    if not fs: det.append(f'moov not before mdat ({order})')
    want_audio = (task or {}).get('audio', {}).get('music', {}).get('source', 'none') != 'none' if task else a is not None
    if want_audio and (not a or a['codec_name'] != 'aac'): det.append(f"audio {a and a['codec_name']} (expected aac)")
    out.append(check('T3.codec', 'P0', not det, 'H.264 yuv420p, faststart' + (', AAC audio' if want_audio else ''), '; '.join(det)))

    # T5 black frames (ignore ≤0.5 s at head/tail: fades)
    err = ff_filter(video, vf='blackdetect=d=0.3:pic_th=0.98:pix_th=0.06')
    blacks = [(float(s), float(e)) for s, e in re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', err)]
    bad = [(s, e) for s, e in blacks if not (s <= 0.5 and e <= 0.8) and not (s >= dur - 0.8)]
    out.append(check('T5.black', 'P1', not bad, 'no black segments ≥0.3s (except head/tail fades)', f'{bad}'))
    # T6 frozen frames
    err = ff_filter(video, vf='freezedetect=n=-60dB:d=1.0')
    frz = [float(x) for x in re.findall(r'freeze_duration: ([\d.]+)', err)]
    starts = [float(x) for x in re.findall(r'freeze_start: ([\d.]+)', err)]
    out.append(check('T6.frozen', 'P1', not starts, 'no frozen segments ≥1.0s', f'starts {starts} durations {frz}'))
    # A1 loudness
    target = lufs if lufs is not None else (task or {}).get('audio', {}).get('target_lufs', -14)
    if a:
        err = ff_filter(video, af='ebur128=peak=true')
        summ = err[err.rfind('Summary:'):]
        I = float(re.search(r'I:\s+(-?[\d.]+) LUFS', summ).group(1))
        tp = re.search(r'Peak:\s+(-?[\d.]+|-inf) dBFS', summ)
        TP = float(tp.group(1)) if tp and tp.group(1) != '-inf' else -99
        out.append(check('A1.loudness', 'P1', abs(I - target) <= 2 and TP <= -1.0, f'integrated {I:.1f} LUFS (target {target}±2), true peak {TP:.1f} dBTP (≤ -1)'))
    elif want_audio:
        out.append(check('A1.loudness', 'P1', False, 'loudness', 'no audio stream'))
    else:
        out.append(skip('A1.loudness', 'P1', 'loudness', 'no audio requested'))
    return out, {'duration': dur, 'fps': fps, 'width': v and v['width'], 'height': v and v['height'], 'size_bytes': int(info['format']['size']),
                 'bitrate': int(info['format'].get('bit_rate', 0)), 'audio': bool(a), 'black': blacks}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('video'); ap.add_argument('--project'); ap.add_argument('--lufs', type=float)
    a = ap.parse_args()
    res, meta = run(a.video, a.project, a.lufs)
    print_checks(res, f'video: {a.video}')
    print('  meta:', json.dumps(meta))
    return 1 if any(c['status'] == 'fail' for c in res) else 0

if __name__ == '__main__':
    sys.exit(main())
