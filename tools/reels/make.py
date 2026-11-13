"""TikTok-videor 1080x1920 i samma stil som MASKINHALLEN-reelen."""
import subprocess, os, sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
ORANGE = (245, 166, 35); WHITE = (240, 238, 232); GREY = (150, 150, 150); BG = (20, 20, 20); TAPE = (242, 181, 29)
F = "/usr/share/fonts/opentype/inter/"
fBig = ImageFont.truetype(F + "Inter-ExtraBold.otf", 118)
fSub = ImageFont.truetype(F + "Inter-SemiBold.otf", 40)
fMono = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 26)
fUrl = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 34)
fLogo = ImageFont.truetype(F + "Inter-ExtraBold.otf", 40)
logo = Image.open("/home/claude/maskinhallen/brand/logo-marke.png").convert("RGBA")
OUT = sys.argv[1]
VY, VH = 150, 900   # videons plats

def spaced(d, xy, text, font, fill, sp=6):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + sp

def overlay(path, label, l1, l2, sub, url=None, code=None):
    im = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(im)
    # hål för videon
    d.rectangle([0, VY, W, VY + VH], fill=(0, 0, 0, 0))
    # varningstejp
    for x in range(-60, W + 60, 56):
        d.polygon([(x, 0), (x + 28, 0), (x + 4, 26), (x - 24, 26)], fill=TAPE)
    spaced(d, (60, 82), "MASKINHALLEN", fMono, ORANGE)
    t = "PHUNKSHUNZ AUDIO"; spaced(d, (W - 60 - 18 * len(t) - 6 * len(t), 82), t, fMono, GREY)
    # nedre panel
    y = VY + VH + 50
    spaced(d, (60, y), label, fMono, GREY, 5)
    y += 56
    d.text((56, y), l1, font=fBig, fill=WHITE)
    y += 132
    d.text((56, y), l2, font=fBig, fill=ORANGE)
    y += 160
    d.text((60, y), sub, font=fSub, fill=(205, 200, 190))
    y += 70
    if url:
        tw = d.textlength(url, font=fUrl)
        d.rounded_rectangle([60, y, 60 + tw + 48, y + 66], radius=10, outline=ORANGE, width=3)
        d.text((84, y + 14), url, font=fUrl, fill=WHITE)
        y += 86
    if code:
        d.text((60, y), code, font=fSub, fill=ORANGE)
    # logga uppe i videon, liten
    lg = logo.resize((64, 64))
    im.alpha_composite(lg, (W - 60 - 64, VY + VH - 64 - 24))
    im.save(path)

def build(name, segs, phases, total):
    os.makedirs(OUT, exist_ok=True)
    tmp = f"/tmp/claude-0/tt/{name}"
    os.makedirs(tmp, exist_ok=True)
    ins, fl = [], []
    for i, (f, ss, du) in enumerate(segs):
        ins += ["-ss", str(ss), "-t", str(du), "-i", f"/home/claude/maskinhallen/videos/{f}.mp4"]
        # beskär mitten, skala till 1080 bred, lite långsam inzoomning
        fl.append(f"[{i}:v]crop=1100:894:250:0,scale=1080:{VH}:force_original_aspect_ratio=increase,crop=1080:{VH},"
                  f"zoompan=z='min(1+0.0009*on,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x{VH}:fps=30,setsar=1[v{i}]")
        fl.append(f"[{i}:a]aresample=48000,afade=t=in:d=0.02,afade=t=out:st={du-0.03}:d=0.03[a{i}]")
    n = len(segs)
    fl.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac]")
    base = len(segs)
    ov_in = []
    for j, (t0, t1, args) in enumerate(phases):
        p = f"{tmp}/ov{j}.png"; overlay(p, *args); ov_in += ["-loop", "1", "-t", str(total), "-i", p]
    fl.append(f"color=c=0x141414:s={W}x{H}:r=30:d={total}[bg]")
    fl.append(f"[bg][vc]overlay=0:{VY}:shortest=1[b0]")
    last = "b0"
    for j, (t0, t1, _) in enumerate(phases):
        fl.append(f"[{last}][{base + j}:v]overlay=0:0:enable='between(t,{t0},{t1})'[b{j+1}]")
        last = f"b{j+1}"
    fl.append(f"[ac]loudnorm=I=-14:TP=-1.0:LRA=11,afade=t=out:st={total-0.6}:d=0.6[aout]")
    cmd = ["ffmpeg", "-loglevel", "error", "-y"] + ins + ov_in + ["-filter_complex", ";".join(fl), "-map", f"[{last}]", "-map", "[aout]",
           "-t", str(total), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", f"{OUT}/{name}.mp4"]
    subprocess.run(cmd, check=True)
    print("klar", name)

URL = "phunkshunz.github.io/maskinhallen"
V = {
 "1-hela-hallen": (
   [("fras", 10, 4.0), ("kolv", 8, 4.0), ("fukt", 3, 4.0), ("kulvert", 10, 3.6)], 15.6,
   [(0, 5.2, ("THE WHOLE HALL", "All 13", "machines. €89.", "Or €20 each · free updates for life")),
    (5.2, 10.4, ("STOCKHOLM TECHNO MACHINES", "Mac. Windows.", "Linux.", "VST3 · AU · standalone")),
    (10.4, 16, ("FREE DEMO OF EVERY MACHINE", "Try first.", "Then buy.", "BETONG + GLAPP are free", URL))]),
 "2-betong-gratis": (
   [("betong", 0, 15.0)], 15.0,
   [(0, 5, ("FREE TECHNO SAMPLER", "Chop any loop", "into techno.", "BETONG · full version · free")),
    (5, 10, ("8 TRACKS · 16 PADS · MIDI OUT", "Skewed. Drunk.", "Polyrhythmic.", "Micro-timing like a real drummer")),
    (10, 16, ("BETONG · MAC · WIN · LINUX", "Free.", "No email.", "Download it today", URL))]),
 "3-fras": (
   [("fras", 4, 15.0)], 15.0,
   [(0, 5, ("FRÄS · GEOMETRIC FILTER", "Shapes cut", "your beat.", "Every corner of the shape is a hit")),
    (5, 10, ("4 SHAPES · TEMPO SYNCED", "Funk from", "geometry.", "Stutter · tape stop · comb · freeze")),
    (10, 16, ("FREE DEMO · FULL €20", "Try the", "free demo.", "Or all 13 machines for €89", URL))]),
 "4-kolv": (
   [("kolv", 2, 15.0)], 15.0,
   [(0, 5, ("KOLV · TECHNO TRACK BUILDER", "Press play.", "It builds.", "Kick, hats, bass and stabs grow in")),
    (5, 10, ("NO LOOPS · IT EVOLVES", "Not a loop.", "A whole track.", "Lock the lanes you love")),
    (10, 16, ("FREE DEMO · FULL €20", "Try the", "free demo.", "Or all 13 machines for €89", URL))]),
 "5-kulvert": (
   [("kulvert", 6, 15.0)], 15.0,
   [(0, 5, ("KULVERT · BASEMENT ROOM", "Your loop,", "in a basement.", "A concrete tunnel under Stockholm")),
    (5, 10, ("TUNNEL · PIPES · CONDENSATION", "Dark. Wet.", "Wide.", "Built for techno, not for ballads")),
    (10, 16, ("FREE DEMO · FULL €20", "Try the", "free demo.", "Or all 13 machines for €89", URL))]),
}
which = sys.argv[2:] or list(V)
for k in which:
    segs, total, ph = V[k]
    build(k, segs, ph, total)
