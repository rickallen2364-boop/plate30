"""Opening greeting card video (phone, 9:16, about 20 seconds).

Story: an envelope with a wax seal -> the flap opens -> the card slides out and fills the screen ->
the painted front glows with falling snow -> the card swings open -> the greeting inside.
Usage:  python card_open.py door_card
Writes: work/cards/<name>_open.mp4
"""
import cv2, numpy as np, subprocess, sys, math, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from card_loop import CARDS, W, H, FPS, FONT_DIR, OUT, prepare, front_frame, render_snow, TINT

DUR = 20.0
# envelope (portrait) and the card while it is inside it, in screen pixels
EW, EH, EX, EY = 720, 1080, 180, 800
CW, CH = 560, 996
CX, CY0, CY1 = 260, 854, 80          # card left, start top (hidden), top after sliding out
# timeline in seconds
FADE_IN, FLAP, RISE, ZOOM, OPEN, TXT, FADE_OUT = (0, .5), (1.0, 2.0), (2.0, 3.6), (3.6, 4.8), (11.0, 12.4), (12.6, 13.8), (19.4, 20.0)


def ease(t, a, b):
    u = min(max((t - a) / (b - a), 0), 1)
    return u * u * (3 - 2 * u)


def paper(w, h, base, seed, grain=0.035):
    """Cream paper with soft fibres and darker edges, float BGR."""
    rng = np.random.default_rng(seed)
    n = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), 1.2) * grain
    n += cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), 25) * grain * 1.5
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    edge = 1 - 0.10 * (((xx / w - .5) * 2) ** 4 + ((yy / h - .5) * 2) ** 4)
    rgb = np.array(base[::-1], np.float32) / 255
    return np.clip(rgb * (edge + n)[..., None], 0, 1)


def over(dst, src, alpha, x, y):
    """Paste float BGR `src` with float mask `alpha` onto dst at (x, y), clipped to the screen."""
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x1 <= x0 or y1 <= y0:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    a = alpha[y0 - y:y1 - y, x0 - x:x1 - x][..., None]
    dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - a) + s * a


def poly_mask(w, h, pts, blur=1.0):
    m = np.zeros((h, w), np.float32)
    cv2.fillPoly(m, [np.array(pts, np.int32)], 1.0, cv2.LINE_AA)
    return cv2.GaussianBlur(m, (0, 0), blur) if blur else m


def make_seal():
    """Deep red wax seal with MJ, as (BGR, alpha), 150 x 150."""
    S = 150
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = [(S / 2 + (66 + 5 * math.sin(k * 2.3)) * math.cos(k * math.pi / 14),
            S / 2 + (66 + 5 * math.sin(k * 2.3)) * math.sin(k * math.pi / 14)) for k in range(28)]
    d.polygon(pts, fill=(118, 22, 26, 255))
    d.ellipse((24, 24, S - 24, S - 24), fill=(140, 30, 34, 255), outline=(95, 15, 20, 255), width=4)
    f = ImageFont.truetype(FONT_DIR + 'cormorant-garamond-latin-600-italic.woff', 64)
    d.text((S / 2 + 1, S / 2 + 3), 'MJ', font=f, anchor='mm', fill=(80, 10, 14, 255))
    d.text((S / 2 - 1, S / 2), 'MJ', font=f, anchor='mm', fill=(196, 92, 80, 255))
    im = im.filter(ImageFilter.GaussianBlur(0.6))
    a = np.asarray(im).astype(np.float32) / 255
    return a[..., 2::-1].copy(), a[..., 3].copy()


def inside_page(c):
    """Cream inside page with the greeting; returns (paper BGR, text BGR, text alpha, inset box)."""
    pg = paper(W, H, (236, 226, 204), 5)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(FONT_DIR + 'cormorant-garamond-latin-600-italic.woff', 132)
    f2 = ImageFont.truetype(FONT_DIR + 'cormorant-garamond-latin-500-normal.woff', 56)
    f3 = ImageFont.truetype(FONT_DIR + 'cormorant-garamond-latin-500-italic.woff', 32)
    brown, soft = (74, 46, 28, 255), (110, 82, 58, 255)
    d.text((W / 2, 1330), c['title'], font=f1, anchor='mm', fill=brown)
    d.line((W / 2 - 150, 1425, W / 2 + 150, 1425), fill=(176, 138, 76, 255), width=3)
    d.text((W / 2, 1500), c['line2'], font=f2, anchor='mm', fill=soft)
    d.text((W / 2, 1850), 'MidnightJoeArt', font=f3, anchor='mm', fill=(140, 115, 90, 200))
    a = np.asarray(im).astype(np.float32) / 255
    inset = (140, 170, 800, 1000)        # x, y, w, h of the small live painting on the inside page
    x, y, w, h = inset
    shadow = np.zeros((H, W), np.float32)
    shadow[y + 14:y + h + 14, x + 8:x + w + 8] = 1
    pg *= (1 - 0.35 * cv2.GaussianBlur(shadow, (0, 0), 14))[..., None]
    return pg, a[..., 2::-1].copy(), a[..., 3:4].copy(), inset


