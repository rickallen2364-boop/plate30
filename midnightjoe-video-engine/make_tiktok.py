"""Three TikTok / Reels videos (1080 x 1920, silent: add a sound inside TikTok).

1. POV: the envelope opens and the card comes alive
2. Before / after: the still painting, then it comes alive
3. Which one would you send? three cards side by side
Usage:  python make_tiktok.py
Writes: work/tiktok/*.mp4
"""
import cv2, numpy as np, subprocess, os
from PIL import Image, ImageDraw, ImageFont
from card_loop import prepare

W, H, FPS = 1080, 1920, 24
SRC, OUT = './work/cards/', './work/tiktok/'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
os.makedirs(OUT, exist_ok=True)


def read_all(path, start=0.0, end=None):
    cap = cv2.VideoCapture(path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(start * FPS))
    frames = []
    while end is None or len(frames) < int((end - start) * FPS):
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    return frames


def caption(frame, lines, y, size=74):
    """Big white TikTok-style text with a dark outline, centred, wrapped to fit."""
    im = Image.fromarray(frame[..., ::-1])
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(BOLD, size)
    out = []
    for line in lines:
        words, cur = line.split(), ''
        for w in words:
            t = (cur + ' ' + w).strip()
            if d.textlength(t, font=f) > W - 150:
                out.append(cur)
                cur = w
            else:
                cur = t
        out.append(cur)
    for i, t in enumerate(out):
        d.text((W / 2, y + i * size * 1.25), t, font=f, anchor='mm', fill=(255, 255, 255),
               stroke_width=7, stroke_fill=(15, 10, 8))
    return np.asarray(im)[..., ::-1].copy()


def fade(a, b, n):
    return [cv2.addWeighted(a, 1 - k / n, b, k / n, 0) for k in range(1, n)]


def write(name, frames):
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '19',
                          '-pix_fmt', 'yuv420p', '-tag:v', 'avc1', '-movflags', '+faststart', OUT + name],
                         stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(f.tobytes())
    p.stdin.close()
    p.wait()
    print(name, round(len(frames) / FPS, 1), 's')


def video_pov():
    src = read_all(SRC + 'door_card_open.mp4', 0.4, 15.4)
    out = []
    for i, f in enumerate(src):
        t = i / FPS
        if t < 5.5:
            f = caption(f, ['POV: you got the prettiest Christmas card'], 330)
        elif 9.8 < t < 12.5:
            f = caption(f, ['it opens like a real card'], 330)
        elif t >= 12.8:
            f = caption(f, ['Animated Christmas cards', 'link in bio'], 330, 64)
        out.append(f)
    write('1-pov-prettiest-card.mp4', out)


def video_before_after():
    P = prepare('candle_card')
    still = (P['f'] * 255).astype(np.uint8)
    still = cv2.addWeighted(still, 0.85, np.zeros_like(still), 0.15, 0)        # a little flatter: "before"
    before = [caption(still, ['Watch this painting', 'come alive...'], 330)] * int(2.6 * FPS)
    loop = read_all(SRC + 'candle_card.mp4') * 1
    after = [caption(f, ['Glowing candle. Falling snow.'], 330, 66) if i < 5 * FPS else
             caption(f, ['Send it as a Christmas card', 'link in bio'], 330, 64) for i, f in enumerate(loop)]
    write('2-painting-comes-alive.mp4', before + fade(before[-1], after[0], 8) + after)


def video_which_one():
    keys = ['candle_card', 'church_card', 'rooftops_card']
    loops = [read_all(SRC + k + '.mp4') for k in keys]
    n = min(len(l) for l in loops)
    cw, ch, gap = 340, 604, 15
    x0 = (W - 3 * cw - 2 * gap) // 2
    y0 = 640
    out = []
    for i in range(n):
        fr = np.full((H, W, 3), (14, 10, 8), np.uint8)
        im = Image.new('RGB', (W, H), (8, 10, 14))
        fr = np.asarray(im)[..., ::-1].copy()
        for j, l in enumerate(loops):
            x = x0 + j * (cw + gap)
            fr[y0:y0 + ch, x:x + cw] = cv2.resize(l[i], (cw, ch), interpolation=cv2.INTER_AREA)
        fr = caption(fr, ['Which one would you send?'], 420, 76)
        im = Image.fromarray(fr[..., ::-1])
        d = ImageDraw.Draw(im)
        f = ImageFont.truetype(BOLD, 90)
        for j in range(3):
            d.text((x0 + j * (cw + gap) + cw / 2, y0 + ch + 90), str(j + 1), font=f, anchor='mm',
                   fill=(255, 255, 255), stroke_width=6, stroke_fill=(15, 10, 8))
        f2 = ImageFont.truetype(BOLD, 52)
        d.text((W / 2, y0 + ch + 230), 'Comment 1, 2 or 3', font=f2, anchor='mm', fill=(255, 220, 150),
               stroke_width=5, stroke_fill=(15, 10, 8))
        out.append(np.asarray(im)[..., ::-1].copy())
    write('3-which-one-would-you-send.mp4', out)


if __name__ == '__main__':
    video_pov()
    video_before_after()
    video_which_one()
