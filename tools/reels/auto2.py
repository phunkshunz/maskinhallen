"""Automatisk reel v2.  python3 auto2.py <ut-mapp> <frö> [plastik|hardgroove]
Musik av BETONG-kitets ljud i två stilar, ett klipp per takt mellan maskinerna,
zoom-puls på varje kick, blixt vid nya avsnitt, och egna visualiseringsklipp."""
import subprocess, os, sys, io, json
import numpy as np
from scipy.io import wavfile
from scipy.signal import lfilter, butter, sosfilt, fftconvolve
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1]; SEED = int(sys.argv[2]); STYLE = sys.argv[3] if len(sys.argv) > 3 else ("plastik" if SEED % 2 else "hardgroove")
rng = np.random.default_rng(SEED)
SR = 48000; BPM = 128 if STYLE == "plastik" else 134
BEAT = 60 / BPM; BAR = 4 * BEAT; STEP = BEAT / 4; NB = 16; DUR = NB * BAR; N = int(DUR * SR) + 2 * SR
LIB = "/home/claude/betong-vsti/assets/library/"; VID = "/home/claude/maskinhallen/videos/"; SH = "/home/claude/maskinhallen/shots/"
UP = "/mnt/user-data/uploads/"
TMP = f"/tmp/claude-0/tt/a2_{SEED}"; os.makedirs(TMP, exist_ok=True); os.makedirs(OUT, exist_ok=True)

def load(name, rate=1.0):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", LIB + name + ".flac", "-ac", "1", "-ar", str(int(SR * rate)), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).copy()

def place(bus, smp, t, g=1.0, pitch=0.0, maxlen=None):
    if pitch:
        r = 2 ** (pitch / 12); idx = np.arange(0, len(smp) - 1, r); smp = np.interp(idx, np.arange(len(smp)), smp).astype(np.float32)
    if maxlen:
        n = min(len(smp), int(maxlen * SR)); smp = smp[:n] * np.minimum(1, np.linspace(n / 200, 0, n))
    i = int(t * SR); e = min(len(bus), i + len(smp))
    if 0 <= i < len(bus): bus[i:e] += smp[: e - i] * g

def delay(x, sec, fb, mix, lp=2500):
    d = int(sec * SR); y = x.copy(); sos = butter(1, lp, "low", fs=SR, output="sos")
    tap = np.zeros_like(x)
    for k in range(1, 7):
        sh = np.zeros_like(x); sh[d * k:] = x[: len(x) - d * k] * (fb ** k); tap += sh
    return y + sosfilt(sos, tap) * mix

def resonant(x, fc_curve, q=6.0):
    """Resonant lågpass (SVF) med svepande frekvens, kurva per sampel."""
    y = np.zeros_like(x); ic1 = ic2 = 0.0; k = 1.0 / q
    g = np.tan(np.pi * np.clip(fc_curve, 40, 16000) / SR)
    for i in range(0, len(x), 64):          # koefficienter var 64:e sampel
        gg = float(g[i]); a1 = 1 / (1 + gg * (gg + k)); a2 = gg * a1; a3 = gg * a2
        for j in range(i, min(i + 64, len(x))):
            v3 = x[j] - ic2; v1 = a1 * ic1 + a2 * v3; v2 = ic2 + a2 * ic1 + a3 * v3
            ic1 = 2 * v1 - ic1; ic2 = 2 * v2 - ic2; y[j] = v2
    return y

kick = np.zeros(N, np.float32); drums = np.zeros(N, np.float32); acid = np.zeros(N, np.float32)
low = np.zeros(N, np.float32); dub = np.zeros(N, np.float32); fx = np.zeros(N, np.float32)
SWING = 0.0 if STYLE == "plastik" else 0.16
def T(bar, st):
    return bar * BAR + st * STEP + (SWING * STEP if st % 2 else 0)

