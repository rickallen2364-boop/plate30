"""Etsy listing media for the animated card set: a 15-second square preview video and two listing photos.

Needs the files made by card_open.py and card_loop.py.
Usage:  python make_listing_media.py
Writes: work/listing/preview.mp4, work/listing/01-hero.jpg, work/listing/02-whats-included.jpg
"""
import cv2, numpy as np, subprocess, os
from PIL import Image, ImageDraw, ImageFont

SRC, OUT, FONTS = './work/cards/', './work/listing/', 'fonts/'
KEYS = ['door_card', 'candle_card', 'lamplight_card', 'shop_card', 'shoppers_card']
S, FPS = 1080, 24
GOLD, CREAM, DARK = (232, 196, 128), (240, 228, 205), (18, 13, 9)
os.makedirs(OUT, exist_ok=True)


def font(kind, size):
    return ImageFont.truetype(FONTS + {'title': 'cormorant-garamond-latin-600-italic.woff',
                                       'body': 'cormorant-garamond-latin-500-normal.woff',
                                       'small': 'cormorant-garamond-latin-500-italic.woff'}[kind], size)


def frames(path, start, end, n):
    """n evenly spaced frames between start and end seconds (BGR uint8)."""
    cap = cv2.VideoCapture(path)
    out = []
    for i in range(n):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int((start + (end - start) * i / max(n - 1, 1)) * FPS))
        ok, f = cap.read()
        out.append(f)
    return out


def portrait_on_square(f):
    """Phone-shaped frame centred on a square, with a blurred, darkened copy filling the sides."""
    bg = cv2.GaussianBlur(cv2.resize(f, (S, int(S * 16 / 9)))[int(S * 7 / 18):int(S * 7 / 18) + S], (0, 0), 30)
    bg = (bg * 0.35).astype(np.uint8)
    fg = cv2.resize(f, (608, S), interpolation=cv2.INTER_AREA)
    bg[:, (S - 608) // 2:(S + 608) // 2] = fg
    return bg


def text_img(img, lines):
    """Draw centred lines [(text, kind, size, colour, y)] on a BGR image."""
    im = Image.fromarray(img[..., ::-1])
    d = ImageDraw.Draw(im)
    for txt, kind, size, col, y in lines:
        d.text((img.shape[1] / 2 + 2, y + 3), txt, font=font(kind, size), anchor='mm', fill=(0, 0, 0))
        d.text((img.shape[1] / 2, y), txt, font=font(kind, size), anchor='mm', fill=col)
    return np.asarray(im)[..., ::-1].copy()


def preview_video():
    seq = []
    # 0-3 s: the envelope opens and the card comes out (sped up a little)
    seq += [portrait_on_square(f) for f in frames(SRC + 'door_card_open.mp4', 0.6, 4.9, 72)]
    # 3-11.5 s: the five fronts, 1.7 s each
    for k in KEYS:
        seq += [portrait_on_square(f) for f in frames(SRC + k + '.mp4', 1.0, 2.7, 41)]
    # 11.5-13.5 s: the card swings open to the greeting
    seq += [portrait_on_square(f) for f in frames(SRC + 'door_card_open.mp4', 10.9, 14.5, 48)]
    # 13.5-15 s: all five together with the headline
    loops = [frames(SRC + k + '.mp4', 3.0, 4.5, 35) for k in KEYS]
    for i in range(35):
        fr = np.full((S, S, 3), DARK[::-1], np.uint8)
        for j in range(5):
            fr[300:300 + 336, 30 + j * 207:30 + j * 207 + 189] = cv2.resize(loops[j][i], (189, 336), interpolation=cv2.INTER_AREA)
        seq.append(text_img(fr, [('5 Animated Christmas Cards', 'title', 84, GOLD, 170),
                                 ('Opens like a real card', 'body', 46, CREAM, 760),
                                 ('Text  ·  Email  ·  Share', 'body', 46, CREAM, 830),
                                 ('MidnightJoeArt', 'small', 34, (190, 170, 140), 980)]))
    # soft crossfades between sections
    cuts = [72] + [72 + 41 * (i + 1) for i in range(5)] + [72 + 205 + 48]
    for c in cuts:
        for k in range(1, 6):
            if c + k < len(seq):
                a = k / 6
                seq[c + k - 1] = cv2.addWeighted(seq[c - 1], 1 - a, seq[c + k - 1], a, 0)
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{S}x{S}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '20',
                          '-pix_fmt', 'yuv420p', '-tag:v', 'avc1', '-movflags', '+faststart', OUT + 'preview.mp4'],
                         stdin=subprocess.PIPE)
    for f in seq:
        p.stdin.write(f.tobytes())
    p.stdin.close()
    p.wait()
    print('preview video:', len(seq) / FPS, 's')


