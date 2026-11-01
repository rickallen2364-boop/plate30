import cv2, numpy as np, subprocess, sys, math, os, time

cv2.setNumThreads(1)
W, H, FPS, DUR = 1920, 1080, 24, 14.0
SRC = 'paintings/'
OUT = './work/'
os.makedirs(OUT, exist_ok=True)

CFG = {
    'door': dict(file='door.jpg', zoom=(1.03, 1.12), c0=(1288, 760), c1=(1400, 640),
                 rois=[(1150, 20, 1700, 520)], lo=.55, hi=.80, halo=35, hg=2.2, amp=.22, hamp=.30,
                 freq=.22, seed=1, snow=(260, 120, 34)),
    'laundry': dict(file='laundry.jpg', zoom=(1.22, 1.22), c0=(1250, 700), c1=(1500, 700),
                    rois=[(700, 90, 1700, 260), (1180, 520, 1900, 720)], lo=.5, hi=.78, halo=35, hg=2.0,
                    amp=.20, hamp=.30, freq=.25, seed=2, snow=(260, 120, 34)),
    'candle': dict(file='candle.jpg', zoom=(1.05, 1.20), c0=(1300, 780), c1=(1480, 860),
                   rois=[(940, 700, 1760, 1200)], lo=.45, hi=.75, halo=40, hg=2.0, amp=.22, hamp=.30,
                   freq=.30, seed=3, snow=(90, 0, 0), candle=(1480, 880, 260, 330)),
    'shop': dict(file='shop.jpg', zoom=(1.15, 1.15), c0=(1120, 720), c1=(1456, 720),
                 rois=[(420, 100, 2300, 1000)], lo=.62, hi=.85, halo=35, hg=2.0, amp=.20, hamp=.30,
                 freq=.35, seed=4, snow=(285, 145, 40)),
    'shoppers': dict(file='shoppers.jpg', zoom=(1.28, 1.12), c0=(1300, 740), c1=(1288, 725),
                     rois=[(780, 330, 2260, 840)], lo=.74, hi=.93, halo=40, hg=1.6, amp=.14, hamp=.22,
                     freq=.25, seed=5, snow=(210, 95, 24)),
}


def load_painting(fname):
    img = cv2.imread(SRC + fname)
    if img is None:
        sys.exit(f'Could not find the painting {SRC}{fname}. Put the picture in the paintings folder '
                 f'with exactly that name, then run this again from the project folder.')
    return img


def smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


class Snow:
    def __init__(self, counts, seed):
        rng = np.random.default_rng(seed)
        # (count, radius, speed px/s, alpha, blur sigma)
        specs = [(counts[0], 1.2, (28, 48), .55, .6), (counts[1], 2.2, (55, 90), .55, 1.0),
                 (counts[2], 4.0, (100, 150), .40, 2.2)]
        self.layers = []
        for (n, r, sp, a, bl), idx in zip(specs, range(3)):
            if n <= 0:
                continue
            self.layers.append(dict(
                n=n, r=r, a=a, bl=bl,
                x=rng.uniform(0, W, n), y=rng.uniform(0, H, n),
                sp=rng.uniform(*sp, n), ph=rng.uniform(0, 6.28, n),
                sw=rng.uniform(8, 26, n), dr=rng.uniform(-6, 10)))

    def render(self, t):
        out = np.zeros((H, W), np.float32)
        for L in self.layers:
            img = np.zeros((H, W), np.float32)
            x = (L['x'] + L['sw'] * np.sin(0.5 * t + L['ph']) + L['dr'] * t) % W
            y = (L['y'] + L['sp'] * t) % H
            for xi, yi in zip(x, y):
                cv2.circle(img, (int(xi), int(yi)), max(1, int(round(L['r']))), L['a'], -1, cv2.LINE_AA)
            img = cv2.GaussianBlur(img, (0, 0), L['bl'])
            out = 1 - (1 - out) * (1 - img)
        return out


