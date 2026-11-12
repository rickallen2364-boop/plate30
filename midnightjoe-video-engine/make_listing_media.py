"""Etsy listing media: a 15-second square preview video and two listing photos.

Needs the files made by card_open.py, card_loop.py and card_wide.py.
Usage:  python make_listing_media.py            (Set 1, five cards)  -> work/listing/
        python make_listing_media.py complete   (all 13 cards)        -> work/listing/complete/
Writes: preview.mp4, 01-hero.jpg, 02-whats-included.jpg
"""
import cv2, numpy as np, subprocess, os, sys
from PIL import Image, ImageDraw, ImageFont

SRC, FONTS = './work/cards/', 'fonts/'
SET1 = ['door_card', 'candle_card', 'lamplight_card', 'shop_card', 'shoppers_card']
SET2 = ['lanterns_card', 'church_card', 'mittens_card', 'village_card', 'cottage_card', 'frost_card',
        'carriage_card', 'cafe_card', 'window_card', 'rush_card', 'rooftops_card']
WHICH = sys.argv[1] if len(sys.argv) > 1 else 'set1'
KEYS = SET1 + SET2 if WHICH == 'complete' else SET1
OUT = './work/listing/complete/' if WHICH == 'complete' else './work/listing/'
N = len(KEYS)
HEADLINE = f'{N} Animated Christmas Cards'
S, FPS = 1080, 24
GOLD, CREAM, DARK, SOFT = (232, 196, 128), (240, 228, 205), (18, 13, 9), (190, 170, 140)
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
    bg[:, (S - 608) // 2:(S + 608) // 2] = cv2.resize(f, (608, S), interpolation=cv2.INTER_AREA)
    return bg


def text_img(img, lines):
    """Draw centred lines [(text, kind, size, colour, y)] on a BGR image."""
    im = Image.fromarray(img[..., ::-1])
    d = ImageDraw.Draw(im)
    for txt, kind, size, col, y in lines:
        d.text((img.shape[1] / 2 + 2, y + 3), txt, font=font(kind, size), anchor='mm', fill=(0, 0, 0))
        d.text((img.shape[1] / 2, y), txt, font=font(kind, size), anchor='mm', fill=col)
    return np.asarray(im)[..., ::-1].copy()


def grid_positions(n, area_w, card_w, card_h, gap, top, row_gap):
    """Cards in rows of up to 7, each row centred. Returns [(x, y)]."""
    per_row = n if n <= 7 else (n + 1) // 2 if n <= 14 else (n + 2) // 3
    pos = []
    for i in range(n):
        r, cidx = divmod(i, per_row)
        in_row = min(per_row, n - r * per_row)
        x0 = (area_w - (in_row * card_w + (in_row - 1) * gap)) // 2
        pos.append((x0 + cidx * (card_w + gap), top + r * (card_h + row_gap)))
    return pos


def preview_video():
    seq, cuts = [], []
    # the envelope opens and the card comes out (3 s)
    seq += [portrait_on_square(f) for f in frames(SRC + 'door_card_open.mp4', 0.6, 4.9, 72)]
    # every card's front (8.5 s for five cards, 7.6 s for thirteen)
    each = 41 if N <= 5 else 14
    for k in KEYS:
        cuts.append(len(seq))
        seq += [portrait_on_square(f) for f in frames(SRC + k + '.mp4', 1.0, 1.0 + each / FPS, each)]
    # the card swings open to the greeting (2 s)
    cuts.append(len(seq))
    seq += [portrait_on_square(f) for f in frames(SRC + 'door_card_open.mp4', 10.9, 14.5, 48)]
    # all cards together with the headline, filling up to exactly 15 seconds
    cuts.append(len(seq))
    n_end = 15 * FPS - len(seq)
    loops = [frames(SRC + k + '.mp4', 3.0, 3.0 + n_end / FPS, n_end) for k in KEYS]
    cw, ch = (189, 336) if N <= 5 else (130, 231)
    pos = grid_positions(N, S, cw, ch, 18 if N <= 5 else 12, 300 if N <= 5 else 250, 14)
    bottom = pos[-1][1] + ch
    for i in range(n_end):
        fr = np.full((S, S, 3), DARK[::-1], np.uint8)
        for j, (x, y) in enumerate(pos):
            fr[y:y + ch, x:x + cw] = cv2.resize(loops[j][i], (cw, ch), interpolation=cv2.INTER_AREA)
        seq.append(text_img(fr, [(HEADLINE, 'title', 84, GOLD, 150),
                                 ('Opens like a real card', 'body', 46, CREAM, bottom + 110),
                                 ('Phone & Computer  ·  Text  ·  Email  ·  Share', 'body', 42, CREAM, bottom + 175),
                                 ('MidnightJoeArt', 'small', 34, SOFT, 1010)]))
    fade = 6 if N <= 5 else 3                 # soft crossfades between sections
    for c in cuts:
        for k in range(1, fade):
            if 0 < c and c + k - 1 < len(seq):
                seq[c + k - 1] = cv2.addWeighted(seq[c - 1], 1 - k / fade, seq[c + k - 1], k / fade, 0)
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{S}x{S}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '20',
                          '-pix_fmt', 'yuv420p', '-tag:v', 'avc1', '-movflags', '+faststart', OUT + 'preview.mp4'],
                         stdin=subprocess.PIPE)
    for f in seq:
        p.stdin.write(f.tobytes())
    p.stdin.close()
    p.wait()
    print('preview video:', len(seq) / FPS, 's')