if STYLE == "plastik":
    S = {k: load(v) for k, v in dict(kick=rng.choice(["K26_Rund_Minimal", "K04_Minimal_Tight", "K10_Click_Thump"]), hat="H18_Closed_Tight",
         rim="C19_Rim_909", click="P09_Blip", acid=rng.choice(["B04_Acid_Soft_F", "B03_Acid_Squelch_F"]), sub="B20_Sub_Sine_F",
         stab="S01_Dub_Fm7_Dry", noise="X09_Glitch_Granular", crash="X04_Crash_Reverse").items()}
    line = [(0, 0), (3, 12), (6, 0), (8, 0), (10, 15), (11, 12), (14, 0)] if SEED % 3 else [(0, 0), (2, 0), (5, 12), (7, 0), (10, 3), (13, 0), (15, 10)]
    for bar in range(NB):
        brk = bar in (8, 9)
        for st in range(16):
            t = T(bar, st)
            if st % 4 == 0 and not brk: place(kick, S["kick"], t, 1.0)
            acc = [1, .3, .6, .3][st % 4] * (0.85 + 0.3 * rng.random())
            if bar >= 1: place(drums, S["hat"], t, 0.22 * acc, maxlen=0.05)
            if bar >= 2 and st in (7, 15) or (bar >= 6 and st == 10 and bar % 2): place(dub, S["rim"], t, 0.55)
            if bar >= 3 and st in (3, 9) and rng.random() < 0.6: place(drums, S["click"], t, 0.25, maxlen=0.06)
        if bar >= 4:
            for st, n in line: place(acid, S["acid"], T(bar, st), 0.5, pitch=n - 12, maxlen=STEP * 1.6)
        if bar % 2 == 0 and bar >= 2 and not brk: place(low, S["sub"], T(bar, 0), 0.45, maxlen=BAR * 0.9)
        if bar in (6, 10, 14): place(dub, S["stab"], T(bar, 6), 0.3)
    place(fx, S["crash"], T(9, 0), 0.5); place(fx, S["noise"], T(8, 8), 0.3)
    # acid-filtret: långsamt svep över åtta takter (det klassiska Plastikman-greppet)
    tt = np.arange(N) / SR
    sweep = 250 + 2600 * (0.5 - 0.5 * np.cos(2 * np.pi * tt / (8 * BAR))) ** 1.6
    acid = resonant(acid, sweep, q=7.5) * 1.4
    dub = delay(dub, 3 * STEP, 0.55, 0.8)
    acid = delay(acid, 3 * STEP, 0.35, 0.35)
else:
    r = 134 / 138
    S = {k: load(v) for k, v in dict(kick=rng.choice(["K25_Hardgroove_Tight", "K15_Hardgroove_909", "K23_Peak_Punch"]), tl="P43_Tom_909_Low",
         tm="P44_Tom_909_Mid", th="P45_Tom_909_High", cow="P46_Cowbell_808", rim="P22_Rim_Crack", clap="C01_Clap_909ish",
         ride="H16_Ride_Tech", oh="H15_Hat_Open_House", hat="H12_Hat_Tape_909", rum="B07_Rumble_Tone_F", crash="X03_Crash",
         riser="X13_Riser_Grind_138").items()}
    loop = load("Lp09_Hardgroove_Perc_138", rate=1 / r)   # samma tonhöjd, sträckt till 134
    toms = [("tl", 2), ("tm", 6), ("th", 9), ("tm", 11), ("tl", 14)] if SEED % 2 else [("th", 3), ("tm", 7), ("tl", 10), ("tm", 13), ("th", 15)]
    for bar in range(NB):
        brk = bar in (8, 9)
        for st in range(16):
            t = T(bar, st)
            if st % 4 == 0 and not brk: place(kick, S["kick"], t, 1.0)
            place(drums, S["hat"], t, (0.35 if st % 2 else 0.18) * (0.8 + 0.4 * rng.random()), maxlen=0.07)
            if bar >= 1 and st % 4 == 2: place(drums, S["oh"], t, 0.4, maxlen=0.2)
            if bar >= 2 and st in (4, 12): place(drums, S["clap"], t, 0.6)
            if bar >= 3 and st % 2 == 1 and not brk: place(low, S["rum"], t, 0.4, maxlen=STEP * 1.1)
            if bar >= 4 and st % 4 == 2: place(drums, S["ride"], t, 0.25, maxlen=0.3)
            if bar >= 6 and st in (3, 11, 14) and rng.random() < 0.85: place(dub, S["cow"], t, 0.3)
            if bar >= 6 and st in (6, 15): place(drums, S["rim"], t, 0.35)
        if bar >= 5 and not brk:
            for k, st in toms: place(drums, S[k], T(bar, st), 0.5 * (0.8 + 0.4 * rng.random()))
        if bar >= 4 and bar % 2 == 0:
            place(drums, loop, T(bar, 0), 0.35, maxlen=2 * BAR)
    place(fx, S["riser"], T(8, 0), 0.5, maxlen=2 * BAR); place(fx, S["crash"], T(10, 0), 0.55)
    dub = delay(dub, 3 * STEP, 0.4, 0.5)
    low = sosfilt(butter(2, 220, "low", fs=SR, output="sos"), low) * 1.6

