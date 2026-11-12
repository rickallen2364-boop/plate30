"""Computer-size opening card (wide, 1920 x 1080, 20 seconds) - the companion to the phone card.

Same story as card_open.py: envelope with wax seal -> card slides out -> the whole painting glows with
falling snow -> the card swings open -> the greeting inside (painting on the left, words on the right).
Usage:  python card_wide.py door_card
Writes: work/cards/<name>_wide.mp4
"""
import cv2, numpy as np, subprocess, sys, math, os
from PIL import Image, ImageDraw
from card_loop import CARDS, FPS, T, OUT, smooth, TINT, window_mask
from card_open import ease, paper, over, poly_mask, make_seal, DUR, FADE_IN, FLAP, RISE, ZOOM, OPEN, TXT, FADE_OUT
from card_loop import FONT_DIR
from PIL import ImageFont

W, H = 1920, 1080
EW, EH, EX, EY = 1000, 640, 460, 420      # envelope
CW, CH = 880, 495                          # card while inside the envelope
CX, CY0, CY1 = 520, 460, 59                # card left, start top (hidden), top after sliding out


def prepare_wide(name):
    """Whole painting at 1920 x 1080; the light flickers inside the same area as on the phone card."""
    c = CARDS[name]
    src = cv2.imread(c['file'])
    if src is None:
        sys.exit(f"Could not find {c['file']}")
    k = src.shape[1] / 2576
    img = cv2.resize(src, (W, H), interpolation=cv2.INTER_AREA)
    s = W / src.shape[1]
    f = img.astype(np.float32) / 255
    b, g, r = cv2.split(f)
    m = smooth(.114 * b + .587 * g + .299 * r, c['lo'], c['hi']) * smooth(r - b, *c.get('warm', (-0.02, 0.08)))   # how orange a light must be
    x0, y0, x1, y1 = (int(v * k * s) for v in c['glow_box'])
    roi = np.zeros((H, W), np.float32)
    roi[y0:y1, x0:x1] = 1
    m *= cv2.GaussianBlur(roi, (0, 0), 40)
    halo = np.clip(cv2.GaussianBlur(f * m[..., None], (0, 0), c['halo']) * c['hg'], 0, 1)
    return dict(c=c, f=f, m=m, halo=halo, snow=snow_layers(), snow_mask=window_mask(c, f, k * s))


def snow_layers():
    """Same three flake layers as the phone card, laid out for a wide screen (whole cycles in T, so it loops)."""
    rng = np.random.default_rng(21)
    specs = [(70, 2, 360, 1, .55, .8), (30, 3, 360, 2, .55, 1.3), (9, 6, 1080, 1, .40, 2.8)]
    layers = []
    for n, r, P, k, a, bl in specs:
        reps = H // P
        base = rng.uniform(0, P, n)
        layers.append(dict(r=r, a=a, bl=bl, x=np.tile(rng.uniform(0, W, n), reps),
                           y=np.concatenate([base + j * P for j in range(reps)]), v=k * P / T,
                           sw=np.tile(rng.uniform(6, 20, n), reps), ph=np.tile(rng.uniform(0, 6.28, n), reps),
                           cyc=np.tile(rng.integers(1, 3, n), reps)))
    return layers


def render_snow(layers, t):
    acc = np.zeros((H, W), np.float32)
    for L in layers:
        img = np.zeros((H, W), np.float32)
        x = (L['x'] + L['sw'] * np.sin(2 * math.pi * L['cyc'] / T * t + L['ph'])) % W
        y = (L['y'] + L['v'] * t) % H
        for xi, yi in zip(x, y):
            cv2.circle(img, (int(xi), int(yi)), L['r'], L['a'], -1, cv2.LINE_AA)
        acc = 1 - (1 - acc) * (1 - cv2.GaussianBlur(img, (0, 0), L['bl']))
    return acc


def front(P, t, snow=True):
    c = P['c']
    k1, k2 = c['slow']
    q1, q2 = c['flutter']
    fl = (0.7 * math.sin(2 * math.pi * k1 / T * t) + 0.3 * math.sin(2 * math.pi * k2 / T * t + 1.3)
          + c['flutter_amt'] * (math.sin(2 * math.pi * q1 / T * t) + math.sin(2 * math.pi * q2 / T * t + 2.1)))
    fr = np.clip(P['f'] * (1 + c['amp'] * P['m'] * fl)[..., None] + P['halo'] * (c['hamp'] * (0.5 + 0.5 * fl)), 0, 1)
    if snow:
        sn = render_snow(P['snow'], t)[..., None] * TINT
        if P['snow_mask'] is not None:
            sn = sn * P['snow_mask']
        fr = 1 - (1 - fr) * (1 - sn)
    return fr


def inside_page(c):
    """Cream inside page: small live painting on the left, greeting on the right."""
    pg = paper(W, H, (236, 226, 204), 5)
    inset = (120, 238, 860, 484)
    x, y, w, h = inset
    shadow = np.zeros((H, W), np.float32)
    shadow[y + 14:y + h + 14, x + 8:x + w + 8] = 1
    pg *= (1 - 0.35 * cv2.GaussianBlur(shadow, (0, 0), 14))[..., None]
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = 1450
    d.text((cx, 400), c['title'], font=ImageFont.truetype(FONT_DIR + 'cormorant-garamond-latin-600-italic.woff', 116),
           anchor='mm', fill=(74, 46, 28, 255))
    d.line((cx - 140, 482, cx + 140, 482), fill=(176, 138, 76, 255), width=3)
    d.text((cx, 550), c['line2'], font=ImageFont.truetype(FONT_DIR + 'cormorant-garamond-latin-500-normal.woff', 48),
           anchor='mm', fill=(110, 82, 58, 255))
    d.text((cx, 990), 'MidnightJoeArt', font=ImageFont.truetype(FONT_DIR + 'cormorant-garamond-latin-500-italic.woff', 30),
           anchor='mm', fill=(140, 115, 90, 200))
    a = np.asarray(im).astype(np.float32) / 255
    return pg, a[..., 2::-1].copy(), a[..., 3:4].copy(), inset


