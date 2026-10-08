"""Render DIN Instagram headline cards (1080x1080 PNG) and optional video cards.

Usage: python3 -I make_card.py cards.json OUTPUT_DIR
cards.json: list of {"id","category","headline","source","theme": "dark"|"light","video": bool}
"""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
BRAND = os.path.join(HERE, "brand")
FONTS = "/usr/share/fonts/truetype/google-fonts/"
S = 1080
M = 84

THEMES = {
    "dark": dict(bg=(0, 0, 0), text=(245, 245, 246), muted=(176, 176, 182),
                 accent=(196, 140, 92), logo="04fa17c4-image.png"),
    "light": dict(bg=(254, 254, 254), text=(28, 28, 31), muted=(98, 98, 104),
                  accent=(160, 104, 63), logo="63309a14-image.png"),
}


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, f"Poppins-{name}.ttf"), size)


def wrap(draw, text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=f) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def spaced(draw, xy, text, f, fill, tracking):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill)
        x += draw.textlength(ch, font=f) + tracking
    return x


def card(spec, top=0):
    """Draw a card. `top` reserves space at the top (for the video header)."""
    t = THEMES[spec.get("theme", "dark")]
    im = Image.new("RGB", (S, S), t["bg"])
    if spec.get("theme", "dark") == "dark" and top == 0:
        glow = Image.new("RGB", (S, S), t["bg"])
        ImageDraw.Draw(glow).ellipse((560, -380, 1460, 420), fill=(58, 38, 22))
        im = glow.filter(ImageFilter.GaussianBlur(170))
    d = ImageDraw.Draw(im)

    # Category label with accent rule
    y = top + (M if top == 0 else 44)
    d.rectangle((M, y + 17, M + 44, y + 20), fill=t["accent"])
    spaced(d, (M + 62, y), spec["category"].upper(), font("Medium", 26), t["accent"], 5)

    # Headline: shrink until it fits, then centre the block in the open space
    logo_h = 140
    region_top, region_bot = y + 70, S - (M + logo_h + 40)
    avail = region_bot - region_top - 110  # room for divider + source line
    for size in range(84, 40, -2):
        hf = font("Bold", size)
        lines = wrap(d, spec["headline"], hf, S - 2 * M)
        lh = int(size * 1.18)
        if len(lines) * lh <= avail:
            break
    block = len(lines) * lh + 110
    hy = region_top if top else region_top + max(0, (region_bot - region_top - block) // 2)
    for ln in lines:
        d.text((M, hy), ln, font=hf, fill=t["text"])
        hy += lh

    # Accent divider and source line
    hy += 26
    d.rectangle((M, hy, M + 90, hy + 4), fill=t["accent"])
    d.text((M, hy + 26), f"Source: {spec['source']}", font=font("Regular", 30), fill=t["muted"])

    # Footer: banner logo + call to action
    logo = Image.open(os.path.join(BRAND, t["logo"])).convert("RGBA")
    logo = logo.crop((0, 0, logo.width, logo.height - 4))  # drop stray edge line
    lw = 520
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    ly = S - M - logo.height + 10
    im.paste(logo, (M - 18, ly), logo)
    cta = "dualincomenetwork.com"
    cf = font("Medium", 27)
    d.text((S - M - d.textlength(cta, font=cf), ly + logo.height // 2 - 18), cta, font=cf, fill=t["accent"])
    return im


def video_card(spec, out_dir):
    """Square video: DIN logo animation on top, headline card below (6 s)."""
    vh = 540
    base = card(dict(spec, theme="dark"), top=vh)
    base_path = os.path.join(out_dir, f"{spec['id']}_base.png")
    base.save(base_path)
    out = os.path.join(out_dir, f"{spec['id']}.mp4")
    # Full-width logo animation (1080x608), trimmed to the header height
    filt = (f"[1:v]scale={S}:-2,crop={S}:{vh}:0:20[v];"
            f"[0:v][v]overlay=0:0,format=yuv420p[o]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", base_path,
                    "-i", os.path.join(BRAND, "logo.mp4"), "-filter_complex", filt,
                    "-map", "[o]", "-map", "1:a?", "-t", "6", "-r", "30",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-c:a", "aac", "-shortest", out], check=True)
    os.remove(base_path)
    return out


if __name__ == "__main__":
    specs = json.load(open(sys.argv[1]))
    out_dir = sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    for s in specs:
        card(s).save(os.path.join(out_dir, f"{s['id']}.png"), optimize=True)
        if s.get("video"):
            video_card(s, out_dir)
        print("rendered", s["id"])
