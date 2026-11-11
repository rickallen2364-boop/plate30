"""Animated greeting card: a short, perfectly looping phone video (9:16) made from one painting.

The painting's light gently glows and flickers, snow falls, and a greeting sits at the bottom.
Usage:  python card_loop.py door_card
Writes: work/cards/<name>.mp4 (looping video) and work/cards/<name>.jpg (still preview)
"""
import cv2, numpy as np, subprocess, sys, math, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS, T = 1080, 1920, 24, 10          # phone size, 10-second seamless loop
OUT = './work/cards/'
FONT_DIR = os.environ.get('CARD_FONTS', 'fonts/')

CARDS = {
    # Paintings are the 4K originals. Positions below are measured on a 2576-wide copy and scaled automatically.
    'door_card': dict(file='paintings/4k/moody4.jpg', crop_x=997,
                      glow_box=(1150, 20, 1660, 720), lo=.42, hi=.72, halo=45, hg=2.0,
                      amp=.20, hamp=.28, slow=(2, 3), flutter=(37, 59), flutter_amt=.12,
                      title='Merry Christmas', line2='Peace & light this season'),
    'candle_card': dict(file='paintings/4k/candle.jpg', crop_x=993, inset_y=450,
                        glow_box=(1050, 350, 1760, 1300), lo=.45, hi=.75, halo=45, hg=2.0,
                        amp=.22, hamp=.30, slow=(3, 4), flutter=(23, 37), flutter_amt=.30,
                        title='Merry Christmas', line2='May your home be warm and bright',
                        snow_window=1090,    # snow only on the window glass, not on the sill or the candle jar
                        snow_color=False,    # the whole window is glass, so don't pick it out by colour
                        snow_exclude_box=[(0, 0, 362, 1090), (1160, 0, 1300, 1090), (1215, 515, 1775, 1100), (90, 790, 840, 1100)]),  # frame bars, jar, holly
    'lamplight_card': dict(file='paintings/4k/door.jpg', crop_x=1540,
                           glow_box=(1500, 0, 2576, 1300), lo=.55, hi=.80, halo=40, hg=2.0,
                           amp=.20, hamp=.28, slow=(2, 3), flutter=(37, 59), flutter_amt=.10,
                           title="Season's Greetings", line2="Wishing you a peaceful winter's night"),
    'shop_card': dict(file='paintings/4k/shop.jpg', crop_x=1323, inset_y=250,
                      glow_box=(1250, 350, 2250, 1200), lo=.55, hi=.82, halo=35, hg=2.0,
                      amp=.20, hamp=.30, slow=(3, 4), flutter=(37, 59), flutter_amt=.10,
                      title='Happy Holidays', line2='Warm wishes from our home to yours'),
    'shoppers_card': dict(file='paintings/4k/shoppers.jpg', crop_x=1243, inset_y=300,
                          glow_box=(1000, 150, 2200, 1000), lo=.65, hi=.90, halo=40, hg=1.6,
                          amp=.14, hamp=.22, slow=(2, 3), flutter=(37, 59), flutter_amt=.10,
                          title='Merry Christmas', line2='Joy to you and yours this season'),
    # ---- Set 2 ----
    'lanterns_card': dict(file='paintings/4k/lanterns.jpg', crop_x=448,
                          glow_box=(300, 30, 1800, 900), lo=.50, hi=.80, halo=40, hg=2.0,
                          amp=.20, hamp=.30, slow=(2, 3), flutter=(37, 59), flutter_amt=.12,
                          title='Merry Christmas', line2='Lighting your way home this season'),
    'church_card': dict(file='paintings/4k/church.jpg', crop_x=448, inset_y=400,
                        glow_box=(250, 400, 1500, 1300), lo=.45, hi=.75, halo=40, hg=2.0,
                        amp=.20, hamp=.30, slow=(2, 3), flutter=(29, 47), flutter_amt=.15,
                        title='O Holy Night', line2='Wishing you peace this Christmas'),
    'mittens_card': dict(file='paintings/4k/mittens.jpg', crop_x=1500, inset_y=100,
                         glow_box=(1300, 300, 2576, 1449), lo=.45, hi=.75, halo=45, hg=2.0,
                         amp=.22, hamp=.30, slow=(3, 4), flutter=(23, 37), flutter_amt=.25,
                         title='Warm Wishes', line2='Stay cozy this Christmas',
                         snow_window=820,    # snow only on the blue window glass above this line (indoor scene)
                         snow_exclude=[(755, 700, 300, 330), (1450, 650, 100, 220), (1757, 694, 272, 302), (2149, 694, 196, 287)]),  # the mittens
    'village_card': dict(file='paintings/4k/moody1.jpg', crop_x=851,
                         glow_box=(0, 0, 2576, 1449), lo=.55, hi=.85, halo=35, hg=2.0,
                         amp=.20, hamp=.28, slow=(3, 4), flutter=(37, 59), flutter_amt=.10,
                         title='Merry Christmas', line2='May your days be merry and bright'),
    'cottage_card': dict(file='paintings/4k/moody2.jpg', crop_x=1393, inset_y=150,
                         glow_box=(1300, 450, 2400, 1150), lo=.45, hi=.75, halo=40, hg=2.0,
                         amp=.22, hamp=.30, slow=(2, 3), flutter=(29, 47), flutter_amt=.15,
                         title="Season's Greetings", line2='Peace on earth, and in your home'),
    'frost_card': dict(file='paintings/4k/moody3.jpg', crop_x=300, inset_y=250,
                       glow_box=(0, 250, 1400, 1300), lo=.45, hi=.75, halo=50, hg=2.0,
                       amp=.20, hamp=.30, slow=(2, 3), flutter=(23, 37), flutter_amt=.10,
                       title='Peace & Joy', line2='Warmest wishes this winter'),
    'carriage_card': dict(file='paintings/4k/moody6.jpg', crop_x=943, inset_y=550,
                          glow_box=(900, 300, 2000, 1250), lo=.45, hi=.75, halo=40, hg=2.0,
                          amp=.22, hamp=.30, slow=(2, 3), flutter=(29, 47), flutter_amt=.15,
                          title='Merry Christmas', line2='Wishing you a joyful journey home'),
    'cafe_card': dict(file='paintings/4k/moody7.jpg', crop_x=1093, inset_y=300,
                      glow_box=(1000, 450, 2100, 1150), lo=.45, hi=.75, halo=40, hg=2.0,
                      amp=.20, hamp=.30, slow=(2, 3), flutter=(37, 59), flutter_amt=.12,
                      title='Happy Holidays', line2='Come in from the cold'),
}


def smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def text_layer(c):
    """Greeting text with a soft dark band behind it, as an RGBA image."""
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    band = np.zeros((H, W), np.float32)
    y0 = int(H * 0.70)
    band[y0:] = np.linspace(0, 1, H - y0)[:, None] ** 0.8
    shade = Image.fromarray((band * 190).astype(np.uint8))
    layer.paste(Image.new('RGBA', (W, H), (20, 14, 8, 255)), (0, 0), shade)
    d = ImageDraw.Draw(layer)
    f1 = ImageFont.truetype(FONT_DIR + 'cormorant-garamond-latin-600-italic.woff', 128)
    f2 = ImageFont.truetype(FONT_DIR + 'cormorant-garamond-latin-500-normal.woff', 54)
    f3 = ImageFont.truetype(FONT_DIR + 'cormorant-garamond-latin-500-italic.woff', 30)
    gold, cream = (232, 196, 128, 255), (240, 228, 205, 235)
    shadow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(shadow)
    for draw, col in ((ds, (0, 0, 0, 200)), (d, None)):
        draw.text((W / 2, 1585), c['title'], font=f1, anchor='mm', fill=col or gold)
        draw.text((W / 2, 1712), c['line2'], font=f2, anchor='mm', fill=col or cream)
        draw.text((W / 2, 1868), 'MidnightJoeArt', font=f3, anchor='mm', fill=col or (200, 180, 150, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    return Image.alpha_composite(shadow, layer)


def snow_layers():
    """Three layers of flakes. Every speed and sway is a whole number of cycles in T, so the loop is seamless."""
    rng = np.random.default_rng(21)
    # (count per tile, radius, tile height, tiles moved per loop, alpha, blur)
    specs = [(70, 2, 640, 1, .55, .8), (30, 3, 640, 2, .55, 1.3), (9, 6, 1920, 1, .40, 2.8)]
    layers = []
    for n, r, P, k, a, bl in specs:
        reps = H // P
        x = np.tile(rng.uniform(0, W, n), reps)
        base = rng.uniform(0, P, n)
        y = np.concatenate([base + j * P for j in range(reps)])   # same flakes repeated down the screen
        layers.append(dict(r=r, a=a, bl=bl, x=x, y=y, v=k * P / T, sw=np.tile(rng.uniform(6, 20, n), reps),
                           ph=np.tile(rng.uniform(0, 6.28, n), reps), cyc=np.tile(rng.integers(1, 3, n), reps)))
    return layers


def render_snow(layers, t):
    acc = np.zeros((H, W), np.float32)
    for L in layers:
        img = np.zeros((H, W), np.float32)
        x = (L['x'] + L['sw'] * np.sin(2 * math.pi * L['cyc'] / T * t + L['ph'])) % W
        y = (L['y'] + L['v'] * t) % H
        for xi, yi in zip(x, y):
            cv2.circle(img, (int(xi), int(yi)), L['r'], L['a'], -1, cv2.LINE_AA)
        img = cv2.GaussianBlur(img, (0, 0), L['bl'])
        acc = 1 - (1 - acc) * (1 - img)
    return acc


def prepare(name):
    """Load the painting, crop it to phone shape and work out where the light glows."""
    c = CARDS[name]
    src = cv2.imread(c['file'])
    if src is None:
        sys.exit(f"Could not find {c['file']}")
    k = src.shape[1] / 2576                      # positions are written for a 2576-wide painting
    Hs = src.shape[0]
    cw = int(round(Hs * W / H))
    cx = min(int(round(c['crop_x'] * k)), src.shape[1] - cw)
    img = cv2.resize(src[:, cx:cx + cw], (W, H), interpolation=cv2.INTER_AREA if cw > W else cv2.INTER_CUBIC)
    s = W / cw
    f = img.astype(np.float32) / 255
    b, g, r = cv2.split(f)
    m = smooth(.114 * b + .587 * g + .299 * r, c['lo'], c['hi']) * smooth(r - b, -0.02, 0.08)
    x0, y0, x1, y1 = (v * k for v in c['glow_box'])
    roi = np.zeros((H, W), np.float32)
    roi[int(y0 * s):int(y1 * s), max(0, int((x0 - cx) * s)):int((x1 - cx) * s)] = 1
    m *= cv2.GaussianBlur(roi, (0, 0), 40)
    halo = np.clip(cv2.GaussianBlur(f * m[..., None], (0, 0), c['halo']) * c['hg'], 0, 1)
    return dict(c=c, f=f, m=m, halo=halo, snow=snow_layers(), snow_mask=window_mask(c, f, k * s, cx * s))


def window_mask(c, f, scale, offset=0):
    """For indoor scenes: 1 on the cool, blue-grey window glass above the sill, 0 elsewhere (None = snow everywhere).
    `scale` turns 2576-wide painting positions into screen pixels; `offset` is how far the crop starts from the left."""
    if 'snow_window' not in c:
        return None
    b, g, r = cv2.split(f)
    m = smooth(b - r, -0.02, 0.06) if c.get('snow_color', True) else np.ones_like(b)
    m[int(c['snow_window'] * scale):] = 0
    for x0, y0, x1, y1 in c.get('snow_exclude_box', []):
        m[max(0, int(y0 * scale)):int(y1 * scale), max(0, int(x0 * scale - offset)):max(0, int(x1 * scale - offset))] = 0
    for ex, ey, ax, ay in c.get('snow_exclude', []):   # objects in front of the glass
        cv2.ellipse(m, (int(ex * scale - offset), int(ey * scale)), (int(ax * scale), int(ay * scale)), 0, 0, 360, 0, -1)
    return cv2.GaussianBlur(m, (0, 0), 3)[..., None]


TINT = np.array([0.92, 0.97, 1.0], np.float32)   # BGR: slightly warm-white flakes


def front_frame(P, t, snow=True):
    """The painting at time t: glowing light plus falling snow, as a float BGR image (0..1)."""
    c = P['c']
    k1, k2 = c['slow']
    q1, q2 = c['flutter']
    fl = (0.7 * math.sin(2 * math.pi * k1 / T * t) + 0.3 * math.sin(2 * math.pi * k2 / T * t + 1.3)
          + c['flutter_amt'] * (math.sin(2 * math.pi * q1 / T * t) + math.sin(2 * math.pi * q2 / T * t + 2.1)))
    fr = np.clip(P['f'] * (1 + c['amp'] * P['m'] * fl)[..., None] + P['halo'] * (c['hamp'] * (0.5 + 0.5 * fl)), 0, 1)
    if snow:
        sn = render_snow(P['snow'], t)[..., None] * TINT
        if P.get('snow_mask') is not None:
            sn = sn * P['snow_mask']
        fr = 1 - (1 - fr) * (1 - sn)
    return fr


def build(name):
    P = prepare(name)
    c = P['c']
    txt = np.asarray(text_layer(c)).astype(np.float32) / 255
    ta, trgb = txt[..., 3:4], txt[..., 2::-1]         # RGBA -> alpha + BGR
    os.makedirs(OUT, exist_ok=True)
    out = OUT + name + '.mp4'
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}',
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p',
           '-tag:v', 'avc1', '-movflags', '+faststart', out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(T * FPS):
        fr = front_frame(P, i / FPS)
        fr = fr * (1 - ta) + trgb * ta
        frame = (np.clip(fr, 0, 1) * 255).astype(np.uint8)
        if i == 0:
            cv2.imwrite(OUT + name + '.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
        p.stdin.write(frame.tobytes())
    p.stdin.close()
    p.wait()
    print('card written:', out)


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else 'door_card')