def build(name):
    c = CFG[name]
    img = load_painting(c['file'])
    Hs, Ws = img.shape[:2]
    f = img.astype(np.float32) / 255
    b, g, r = cv2.split(f)
    lum = .114 * b + .587 * g + .299 * r
    warm = r - b
    m = smooth(lum, c['lo'], c['hi']) * smooth(warm, -0.02, 0.08)
    roi = np.zeros((Hs, Ws), np.float32)
    for (x0, y0, x1, y1) in c['rois']:
        roi[y0:y1, x0:x1] = 1
    m = m * cv2.GaussianBlur(roi, (0, 0), 30)
    halo = cv2.GaussianBlur(f * m[..., None], (0, 0), c['halo']) * c['hg']
    halo_u8 = (np.clip(halo, 0, 1) * 255).astype(np.uint8)
    rng = np.random.default_rng(c['seed'])
    ph = rng.standard_normal((18, 32)).astype(np.float32)
    ph = cv2.resize(ph, (Ws, Hs), interpolation=cv2.INTER_CUBIC)
    ph = ph / (ph.std() + 1e-6) * 3.0
    gm = np.zeros((Hs, Ws), np.float32)
    if 'candle' in c:
        cx, cy, ax, ay = c['candle']
        cv2.ellipse(gm, (cx, cy), (ax, ay), 0, 0, 360, 1.0, -1)
        gm = cv2.GaussianBlur(gm, (0, 0), 50)
    m3 = np.dstack([m, ph, gm]).astype(np.float32)
    snow = Snow(c['snow'], c['seed'] + 10)
    return c, img, halo_u8, m3, snow, (Ws, Hs)


def frame(c, img, halo_u8, m3, snow, dims, t):
    Ws, Hs = dims
    u = t / DUR
    zoom = c['zoom'][0] + (c['zoom'][1] - c['zoom'][0]) * u
    s = (W / Ws) * zoom
    cx = c['c0'][0] + (c['c1'][0] - c['c0'][0]) * u
    cy = c['c0'][1] + (c['c1'][1] - c['c0'][1]) * u
    hw, hh = (W / 2) / s, (H / 2) / s
    cx = min(max(cx, hw), Ws - hw)
    cy = min(max(cy, hh), Hs - hh)
    M = np.float32([[s, 0, W / 2 - s * cx], [0, s, H / 2 - s * cy]])
    fl = cv2.INTER_LINEAR
    base = cv2.warpAffine(img, M, (W, H), flags=fl, borderMode=cv2.BORDER_REPLICATE)
    hl = cv2.warpAffine(halo_u8, M, (W, H), flags=fl, borderMode=cv2.BORDER_REPLICATE)
    mp = cv2.warpAffine(m3, M, (W, H), flags=fl, borderMode=cv2.BORDER_REPLICATE)
    mk, ph, gm = mp[..., 0], mp[..., 1], mp[..., 2]
    slow = np.sin(2 * math.pi * c['freq'] * t + ph) * 0.7 + np.sin(2 * math.pi * c['freq'] * 0.43 * t + ph * 1.7) * 0.3
    if 'candle' in c:
        fast = (math.sin(2 * math.pi * 2.3 * t + 0.4) + math.sin(2 * math.pi * 3.7 * t + 1.9)
                + math.sin(2 * math.pi * 5.9 * t + 4.1)) / 3
        slowc = 0.6 * math.sin(2 * math.pi * 0.35 * t)
        fl_ = slow * (1 - gm) + (0.75 * fast + 0.25 * slowc) * gm
    else:
        fl_ = slow
    gain = 1 + c['amp'] * mk * fl_
    out = base.astype(np.float32) / 255 * gain[..., None]
    out += hl.astype(np.float32) / 255 * (c['hamp'] * (0.5 + 0.5 * fl_))[..., None]
    out = np.clip(out, 0, 1)
    sn = snow.render(t)
    tint = np.array([1.0, 0.97, 0.92], np.float32)
    out = 1 - (1 - out) * (1 - sn[..., None] * tint)
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


if __name__ == '__main__':
    name = sys.argv[1]
    data = build(name)
    if len(sys.argv) > 2 and sys.argv[2] == 'still':
        t0 = time.time()
        for tt in (1.0, 7.0, 13.0):
            fr = frame(*data, tt)
            cv2.imwrite(f'{OUT}{name}_still_{int(tt)}.png', fr)
        print(name, 'still ok', round((time.time() - t0) / 3, 3), 's/frame')
        sys.exit()
    out = f'{OUT}{name}.mp4'
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}',
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '15',
           '-pix_fmt', 'yuv420p', out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(DUR * FPS)
    t0 = time.time()
    for i in range(n):
        p.stdin.write(frame(*data, i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    print(name, 'done', round(time.time() - t0, 1), 's')