def build(name):
    P = prepare(name)
    c = P['c']
    # background: the painting, blurred and darkened, with a vignette
    bg = cv2.GaussianBlur(P['f'], (0, 0), 28) * 0.38
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    bg *= (1 - 0.55 * np.clip(((xx / W - .5) ** 2 + (yy / H - .5) ** 2) * 2.4, 0, 1))[..., None]
    # envelope parts (local coordinates)
    env_back = paper(EW, EH, (186, 172, 148), 1)
    pocket = paper(EW, EH, (230, 219, 196), 2)
    pocket_a = poly_mask(EW, EH, [(0, .18 * EH), (EW / 2, .56 * EH), (EW, .18 * EH), (EW, EH), (0, EH)])
    pocket *= (1 - 0.22 * cv2.GaussianBlur(1 - pocket_a, (0, 0), 10) * pocket_a)[..., None]   # soft shadow under the flap edge
    flap_out = paper(EW, EH, (238, 228, 206), 3)
    flap_in = paper(EW, EH, (200, 186, 160), 4)
    seal, seal_a = make_seal()
    full_a = np.ones((EH, EW), np.float32)
    pg, txt, txt_a, inset = inside_page(c)
    ix, iy, iw, ih = inset
    os.makedirs(OUT, exist_ok=True)
    out = OUT + name + '_open.mp4'
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}',
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p',
           '-tag:v', 'avc1', '-movflags', '+faststart', out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        t = i / FPS
        if t < OPEN[0]:
            front = front_frame(P, t, snow=t >= ZOOM[0])
        if t < ZOOM[1]:
            fr = bg.copy()
            drop = int(ease(t, ZOOM[0], ZOOM[0] + 0.6) * 1400)       # envelope falls away early in the zoom
            ex, ey = EX, EY + drop
            over(fr, env_back, full_a, ex, ey)
            q = math.cos(math.pi * ease(t, *FLAP))                # 1 = flap closed, -1 = fully open
            tip = .56 * EH * q
            sq = .18 * EH * abs(q)
            flap_a = poly_mask(EW, int(.6 * EH), [(0, 0), (EW, 0), (EW, sq), (EW / 2, abs(tip)), (0, sq)])
            if q < 0:                                              # open flap sits behind the card
                fa = np.flipud(flap_a)
                over(fr, flap_in[:fa.shape[0]] * 0.92, fa, ex, ey - fa.shape[0])
            z = ease(t, *ZOOM)
            cy = CY0 + (CY1 - CY0) * ease(t, *RISE)
            x0, y0 = CX + (0 - CX) * z, cy + (0 - cy) * z
            w_, h_ = CW + (W - CW) * z, CH + (H - CH) * z
            card = cv2.resize(front, (int(w_), int(h_)), interpolation=cv2.INTER_AREA)
            sh = np.zeros((H, W), np.float32)
            sh[int(y0) + 16:int(y0 + h_) + 16, int(x0) + 10:int(x0 + w_) + 10] = 0.6 * (1 - z)
            fr *= (1 - cv2.GaussianBlur(sh, (0, 0), 18))[..., None]
            if t < ZOOM[0]:                                        # card is still inside the envelope
                over(fr, card, np.ones(card.shape[:2], np.float32), int(x0), int(y0))
                over(fr, pocket, pocket_a, ex, ey)
            else:
                over(fr, pocket, pocket_a, ex, ey)
                over(fr, card, np.ones(card.shape[:2], np.float32), int(x0), int(y0))
            if q >= 0:                                             # closed flap in front, with the seal
                over(fr, flap_out[:flap_a.shape[0]], flap_a, ex, ey)
                if q > 0.15:
                    over(fr, seal, seal_a, ex + EW // 2 - 75, ey + int(tip) - 95)
            if t < ZOOM[0]:                                        # a little snow drifting past the envelope
                fr = 1 - (1 - fr) * (1 - 0.6 * render_snow(P['snow'], t)[..., None] * TINT)
        elif t < OPEN[0]:
            fr = front
        else:
            th = math.pi * ease(t, *OPEN)                          # cover swings open on its left edge
            live = front_frame(P, t, snow=False)
            fr = pg.copy()
            fr[iy:iy + ih, ix:ix + iw] = cv2.resize(live[0:int(W * ih / iw)], (iw, ih), interpolation=cv2.INTER_AREA)
            ta = txt_a * ease(t, *TXT)
            fr = fr * (1 - ta) + txt * ta
            if th < math.pi / 2:
                fr *= 1 - 0.45 * math.sin(th)
                rx, grow = W * math.cos(th), 160 * math.sin(th)
                M = cv2.getPerspectiveTransform(np.float32([[0, 0], [W, 0], [W, H], [0, H]]),
                                                np.float32([[0, 0], [rx, -grow], [rx, H + grow], [0, H]]))
                cov = cv2.warpPerspective(front * (1 - 0.35 * math.sin(th)), M, (W, H), flags=cv2.INTER_LINEAR)
                ca = cv2.warpPerspective(np.ones((H, W), np.float32), M, (W, H), flags=cv2.INTER_LINEAR)
                fr = fr * (1 - ca[..., None]) + cov * ca[..., None]
        fade = ease(t, *FADE_IN) * (1 - ease(t, *FADE_OUT))
        frame = (np.clip(fr * fade, 0, 1) * 255).astype(np.uint8)
        p.stdin.write(frame.tobytes())
    p.stdin.close()
    p.wait()
    print('opening card written:', out)


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else 'door_card')