# ---------- bildplan: 16 takter
CLIPS = {
    "BETONG": (VID + "betong.mp4", (420, 100, 1160, 760)), "KOLV": (VID + "kolv.mp4", (380, 80, 1200, 780)),
    "FRÄS": (VID + "fras.mp4", (20, 0, 1560, 880)), "SMUTS": (UP + "Skärminspelning_2026-11-07_kl__13_07_07.mov", (210, 10, 1900, 1583)),
    "KULVERT": (VID + "kulvert.mp4", (460, 80, 1100, 780)), "VENTIL": (UP + "Skärminspelning_2026-11-07_kl__13_10_24.mov", (500, 90, 1800, 1500)),
    "FUKT": (VID + "fukt.mp4", (480, 80, 1100, 780)), "SPÅN": (VID + "span.mp4", (420, 80, 1140, 760)), "GLAPP": (VID + "glapp.mp4", (100, 100, 1480, 760)),
}
STILLS = {"TURBIN": "turbin", "ARMERING": "armering", "SMIDET": "smidet", "FASFEL": "fasfel", "ALLANROP": "allanrop", "GRUND": "grund"}
INFO = {"BETONG": ("SAMPLER · FREE", "chops loops into techno"), "KOLV": ("DRUM MACHINE", "builds the track"), "FRÄS": ("FILTER", "cuts with shapes"),
        "SMUTS": ("LOOP MACHINE", "makes it dirty"), "KULVERT": ("ROOM", "tunnel under Stockholm"), "VENTIL": ("GROOVE EFFECT", "makes it breathe"),
        "FUKT": ("EFFECT", "rumble and grit"), "SPÅN": ("MICRO SAMPLER", "splinters of sound"), "GLAPP": ("MIDI GROOVE · FREE", "loose like a drummer"),
        "TURBIN": ("SYNTH", "dub chords that play themselves"), "ARMERING": ("SYNTH", "hypnotic bass lines"), "SMIDET": ("EUCLIDEAN SYNTH", "metal and blips"),
        "FASFEL": ("PERCUSSION", "microtonal knocks"), "ALLANROP": ("VOICE", "robot, vocoder, choir"), "GRUND": ("SUB BASS", "the floor")}
clipnames = list(CLIPS); rng.shuffle(clipnames); stillnames = list(STILLS); rng.shuffle(stillnames)
seq = ["VIS"]                      # takt 1: eget klipp, vågform
pool = []
for i in range(max(len(clipnames), len(stillnames))):
    if i < len(clipnames): pool.append(("clip", clipnames[i]))
    if i < len(stillnames) and i % 2 == 0: pool.append(("still", stillnames[i]))
body = pool[:13]
bars = [("vis", None)] + body[:7] + [("spec", None)] + body[7:13] + [("cta", None)]
bars = bars[:NB]

def duration(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f], capture_output=True, text=True).stdout)
def motion(f, crop, t0, t1):
    x, y, w, h = crop
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(t0), "-t", str(t1 - t0), "-i", f, "-vf",
                          f"crop={w}:{h}:{x}:{y},scale=96:72,format=gray,fps=30", "-f", "rawvideo", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 72, 96).astype(np.float32)
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2)) if len(fr) > 1 else np.zeros(1)
    global LAST_BRIGHT; LAST_BRIGHT = fr.mean(axis=(1, 2))
    return np.concatenate([[d[0] if len(d) else 0], d])
plan = []
for b, (kind, name) in enumerate(bars):
    p = {"bar": b, "kind": kind, "name": name, "motion": np.zeros(int(BAR * 30) + 2)}
    if kind == "clip":
        f, crop = CLIPS[name]; full = motion(f, crop, 0, duration(f)); win = int(BAR * 30)
        sc = np.convolve(full, np.ones(win), "valid") if len(full) > win else np.ones(1)
        # bara bitar där pluginfönstret syns (mörkt): ljusa bitar är Bitwigs arrangemangsvy
        br = LAST_BRIGHT
        if len(br) > win:
            ok = np.array([br[i:i + win].max() < 48 for i in range(len(sc))])
            if ok.any(): sc = np.where(ok, sc, -1)
        p.update(file=f, crop=crop, start=float(np.argmax(sc[: max(1, len(full) - win)])) / 30.0)
        p["motion"] = motion(f, crop, p["start"], p["start"] + BAR)
    plan.append(p)

