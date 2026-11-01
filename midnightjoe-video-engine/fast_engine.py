"""Fast engine: build per-painting light loops + snow loops once, then compose long segments with ffmpeg."""
import cv2, numpy as np, subprocess, sys, math, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_clip import CFG, smooth, load_painting

cv2.setNumThreads(2)
SRC = 'paintings/'
WORK = './work/fast/'
os.makedirs(WORK, exist_ok=True)
W, H, FPS = 1920, 1080, 24
LOOP = 60            # light loop length (seconds); all flicker frequencies are whole cycles of this
SNOW_T = 90          # snow loop length (seconds)
K = {'door': (13, 6), 'laundry': (15, 6), 'candle': (18, 8), 'shop': (21, 9), 'shoppers': (15, 6)}
SNOW_KIND = {'door': ('dense', .90), 'laundry': ('dense', .90), 'candle': ('light', 1.0),
             'shop': ('dense', 1.0), 'shoppers': ('dense', .75)}
SNOW_SPEC = {'dense': (285, 145, 40), 'light': (90, 0, 0)}


def ffmpeg_writer(path, w, h, crf=12):
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{w}x{h}',
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', str(crf),
           '-pix_fmt', 'yuv420p', path]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def make_lit_loop(name):
    c = CFG[name]
    img = load_painting(c['file'])[:1448]          # even height
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
    halo = np.clip(cv2.GaussianBlur(f * m[..., None], (0, 0), c['halo']) * c['hg'], 0, 1)
    halo = (halo * 255).astype(np.uint8).astype(np.float32) / 255   # same rounding as the first version
    rng = np.random.default_rng(c['seed'])
    ph = rng.standard_normal((18, 32)).astype(np.float32)
    ph = cv2.resize(ph, (Ws, Hs), interpolation=cv2.INTER_CUBIC)
    ph = ph / (ph.std() + 1e-6) * 3.0
    gm = np.zeros((Hs, Ws), np.float32)
    if 'candle' in c:
        cx, cy, ax, ay = c['candle']
        cv2.ellipse(gm, (cx, cy), (ax, ay), 0, 0, 360, 1.0, -1)
        gm = cv2.GaussianBlur(gm, (0, 0), 50)
    # only the glowing region changes from frame to frame
    act = (m > 0.002) | (halo.max(axis=2) > 0.004) | (gm > 0.002)
    ys, xs = np.where(act)
    y0, y1, x0, x1 = max(ys.min() - 8, 0), min(ys.max() + 8, Hs), max(xs.min() - 8, 0), min(xs.max() + 8, Ws)
    sb, sh = f[y0:y1, x0:x1], halo[y0:y1, x0:x1]
    sm, sp, sg = m[y0:y1, x0:x1], ph[y0:y1, x0:x1], gm[y0:y1, x0:x1]
    k1, k2 = K[name]
    n = LOOP * FPS
    out = WORK + f'{name}_lit.mp4'
    p = ffmpeg_writer(out, Ws, Hs, crf=10)
    t0 = time.time()
    for i in range(n):
        t = i / FPS
        slow = np.sin(2 * math.pi * (k1 / LOOP) * t + sp) * 0.7 + np.sin(2 * math.pi * (k2 / LOOP) * t + sp * 1.7) * 0.3
        if 'candle' in c:
            fast = (math.sin(2 * math.pi * 2.3 * t + 0.4) + math.sin(2 * math.pi * 3.7 * t + 1.9)
                    + math.sin(2 * math.pi * 5.9 * t + 4.1)) / 3
            slowc = 0.6 * math.sin(2 * math.pi * 0.35 * t)
            fl = slow * (1 - sg) + (0.75 * fast + 0.25 * slowc) * sg
        else:
            fl = slow
        gain = 1 + c['amp'] * sm * fl
        sub = sb * gain[..., None] + sh * (c['hamp'] * (0.5 + 0.5 * fl))[..., None]
        frame = img.copy()
        frame[y0:y1, x0:x1] = (np.clip(sub, 0, 1) * 255).astype(np.uint8)
        p.stdin.write(frame.tobytes())
    p.stdin.close()
    p.wait()
    print(name, 'lit loop', round(time.time() - t0, 1), 's', flush=True)