def photos():
    W, H = 2400, 1800
    stills = [cv2.imread(SRC + k + '.jpg') for k in KEYS]
    # 1. hero: the five cards side by side
    img = np.full((H, W, 3), DARK[::-1], np.uint8)
    cw, ch, gap = 420, 747, 30
    x0 = (W - (5 * cw + 4 * gap)) // 2
    for j, s in enumerate(stills):
        y = 560 + (40 if j % 2 else 0)
        sh = np.zeros((H, W), np.float32)
        sh[y + 20:y + ch + 20, x0 + j * (cw + gap) + 12:x0 + j * (cw + gap) + cw + 12] = 0.7
        img = (img * (1 - cv2.GaussianBlur(sh, (0, 0), 20))[..., None]).astype(np.uint8)
        img[y:y + ch, x0 + j * (cw + gap):x0 + j * (cw + gap) + cw] = cv2.resize(s, (cw, ch), interpolation=cv2.INTER_AREA)
    img = text_img(img, [('Christmas After Dark', 'small', 70, (200, 178, 140), 200),
                         ('5 Animated Christmas Cards', 'title', 150, GOLD, 330),
                         ('Opens like a real card  ·  Glowing lights & falling snow', 'body', 62, CREAM, 460),
                         ('Text  ·  Email  ·  Facebook  ·  WhatsApp        INSTANT DOWNLOAD', 'body', 56, CREAM, 1500),
                         ('MidnightJoeArt', 'small', 50, (190, 170, 140), 1680)])
    cv2.imwrite(OUT + '01-hero.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    # 2. what's included
    img = np.full((H, W, 3), DARK[::-1], np.uint8)
    inside = cv2.imread(f"./work/delivery/Christmas After Dark - Animated Cards/1 Front Door with Wreath/"
                        f"Front Door with Wreath - Still Card Inside.jpg")
    for j, s in enumerate([stills[0], inside]):
        img[330:330 + 1067, 220 + j * 660:220 + j * 660 + 600] = cv2.resize(s, (600, 1067), interpolation=cv2.INTER_AREA)
    im = Image.fromarray(img[..., ::-1])
    d = ImageDraw.Draw(im)
    d.text((1200, 180), "What's included", font=font('title', 120), anchor='mm', fill=GOLD)
    items = ['5 card designs, each with:', '', '•  Opening card video (20 sec)', '   envelope, wax seal, card opens',
             '•  Small version for Android texts', '•  Looping card for posts & stories', '•  Email GIF that plays by itself',
             '•  2 still pictures (front & inside)', '', 'Send to as many people as you like']
    for i, line in enumerate(items):
        d.text((1560, 420 + i * 92), line, font=font('body', 58), anchor='lm', fill=CREAM if line.startswith(('•', ' ')) else GOLD)
    d.text((1200, 1640), 'MidnightJoeArt', font=font('small', 50), anchor='mm', fill=(190, 170, 140))
    cv2.imwrite(OUT + '02-whats-included.jpg', np.asarray(im)[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 92])
    print('photos written')


if __name__ == '__main__':
    preview_video()
    photos()