def build(name):
    P = prepare_wide(name)
    c = P['c']
    bg = cv2.GaussianBlur(P['f'], (0, 0), 28) * 0.38
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    bg *= (1 - 0.55 * np.clip(((xx / W - .5) ** 2 + (yy / H - .5) ** 2) * 2.4, 0, 1))[..., None]
    env_back = paper(EW, EH, (186, 172, 148), 1)
    pocket = paper(EW, EH, (230, 219, 196), 2)
    pocket_a = poly_mask(EW, EH, [(0, .18 * EH), (EW / 2, .56 * EH), (EW, .18 * EH), (EW, EH), (0, EH)])
    pocket *= (1 - 0.22 * cv2.GaussianBlur(1 - pocket_a, (0, 0), 10) * pocket_a)[..., None]
    flap_out = paper(EW, EH, (238, 228, 206), 3)
    flap_in = paper(EW, EH, (200, 186, 160), 4)
    seal, seal_a = make_seal()
    full_a = np.ones((EH, EW), np.float32)
    pg, txt, txt_a, (ix, iy, iw, ih) = inside_page(c)
    os.makedirs(OUT, exist_ok=True)
    out = OUT + name + '_wide.mp4'
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
                          '-pix_fmt', 'yuv420p', '-tag:v', 'avc1', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        t = i / FPS
        if t < OPEN[0]:
            fr_front = front(P, t, snow=t >= ZOOM[0])
        if t < ZOOM[1]:
            fr = bg.copy()
            ex, ey = EX, EY + int(ease(t, ZOOM[0], ZOOM[0] + 0.6) * 900)
            over(fr, env_back, full_a, ex, ey)
            q = math.cos(math.pi * ease(t, *FLAP))
            tip, sq = .56 * EH * q, .18 * EH * abs(q)
            flap_a = poly_mask(EW, int(.6 * EH), [(0, 0), (EW, 0), (EW, sq), (EW / 2, abs(tip)), (0, sq)])
            if q < 0:
                fa = np.flipud(flap_a)
                over(fr, flap_in[:fa.shape[0]] * 0.92, fa, ex, ey - fa.shape[0])
            z = ease(t, *ZOOM)
            cy = CY0 + (CY1 - CY0) * ease(t, *RISE)
            x0, y0 = CX - CX * z, cy - cy * z
            w_, h_ = CW + (W - CW) * z, CH + (H - CH) * z
            card = cv2.resize(fr_front, (int(w_), int(h_)), interpolation=cv2.INTER_AREA)
            sh = np.zeros((H, W), np.float32)
            sh[int(y0) + 16:int(y0 + h_) + 16, int(x0) + 10:int(x0 + w_) + 10] = 0.6 * (1 - z)
            fr *= (1 - cv2.GaussianBlur(sh, (0, 0), 18))[..., None]
            if t < ZOOM[0]:
                over(fr, card, np.ones(card.shape[:2], np.float32), int(x0), int(y0))
                over(fr, pocket, pocket_a, ex, ey)
            else:
                over(fr, pocket, pocket_a, ex, ey)
                over(fr, card, np.ones(card.shape[:2], np.float32), int(x0), int(y0))
            if q >= 0:
                over(fr, flap_out[:flap_a.shape[0]], flap_a, ex, ey)
                if q > 0.15:
                    over(fr, seal, seal_a, ex + EW // 2 - 75, ey + int(tip) - 95)
            if t < ZOOM[0]:
                fr = 1 - (1 - fr) * (1 - 0.6 * render_snow(P['snow'], t)[..., None] * TINT)
        elif t < OPEN[0]:
            fr = fr_front
        else:
            th = math.pi * ease(t, *OPEN)
            fr = pg.copy()
            fr[iy:iy + ih, ix:ix + iw] = cv2.resize(front(P, t, snow=False), (iw, ih), interpolation=cv2.INTER_AREA)
            ta = txt_a * ease(t, *TXT)
            fr = fr * (1 - ta) + txt * ta
            if th < math.pi / 2:
                fr *= 1 - 0.45 * math.sin(th)
                rx, grow = W * math.cos(th), 110 * math.sin(th)
                M = cv2.getPerspectiveTransform(np.float32([[0, 0], [W, 0], [W, H], [0, H]]),
                                                np.float32([[0, 0], [rx, -grow], [rx, H + grow], [0, H]]))
                cov = cv2.warpPerspective(fr_front * (1 - 0.35 * math.sin(th)), M, (W, H), flags=cv2.INTER_LINEAR)
                ca = cv2.warpPerspective(np.ones((H, W), np.float32), M, (W, H), flags=cv2.INTER_LINEAR)
                fr = fr * (1 - ca[..., None]) + cov * ca[..., None]
        fade = ease(t, *FADE_IN) * (1 - ease(t, *FADE_OUT))
        p.stdin.write((np.clip(fr * fade, 0, 1) * 255).astype(np.uint8).tobytes())
    p.stdin.close()
    p.wait()
    print('computer card written:', out)


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else 'door_card')