# ---------- ljudet svarar på rattarna: filter på allt utom kicken, takt för takt
music = drums + acid + low + dub + fx
env = np.zeros(N, np.float32)
for p in plan:
    m = np.convolve(p["motion"], np.ones(5) / 5, "same"); m = m / (m.max() + 1e-6) if m.max() > 0 else m
    if p["kind"] == "still": m = 0.5 + 0.5 * np.sin(np.linspace(0, np.pi, len(m)))   # stillbild: mjukt svep
    seg = np.interp(np.arange(int(BAR * SR)) / SR * 30, np.arange(len(m)), m)
    i = int(p["bar"] * BAR * SR); n = max(0, min(len(seg), N - i)); env[i:i + n] = seg[:n]
fc = 1400 + 14600 * np.clip(env, 0, 1) ** 1.3
fc[: int(BAR * SR)] = np.linspace(300, 16000, int(BAR * SR))       # intro öppnar upp
fc[int(15 * BAR * SR):] = 16000
music_f = resonant(music.astype(np.float64), fc, q=1.2).astype(np.float32)
kenv = np.convolve(np.abs(kick), np.ones(500) / 500, "same"); kenv /= kenv.max() + 1e-9
mix = kick * 1.1 + music_f * (1 - 0.5 * kenv)
mix = sosfilt(butter(1, 28, "high", fs=SR, output="sos"), mix)
mix = np.tanh(mix * 1.5) / 1.15
mix = mix[: int(DUR * SR)]
mix *= np.minimum(1, (len(mix) - np.arange(len(mix))) / (0.6 * SR))
wavfile.write(f"{TMP}/musik.wav", SR, np.stack([mix, mix], 1).astype(np.float32))

# ---------- grafik
W, H = 1080, 1920; VY, VH = 150, 1180
ORANGE = (245, 166, 35); WHITE = (240, 238, 232); GREY = (150, 150, 150); BG = (20, 20, 20); TAPE = (242, 181, 29)
Fd = "/usr/share/fonts/opentype/inter/"
fBig = ImageFont.truetype(Fd + "Inter-ExtraBold.otf", 124); fSub = ImageFont.truetype(Fd + "Inter-SemiBold.otf", 40)
fMono = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 26)
fUrl = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 34)
logo = Image.open("/home/claude/maskinhallen/brand/logo-marke.png").convert("RGBA")
def spaced(d, xy, text, font, fill, sp=6):
    x, y = xy
    for ch in text: d.text((x, y), ch, font=font, fill=fill); x += d.textlength(ch, font=font) + sp
def overlay(path, label, big, sub, url=None, bigcol=WHITE):
    im = Image.new("RGBA", (W, H), BG + (255,)); d = ImageDraw.Draw(im)
    d.rectangle([0, VY, W, VY + VH], fill=(0, 0, 0, 0))
    for x in range(-60, W + 60, 56): d.polygon([(x, 0), (x + 28, 0), (x + 4, 26), (x - 24, 26)], fill=TAPE)
    spaced(d, (60, 82), "MASKINHALLEN", fMono, ORANGE); t = "PHUNKSHUNZ AUDIO"; spaced(d, (W - 60 - 24 * len(t), 82), t, fMono, GREY)
    y = VY + VH + 36
    spaced(d, (60, y), label, fMono, GREY, 5); y += 44
    d.text((56, y), big, font=fBig, fill=bigcol); y += 150
    d.text((60, y), sub, font=fSub, fill=ORANGE)
    if url:
        tw = d.textlength(url, font=fUrl); y += 64
        d.rounded_rectangle([60, y, 60 + tw + 48, y + 62], radius=10, outline=ORANGE, width=3); d.text((84, y + 12), url, font=fUrl, fill=WHITE)
    im.alpha_composite(logo.resize((64, 64)), (W - 60 - 64, VY + VH - 64 - 24))
    im.save(path)

def run3(cmd):
    import json as _j; open("/tmp/claude-0/tt/lastcmd.json","w").write(_j.dumps(cmd))
    for k in range(3):
        if subprocess.run(cmd).returncode == 0: return
    raise RuntimeError("ffmpeg misslyckades: " + cmd[-1])
import gc
for _n in ("kick", "drums", "acid", "low", "dub", "fx", "music", "music_f", "env", "fc", "kenv"):
    globals().pop(_n, None)
