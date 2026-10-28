#!/usr/bin/env python3
"""synth_music.py — procedurally generate an original music bed + UI sound effects for a storyboard.

    python3 scripts/render/synth_music.py <project_dir> [--out <dir>] [--lufs -14] [--seed 7]

Reads storyboard.json (bpm, duration_s, scenes[].audio_cues) and writes:
    <out>/music_raw.wav   unnormalised mix
    <out>/audio.wav       loudness-normalised (two-pass EBU R128 via ffmpeg loudnorm)
    <out>/audio_cues.json resolved cue list (absolute times) for QA

Everything is synthesised from sine/noise primitives, so the result is original work with no
third-party licence attached. Deterministic for a given seed.
"""
import argparse, json, re, subprocess, sys, wave
from pathlib import Path
import numpy as np

SR = 48000

def note_hz(n):  # MIDI note -> Hz
    return 440.0 * 2 ** ((n - 69) / 12)

def env_adsr(n, a, d, s, r, sr=SR):
    a, d, r = int(a * sr), int(d * sr), int(r * sr)
    sus = max(0, n - a - d - r)
    e = np.concatenate([np.linspace(0, 1, a, False), np.linspace(1, s, d, False), np.full(sus, s), np.linspace(s, 0, r)])
    return e[:n] if len(e) >= n else np.pad(e, (0, n - len(e)))

def onepole_lp(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x); acc = 0.0
    # vectorised enough for a 15–60 s bed; loop over blocks would be faster but this is fine
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc; y[i] = acc
    return y

def add(buf, sig, t, gain=1.0, pan=0.0):
    i = int(round(t * SR))
    if i >= len(buf): return
    sig = sig[: len(buf) - i]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:i + len(sig), 0] += sig * gain * l * np.sqrt(2)
    buf[i:i + len(sig), 1] += sig * gain * r * np.sqrt(2)

def tone(freq, dur, harmonics=(1.0,), detune=0.0):
    t = np.arange(int(dur * SR)) / SR
    out = np.zeros_like(t)
    for k, amp in enumerate(harmonics, 1):
        out += amp * np.sin(2 * np.pi * freq * k * t)
        if detune: out += amp * 0.6 * np.sin(2 * np.pi * freq * k * (1 + detune) * t + 1.3)
    return out

# ---------------------------------------------------------------- instruments
def pad_chord(notes, dur):
    s = sum(tone(note_hz(n), dur, (1, .35, .18, .08), detune=0.004) for n in notes) / len(notes)
    return s * env_adsr(len(s), 0.35, 0.3, 0.75, 0.6)

def bass(n, dur):
    s = tone(note_hz(n), dur, (1, .4, .1))
    return s * env_adsr(len(s), 0.005, 0.12, 0.5, 0.12)

def kick():
    d = 0.22; t = np.arange(int(d * SR)) / SR
    f = 48 + 70 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14)

def hat(rng):
    d = 0.05; n = rng.standard_normal(int(d * SR))
    n = n - onepole_lp(n, 6000)  # crude high-pass
    return n * np.exp(-np.arange(len(n)) / SR * 70) * 0.5

def sfx(kind, rng):
    if kind == 'tick':
        d = 0.035; t = np.arange(int(d * SR)) / SR
        return np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 120)
    if kind == 'pop':
        d = 0.09; t = np.arange(int(d * SR)) / SR
        f = 380 + 700 * (t / d)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 38)
    if kind == 'whoosh':
        d = 0.45; n = rng.standard_normal(int(d * SR))
        n = onepole_lp(n, 1800); e = np.sin(np.linspace(0, np.pi, len(n))) ** 2
        return n * e * 1.6
    if kind == 'chime':
        d = 1.6; t = np.arange(int(d * SR)) / SR
        s = sum(a * np.sin(2 * np.pi * note_hz(88) * r * t) * np.exp(-t * dk) for a, r, dk in [(1, 1, 3), (.5, 2.01, 5), (.3, 3.0, 7), (.2, 4.2, 9)])
        return s * 0.5
    if kind == 'hit':
        return kick() * 1.2
    raise ValueError(kind)

