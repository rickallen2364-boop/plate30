"""Pack the animated cards into the folder a buyer downloads.

Needs work/cards/<card>_open.mp4 (card_open.py) and work/cards/<card>.mp4 (card_loop.py) for each card.
Usage:  python make_card_set.py [set1|set2]
Writes: work/delivery/<set folder>/<number name>/...
"""
import os, subprocess, shutil, sys

SETS = {
    'set1': ('Christmas After Dark - Animated Cards',
             [('door_card', '1 Front Door with Wreath'), ('candle_card', '2 Amber Candle'),
              ('lamplight_card', '3 Lamplight Corner'), ('shop_card', '4 Corner Shop'),
              ('shoppers_card', '5 Holiday Shoppers')]),
    'set2': ('Christmas After Dark - Animated Cards Set 2',
             [('lanterns_card', '1 Christmas Lanterns'), ('church_card', '2 Snowy Church'),
              ('mittens_card', '3 Christmas Mittens'), ('village_card', '4 Village Lights'),
              ('cottage_card', '5 Cottage by the Pond'), ('frost_card', '6 Frosted Window'),
              ('carriage_card', '7 Christmas Carriage'), ('cafe_card', '8 Snowy Night Cafe')]),
}
FOLDER, CARDS = SETS[sys.argv[1] if len(sys.argv) > 1 else 'set1']
SRC = './work/cards/'
DEST = f'./work/delivery/{FOLDER}/'
SMALL_KBPS = 330          # keeps the 20-second Android version under about 1 MB


def ff(*args):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *args], check=True)


for key, title in CARDS:
    d = DEST + title + '/'
    os.makedirs(d, exist_ok=True)
    name = title.split(' ', 1)[1]
    opened, loop = SRC + key + '_open.mp4', SRC + key + '.mp4'
    # 1. full quality opening card for phones (iPhone, WhatsApp, Facebook)
    shutil.copy(opened, d + f'{name} - Opening Card.mp4')
    # 1b. wide opening card for laptops and computers (card_wide.py)
    shutil.copy(SRC + key + '_wide.mp4', d + f'{name} - Computer Card.mp4')
    # 2. small version for Android picture messages (two-pass to hit the size)
    small = d + f'{name} - Opening Card (small, for Android texts).mp4'
    common = ['-i', opened, '-vf', 'scale=540:960', '-c:v', 'libx264', '-b:v', f'{SMALL_KBPS}k', '-preset', 'slow',
              '-pix_fmt', 'yuv420p', '-tag:v', 'avc1']
    ff(*common, '-pass', '1', '-passlogfile', '/tmp/x264pass', '-an', '-f', 'mp4', '/dev/null')
    ff(*common, '-pass', '2', '-passlogfile', '/tmp/x264pass', '-movflags', '+faststart', small)
    # 3. looping front with greeting (for posts and stories)
    shutil.copy(loop, d + f'{name} - Looping Card.mp4')
    # 4. GIF of the looping front, plays by itself inside emails
    gif = d + f'{name} - Email GIF.gif'
    ff('-i', loop, '-filter_complex',
       'fps=8,scale=360:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];'
       '[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle', '-loop', '0', gif)   # about 3-4 MB
    # 5. still pictures: the front with greeting, and the inside page
    shutil.copy(SRC + key + '.jpg', d + f'{name} - Still Card Front.jpg')
    ff('-ss', '19.0', '-i', opened, '-frames:v', '1', '-q:v', '2', d + f'{name} - Still Card Inside.jpg')
    print('packed', title)

for root, _, files in sorted(os.walk(DEST)):
    for f in sorted(files):
        print(f'{os.path.getsize(os.path.join(root, f)) / 1e6:6.2f} MB  {os.path.basename(root)}/{f}')
