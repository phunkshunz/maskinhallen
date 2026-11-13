"""Reels 1080x1920 från egna skärminspelningar: en sammanhängande tagning (grooven bryts inte),
bilden växlar mellan hela fönstret och närbilder."""
import subprocess, os, sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
ORANGE = (245, 166, 35); WHITE = (240, 238, 232); GREY = (150, 150, 150); BG = (20, 20, 20); TAPE = (242, 181, 29)
F = "/usr/share/fonts/opentype/inter/"
fBig = ImageFont.truetype(F + "Inter-ExtraBold.otf", 118)
fSub = ImageFont.truetype(F + "Inter-SemiBold.otf", 40)
fMono = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 26)
fUrl = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 34)
logo = Image.open("/home/claude/maskinhallen/brand/logo-marke.png").convert("RGBA")
OUT = sys.argv[1]
VY, VH = 150, 900

def spaced(d, xy, text, font, fill, sp=6):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill); x += d.textlength(ch, font=font) + sp

def overlay(path, label, l1, l2, sub, url=None, code=None):
    im = Image.new("RGBA", (W, H), BG + (255,)); d = ImageDraw.Draw(im)
    d.rectangle([0, VY, W, VY + VH], fill=(0, 0, 0, 0))
    for x in range(-60, W + 60, 56): d.polygon([(x, 0), (x + 28, 0), (x + 4, 26), (x - 24, 26)], fill=TAPE)
    spaced(d, (60, 82), "MASKINHALLEN", fMono, ORANGE)
    t = "PHUNKSHUNZ AUDIO"; spaced(d, (W - 60 - 24 * len(t), 82), t, fMono, GREY)
    y = VY + VH + 50
    spaced(d, (60, y), label, fMono, GREY, 5); y += 56
    d.text((56, y), l1, font=fBig, fill=WHITE); y += 132
    d.text((56, y), l2, font=fBig, fill=ORANGE); y += 160
    d.text((60, y), sub, font=fSub, fill=(205, 200, 190)); y += 70
    if url:
        tw = d.textlength(url, font=fUrl)
        d.rounded_rectangle([60, y, 60 + tw + 48, y + 66], radius=10, outline=ORANGE, width=3)
        d.text((84, y + 14), url, font=fUrl, fill=WHITE); y += 86
    if code: d.text((60, y), code, font=fSub, fill=ORANGE)
    im.alpha_composite(logo.resize((64, 64)), (W - 60 - 64, VY + VH - 64 - 24))
    im.save(path)

def build(name, src, start, total, shots, phases):
    tmp = f"/tmp/claude-0/tt/{name}"; os.makedirs(tmp, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    fl = [f"[0:v]fps=30,split={len(shots)}" + "".join(f"[s{i}]" for i in range(len(shots)))]
    for i, (t0, t1, (x, y, w, h)) in enumerate(shots):
        # närbild: långsam inzoomning, mjuk start
        fl.append(f"[s{i}]trim={t0}:{t1},setpts=PTS-STARTPTS,crop={w}:{h}:{x}:{y},scale=1296:1080,"
                  f"zoompan=z='min(1+0.0006*on,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x{VH}:fps=30,setsar=1[c{i}]")
    fl.append("".join(f"[c{i}]" for i in range(len(shots))) + f"concat=n={len(shots)}:v=1:a=0[vc]")
    ov = []
    for j, (t0, t1, args) in enumerate(phases):
        p = f"{tmp}/ov{j}.png"; overlay(p, *args); ov += ["-loop", "1", "-t", str(total), "-i", p]
    fl.append(f"color=c=0x141414:s={W}x{H}:r=30:d={total}[bg]")
    fl.append(f"[bg][vc]overlay=0:{VY}:shortest=1[b0]")
    last = "b0"
    for j, (t0, t1, _) in enumerate(phases):
        fl.append(f"[{last}][{j + 1}:v]overlay=0:0:enable='between(t,{t0},{t1})'[b{j+1}]"); last = f"b{j+1}"
    fl.append(f"[0:a]aresample=48000,afade=t=in:d=0.4,loudnorm=I=-14:TP=-1.0:LRA=11,afade=t=out:st={total-1.2}:d=1.2[aout]")
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-ss", str(start), "-t", str(total), "-i", src] + ov + [
        "-filter_complex", ";".join(fl), "-map", f"[{last}]", "-map", "[aout]", "-t", str(total),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", f"{OUT}/{name}.mp4"]
    subprocess.run(cmd, check=True); print("klar", name)

URL = "phunkshunz.github.io/maskinhallen"
CTA = ("FREE DEMO · FULL VERSION €20", "Try the", "free demo.", "Or all 13 machines for €89", URL)
A = "/mnt/user-data/uploads/Skärminspelning_2026-11-07_kl__13_07_07.mov"
B = "/mnt/user-data/uploads/Skärminspelning_2026-11-07_kl__13_10_24.mov"
FULL_S, BEAT_S, MAKRO_S = (210, 10, 1900, 1583), (220, 210, 1300, 1083), (220, 770, 900, 750)
FULL_V, DIAL_V, LEFT_V = (500, 90, 1800, 1500), (990, 185, 900, 750), (560, 300, 780, 650)
JOBS = {
  "reel-smuts": (A, 75, 30, [(0, 7, FULL_S), (7, 14, BEAT_S), (14, 21, MAKRO_S), (21, 25, FULL_S), (25, 30, BEAT_S)],
    [(0, 7.5, ("SMUTS · LOOP MACHINE", "Drop 4 loops.", "Get techno.", "It chops, shuffles and rebuilds them")),
     (7.5, 15, ("KICK · SNARE · HAT · PERC · TONE · TEXTURE", "6 tracks.", "Endless beats.", "Sliced from your own loops")),
     (15, 22.5, ("MACROS: SMUTS · SLÄP · STÖK · KROSS", "Make it", "dirty.", "Four big knobs, one dirty groove")),
     (22.5, 31, CTA)]),
  "reel-ventil": (B, 15, 30, [(0, 7, FULL_V), (7, 14, DIAL_V), (14, 21, LEFT_V), (21, 25, FULL_V), (25, 30, DIAL_V)],
    [(0, 7.5, ("VENTIL · GROOVE EFFECT", "Your loop", "breathes.", "Swing, breath and throws on any audio")),
     (7.5, 15, ("ONE BIG VALVE", "Open it.", "Feel it swing.", "Swing · breath · throw · room · loop")),
     (15, 22.5, ("MASKINHALLEN · STOCKHOLM", "Named after", "machine rooms.", "Every machine is named after real parts")),
     (22.5, 31, CTA)]),
}
for k in (sys.argv[2:] or list(JOBS)):
    build(k, *JOBS[k])