# ---------------------------------------------------------------- arrangement
PROG = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [48, 52, 55]), (55, [55, 59, 62])]  # Am F C G

def build(sb, seed=7):
    rng = np.random.default_rng(seed)
    bpm = float(sb.get('bpm') or 120); beat = 60 / bpm; bar = beat * 4
    dur = float(sb['duration_s']); off = float(sb.get('beat_offset_s') or 0)
    buf = np.zeros((int((dur + 0.01) * SR), 2))
    nb = int(np.ceil(dur / bar)) + 1
    k, h = kick(), None
    for b in range(nb):
        t0 = off + b * bar
        if t0 >= dur: break
        root, chord = PROG[b % len(PROG)]
        add(buf, pad_chord(chord, bar + 0.6), t0, 0.16)
        for i in range(4):
            tb = t0 + i * beat
            if tb >= dur: break
            # sparse first bar = intro; full groove afterwards
            if b > 0 or i >= 2: add(buf, k, tb, 0.42 if i % 2 == 0 else 0.28)
            if i in (0, 2): add(buf, bass(root - 12, beat * 0.9), tb, 0.22)
            if b > 0: add(buf, hat(rng), tb + beat / 2, 0.09, pan=0.3 * (1 if i % 2 else -1))
    cues = []
    for s in sb['scenes']:
        for c in s.get('audio_cues', []):
            cues.append({'t': float(c['t']), 'type': c['type'], 'gain': float(c.get('gain', 0.5)), 'scene': s['id']})
            add(buf, sfx(c['type'], rng), float(c['t']), 0.55 * float(c.get('gain', 0.5)))
    # master: gentle fade in/out, soft clip
    n = len(buf); fi, fo = int(0.25 * SR), int(0.7 * SR)
    buf[:fi] *= np.linspace(0, 1, fi)[:, None]; buf[n - fo:] *= np.linspace(1, 0, fo)[:, None]
    buf = np.tanh(buf * 1.2) / np.tanh(1.2)
    return buf[: int(dur * SR)], cues

def write_wav(path, buf):
    pcm = (np.clip(buf, -1, 1) * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

def loudnorm(src, dst, lufs, tp=-1.5):
    p = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(src), '-af', f'loudnorm=I={lufs}:TP={tp}:LRA=11:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True)
    m = json.loads(re.findall(r'\{[^{}]*"input_i"[^{}]*\}', p.stderr)[-1])
    af = (f"loudnorm=I={lufs}:TP={tp}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(src), '-af', af, '-ar', str(SR), str(dst)], check=True)
    return m

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project'); ap.add_argument('--out'); ap.add_argument('--lufs', type=float, default=None); ap.add_argument('--seed', type=int, default=7)
    a = ap.parse_args()
    proj = Path(a.project); out = Path(a.out) if a.out else proj / 'out'; out.mkdir(parents=True, exist_ok=True)
    sb = json.loads((proj / 'storyboard.json').read_text())
    lufs = a.lufs
    if lufs is None:
        task = proj / 'task.json'
        lufs = json.loads(task.read_text()).get('audio', {}).get('target_lufs', -14) if task.exists() else -14
    buf, cues = build(sb, a.seed)
    write_wav(out / 'music_raw.wav', buf)
    m = loudnorm(out / 'music_raw.wav', out / 'audio.wav', lufs)
    (out / 'audio_cues.json').write_text(json.dumps({'bpm': sb.get('bpm'), 'cues': cues}, ensure_ascii=False, indent=2))
    print(f"audio: {out/'audio.wav'}  (raw {float(m['input_i']):.1f} LUFS -> target {lufs}), {len(cues)} cues")

if __name__ == '__main__':
    sys.exit(main())