def shadowed_paste(img, src, x, y, w, h):
    sh = np.zeros(img.shape[:2], np.float32)
    sh[y + 18:y + h + 18, x + 10:x + w + 10] = 0.7
    img[:] = (img * (1 - cv2.GaussianBlur(sh, (0, 0), 18))[..., None]).astype(np.uint8)
    img[y:y + h, x:x + w] = cv2.resize(src, (w, h), interpolation=cv2.INTER_AREA)


def photos():
    W, H = 2400, 1800
    stills = [cv2.imread(SRC + k + '.jpg') for k in KEYS]
    # 1. hero: all the cards
    img = np.full((H, W, 3), DARK[::-1], np.uint8)
    if N <= 5:
        cw, ch = 420, 747
        pos = [(x, y + (40 if j % 2 else 0)) for j, (x, y) in enumerate(grid_positions(N, W, cw, ch, 30, 560, 0))]
        sub, bottom_y = 'Christmas After Dark', 1500
    else:
        cw, ch = 280, 498
        pos = grid_positions(N, W, cw, ch, 26, 520, 34)
        sub, bottom_y = 'Christmas After Dark  ·  The Complete Collection', 1660
    for s, (x, y) in zip(stills, pos):
        shadowed_paste(img, s, x, y, cw, ch)
    img = text_img(img, [(sub, 'small', 70, (200, 178, 140), 180),
                         (HEADLINE, 'title', 150, GOLD, 310),
                         ('Opens like a real card  ·  Glowing lights & falling snow', 'body', 62, CREAM, 435),
                         ('Phone & Computer  ·  Text  ·  Email  ·  Facebook  ·  WhatsApp      INSTANT DOWNLOAD',
                          'body', 52, CREAM, bottom_y),
                         ('MidnightJoeArt', 'small', 46, SOFT, bottom_y + 90)])
    cv2.imwrite(OUT + '01-hero.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    # 2. what's included: phone card, computer card front and inside, and the file list
    img = np.full((H, W, 3), DARK[::-1], np.uint8)
    wide_front, wide_inside = frames(SRC + 'door_card_wide.mp4', 8.0, 19.0, 2)
    shadowed_paste(img, stills[0], 130, 400, 520, 924)
    shadowed_paste(img, wide_front, 730, 400, 760, 428)
    shadowed_paste(img, wide_inside, 730, 896, 760, 428)
    im = Image.fromarray(img[..., ::-1])
    d = ImageDraw.Draw(im)
    d.text((W / 2, 170), "What's included", font=font('title', 120), anchor='mm', fill=GOLD)
    for txt, x, y in (('Phone', 390, 360), ('Computer', 1110, 360), ('Inside', 1110, 1364)):
        d.text((x, y), txt, font=font('small', 46), anchor='mm', fill=SOFT)
    items = [f'{N} card designs, each with:', '', '•  Phone card (opens, 20 sec)', '•  Computer card (opens, 20 sec)',
             '•  Small version for Android texts', '•  Looping card for posts', '•  Email GIF that plays by itself',
             '•  2 still pictures', '', 'Send to as many people', 'as you like']
    for i, line in enumerate(items):
        d.text((1570, 440 + i * 84), line, font=font('body', 52), anchor='lm',
               fill=CREAM if line.startswith('•') else GOLD)
    d.text((W / 2, 1640), 'MidnightJoeArt', font=font('small', 50), anchor='mm', fill=SOFT)
    cv2.imwrite(OUT + '02-whats-included.jpg', np.asarray(im)[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 92])
    print('photos written to', OUT)


if __name__ == '__main__':
    preview_video()
    photos()