gc.collect()
punch = f"1.0+0.045*exp(-mod(on/30\\,{BEAT:.5f})*13)"
def phase_for(p):
    if p["kind"] == "vis": return ("PHUNKSHUNZ AUDIO PRESENTS", "13 machines.", "MASKINHALLEN · techno tools from Stockholm")
    if p["kind"] == "spec": return ("BUILT FROM SCRATCH", "Pure techno.", "Mac · Windows · Linux · VST3 · AU")
    if p["kind"] == "cta": return ("ALL 13 MACHINES", "€89.", "Or €20 each · free demo of every one", "phunkshunz.github.io/maskinhallen")
    lab, tag = INFO[p["name"]]; return (lab, p["name"], tag)
plan = [p for p in plan]
# sista takten blir alltid CTA
if plan[-1]["kind"] != "cta": plan.append({"bar": len(plan), "kind": "cta", "name": None})
segs = []
for p in plan:
    b = p["bar"]; t0 = b * BAR; seglen = BAR if p["kind"] != "cta" else DUR - t0
    args = phase_for(p); ov = f"{TMP}/ov{b}.png"; overlay(ov, *args, bigcol=ORANGE if args[1] in ("€89.", "13 machines.") else WHITE)
    tail_v = f"zoompan=z='{punch}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x{VH}:fps=30,setsar=1,trim=duration={seglen:.4f},setpts=PTS-STARTPTS"
    if p["kind"] == "clip":
        x, y, w, h = p["crop"]; inp = ["-ss", f"{p['start']:.3f}", "-t", f"{seglen + 0.3:.3f}", "-i", p["file"]]
        v = f"[0:v]fps=30,crop={w}:{h}:{x}:{y},scale=-2:{int(VH * 1.12)},crop={int(1080 * 1.12)}:{int(VH * 1.12)}:'(iw-ow)*t/{BAR:.3f}':0,{tail_v}[hole]"
    elif p["kind"] == "still":
        inp = ["-loop", "1", "-t", f"{seglen + 0.3:.3f}", "-i", SH + STILLS[p["name"]] + ".webp"]
        v = f"[0:v]fps=30,scale=-2:{int(VH * 1.12)},crop={int(1080 * 1.12)}:{int(VH * 1.12)}:'(iw-ow)*t/{BAR:.3f}':0,{tail_v}[hole]"
    else:
        ss = t0 if t0 + seglen + 0.5 < DUR else max(0.0, DUR - seglen - 2.5)   # vid filens slut fastnar ffmpeg, ta vågformen lite tidigare
        inp = ["-ss", f"{ss:.4f}", "-t", f"{seglen + 0.2:.3f}", "-i", f"{TMP}/musik.wav"]
        g = (f"showfreqs=s=1080x{VH}:mode=bar:ascale=sqrt:fscale=log:colors=0xF5A623:win_size=2048" if p["kind"] == "spec"
             else f"showwaves=s=1080x{VH}:mode=cline:scale=sqrt:colors=0xF5A623:draw=full")
        v = f"[0:a]aformat=channel_layouts=mono,{g},fps=30,format=rgba,setsar=1,trim=duration={seglen:.4f},setpts=PTS-STARTPTS[hole]"
    fl = [v, f"color=c=0x141414:s={W}x{H}:r=30:d={seglen:.4f}[bg]", f"[bg][hole]overlay=0:{VY}:shortest=1[a]", "[a][1:v]overlay=0:0[b]"]
    if b in (4, 8, 12): fl.append(f"[b]drawbox=x=0:y={VY}:w=1080:h={VH}:color=white@0.85:t=fill:enable='lt(t,0.07)'[c]"); outl = "[c]"
    else: outl = "[b]"
    fn = f"{TMP}/seg{b:02d}.mp4"
    run3(["ffmpeg", "-loglevel", "error", "-y"] + inp + ["-i", ov, "-filter_complex", ";".join(fl), "-map", outl, "-t", f"{seglen:.4f}",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30", "-an", fn])
    segs.append(fn)
open(f"{TMP}/list.txt", "w").write("".join(f"file '{f}'\n" for f in segs))
name = f"reel-{STYLE}-{SEED}"
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{TMP}/list.txt", "-i", f"{TMP}/musik.wav",
                "-filter_complex", "[1:a]loudnorm=I=-11:TP=-1.0:LRA=8[aout]", "-map", "0:v", "-map", "[aout]", "-t", f"{DUR:.3f}",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", f"{OUT}/{name}.mp4"], check=True)
print("klar", name, STYLE, f"{BPM} BPM", f"{DUR:.1f} s", [p["name"] or p["kind"] for p in plan])