def make_snow_loop(kind):
    counts = SNOW_SPEC[kind]
    rng = np.random.default_rng(77 if kind == 'dense' else 78)
    T = SNOW_T
    # (count, radius, speed range px/s, alpha, blur)
    specs = [(counts[0], 1, (28, 48), .55, .6), (counts[1], 2, (55, 90), .55, 1.0), (counts[2], 4, (100, 150), .40, 2.2)]
    layers = []
    for n, rad, sp, a, bl in specs:
        if n <= 0:
            continue
        sp_ = rng.uniform(*sp, n)
        k = np.maximum(1, np.round(sp_ * T / H))          # whole number of screen-heights over the loop
        layers.append(dict(n=n, r=rad, a=a, bl=bl, x=rng.uniform(0, W, n), y=rng.uniform(0, H, n),
                           sp=k * H / T, ph=rng.uniform(0, 6.28, n), sw=rng.uniform(8, 26, n),
                           m=rng.integers(2, 6, n), dr=rng.integers(-1, 3, n) * W / T))
    tint = np.array([1.0, 0.97, 0.92], np.float32)
    out = WORK + f'snow_{kind}.mp4'
    p = ffmpeg_writer(out, W, H, crf=10)
    t0 = time.time()
    for i in range(T * FPS):
        t = i / FPS
        acc = np.zeros((H, W), np.float32)
        for L in layers:
            img = np.zeros((H, W), np.float32)
            x = (L['x'] + L['sw'] * np.sin(2 * math.pi * L['m'] / T * t + L['ph']) + L['dr'] * t) % W
            y = (L['y'] + L['sp'] * t) % H
            for xi, yi in zip(x, y):
                cv2.circle(img, (int(xi), int(yi)), L['r'], L['a'], -1, cv2.LINE_AA)
            img = cv2.GaussianBlur(img, (0, 0), L['bl'])
            acc = 1 - (1 - acc) * (1 - img)
        frame = (np.clip(acc[..., None] * tint, 0, 1) * 255).astype(np.uint8)
        p.stdin.write(frame.tobytes())
    p.stdin.close()
    p.wait()
    print('snow', kind, round(time.time() - t0, 1), 's', flush=True)


def compose(name, seconds, out):
    """One painting for `seconds` seconds: slow camera over the light loop, snow on top."""
    c = CFG[name]
    Ws, Hs = 2576, 1448
    zf = 1920 / Ws
    D = float(seconds)
    kind, op = SNOW_KIND[name]
    z0, z1 = c['zoom']
    u = f'min(t/{D},1)'
    Z = f'({z0}+({z1}-{z0})*{u})'
    F = f'({zf}*{Z})'
    cx = f"({c['c0'][0]}+({c['c1'][0]}-{c['c0'][0]})*{u})"
    cy = f"({c['c0'][1]}+({c['c1'][1]}-{c['c0'][1]})*{u})"
    fg = (f"[0:v]scale=w='2*trunc({Ws}*{F}/2)':h='2*trunc({Hs}*{F}/2)':eval=frame:flags=bilinear,"
          f"crop=1920:1080:x='max(0,min({cx}*{F}-960,iw-1920))':y='max(0,min({cy}*{F}-540,ih-1080))',format=gbrp[v];"
          f"[1:v]format=gbrp[s];[v][s]blend=all_mode=screen:all_opacity={op},format=yuv420p[o]")
    fgfile = WORK + f'{name}_{int(D)}.fg'
    open(fgfile, 'w').write(fg)
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-stream_loop', '-1', '-i', WORK + f'{name}_lit.mp4',
           '-stream_loop', '-1', '-i', WORK + f'snow_{kind}.mp4', '-filter_complex_script', fgfile,
           '-map', '[o]', '-t', str(D), '-r', str(FPS), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19',
           '-pix_fmt', 'yuv420p', out]
    t0 = time.time()
    subprocess.run(cmd, check=True)
    print(name, 'segment', seconds, 's built in', round(time.time() - t0, 1), 's', flush=True)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'lit':
        make_lit_loop(sys.argv[2])
    elif cmd == 'snow':
        make_snow_loop(sys.argv[2])
    elif cmd == 'seg':
        compose(sys.argv[2], float(sys.argv[3]), sys.argv[4])
