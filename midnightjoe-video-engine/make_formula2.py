"""Formula 2 'ASMR assembly' TikTok (17 s, 1080 x 1920, silent: add a sound inside TikTok).

0-3 s   the sealed envelope drops in and lands, hook text
3-11 s  slow and satisfying: the flap opens, the card slides out and fills the screen
11-17 s the card swings open to the greeting and holds on the art, call to action
Usage:  python make_formula2.py [card]      (default: door_card)
Writes: work/tiktok/formula2-<card>.mp4
"""
import sys, os, subprocess
import card_open
from make_tiktok import read_all, caption, write, OUT

card = sys.argv[1] if len(sys.argv) > 1 else 'door_card'
# slower, ASMR timeline (seconds)
card_open.DUR = 17.0
card_open.FADE_IN = (0.0, 0.2)
card_open.FLAP = (3.2, 5.0)
card_open.RISE = (5.0, 8.0)
card_open.ZOOM = (8.0, 9.6)
card_open.OPEN = (11.2, 12.8)
card_open.TXT = (13.0, 14.2)
card_open.FADE_OUT = (16.8, 17.0)

os.makedirs(OUT, exist_ok=True)
raw = OUT + f'_raw-{card}.mp4'
card_open.build(card, out=raw, drop_in=(0.0, 1.1))

frames = read_all(raw)
final = []
for i, f in enumerate(frames):
    t = i / 24
    if t < 4.6:
        f = caption(f, ['This Christmas card', 'opens like a real one'], 330, 62)
    elif t >= 14.4:
        f = caption(f, ['Send it by text or email', 'link in bio'], 640, 60)
    final.append(f)
write(f'formula2-{card}.mp4', final)
os.remove(raw)
