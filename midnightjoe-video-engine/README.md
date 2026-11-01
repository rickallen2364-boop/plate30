# Midnight Joe Art — Video Engine

This project turns Rick Allen's MidnightJoeArt paintings into long, relaxing videos
for the **Midnight Joe Art** YouTube channel (target length: 1.5 to 3 hours).

Each painting gets:

- **A slow camera move**: a gentle push-in, a sideways pan, or a pull-back.
- **Flickering lights**: only the warm, glowing parts of the painting (windows, lamps,
  candles) softly brighten and dim, like real light. The candle painting gets a faster,
  livelier candle flicker.
- **Falling snow**: gentle snow in three layers (tiny far-away flakes, medium flakes, and a
  few big soft close-up flakes).

**This look is approved.** Rick: "the flicker was spot on perfect", and the snow was raised
about 30% on request (that's "version 2", the current version). **Please don't change the
look settings** unless Rick asks.

---

## What's in this folder

| File | What it is |
|---|---|
| `build_clip.py` | **The first method (the reference).** It draws every single frame by hand. Slow (about 90 seconds to make a 14 second clip), but it shows exactly what the approved look should be. |
| `fast_engine.py` | **The faster method.** It makes short, seamless loops once and then lets the free video tool *ffmpeg* stretch them into long videos. |
| `paintings/` | **Put the painting pictures here** (see the list below). It is empty for now. |
| `work/` | Created automatically. All test pictures and videos are saved here. It is *not* saved to GitHub because the files are huge. |
| `requirements.txt` | The list of add-ons the programs need. |

## The paintings

The originals live in Rick's Google Drive folder **"Christmas After Dark"**. Copy each one
into the `paintings/` folder and **rename it exactly** like this:

| Name in this project | Original file in Google Drive |
|---|---|
| `paintings/door.jpg` | "Door with wreath.jpg" |
| `paintings/laundry.jpg` | "Night laundry mat.jpg" |
| `paintings/candle.jpg` | "Amber candle by glass.jpg" |
| `paintings/shop.jpg` | ". Vintage Teal Corner Shop Snowy Night.jpg" (the name really starts with a dot and a space) |
| `paintings/shoppers.jpg` | "Snowy Evening Holiday Shoppers.jpg" |

The settings were tuned for pictures that are **2576 pixels wide and 1448 pixels tall** (or a
little taller). The fast method assumes that size, so use the same files that were used before.
If a picture is missing, the program stops and tells you which one.

---

## What the computer needs (one-time setup)

This runs on a normal computer or a rented server, **not on the iPad itself**.

1. **Python 3** (the programming language the code is written in).
2. The two add-ons: `pip install -r requirements.txt`
   - *opencv-python-headless*: does the picture work (blurring, zooming, drawing snowflakes).
   - *numpy*: does the maths on whole pictures at once.
3. **ffmpeg**, a free video tool that must be installed separately
   (for example `sudo apt install ffmpeg` on Linux, or `brew install ffmpeg` on a Mac).

Always run the commands below **from inside this project folder**.

---

## How to run it

The painting names you can use are: `door`, `laundry`, `candle`, `shop`, `shoppers`.

### Method 1: the reference look (`build_clip.py`)

- **Quick preview (3 still pictures):**
  `python build_clip.py door still`
  This saves `work/door_still_1.png`, `work/door_still_7.png` and `work/door_still_13.png`
  (snapshots at 1, 7 and 13 seconds). Takes a few seconds.
- **A 14-second test clip:**
  `python build_clip.py door`
  This saves `work/door.mp4`. Takes about 90 seconds.

### Method 2: the fast engine for long videos (`fast_engine.py`)

This works in three steps. Steps 1 and 2 only need to be done **once**; after that the loops
are reused for every video.

1. **Make the two snow loops (one time, about 6 minutes total):**
   `python fast_engine.py snow dense`
   `python fast_engine.py snow light`
   Each makes a 90-second snow video that loops perfectly (the end flows back into the start).
   "Dense" snow is used for four paintings; "light" snow is for the candle.
2. **Make the light-flicker loop for each painting (one time, 2 to 3.5 minutes each):**
   `python fast_engine.py lit door` (then the same for `laundry`, `candle`, `shop`, `shoppers`)
   Each makes a 60-second flicker video that loops perfectly.
3. **Build a long section for one painting:**
   `python fast_engine.py seg door 600 work/door_10min.mp4`
   This means: painting `door`, `600` seconds long (10 minutes), saved as `work/door_10min.mp4`.
   The camera moves slowly across the whole length, and the flicker and snow loops repeat
   underneath it.

**Speed (measured on a 2-core computer):** about 13 seconds of computer time per 10 seconds
of finished video (about 1.3 times the video length). **A 2-hour video takes about
2.5 hours** to build.

---

## What each setting means

All the look settings are at the top of `build_clip.py` in the `CFG` list (one entry per
painting). The fast engine reuses them. **These are approved; leave them alone unless Rick
asks for a change.**

| Setting | Plain English |
|---|---|
| `file` | Which picture in `paintings/` to use. |
| `zoom` | How close the camera is at the **start** and at the **end**. 1.0 = the whole painting fills the screen; bigger numbers = closer. `(1.03, 1.12)` is a slow push-in; `(1.28, 1.12)` is a pull-back; the same number twice (like `(1.22, 1.22)`) means no zoom, just a pan. |
| `c0`, `c1` | Where the camera is pointing at the start (`c0`) and at the end (`c1`), as a spot on the painting (pixels across, pixels down). Different spots make a pan. |
| `rois` | Rectangles marking the areas that are **allowed to flicker** (windows, signs, lamps). Lights outside these boxes stay still. |
| `lo`, `hi` | How bright a spot must be to count as "a light". Below `lo` it never flickers; above `hi` it flickers fully; in between it fades in smoothly. Only warm (orange/yellow) colours count. |
| `halo` | How far the soft glow spreads around each light (bigger = wider, softer glow). |
| `hg` | How strong that glow is. |
| `amp` | How much the lights themselves brighten and dim (0.22 = up to about 22%). |
| `hamp` | How much the glow around the lights pulses. |
| `freq` | How fast the flicker is (in the first method). Low numbers = slow, calm breathing. |
| `seed` | A "lucky number" that fixes the random pattern, so the flicker and snow look the same every time. |
| `snow` | How many snowflakes in each of the three layers: (small far flakes, medium flakes, big close flakes). `(90, 0, 0)` = only a light dusting of small flakes (used for the candle). |
| `candle` | Only for the candle painting: the oval area around the flame that gets the faster, livelier candle flicker. |

Settings found only in `fast_engine.py`:

| Setting | Plain English |
|---|---|
| `LOOP = 60` | The light-flicker loop is 60 seconds long. |
| `SNOW_T = 90` | The snow loop is 90 seconds long. |
| `K` | The flicker speeds for each painting, chosen so the flicker fits a whole number of times into 60 seconds. That's what makes the loop seamless. |
| `SNOW_KIND` | Which snow each painting uses (`dense` or `light`) and how see-through it is (1.0 = full strength, 0.75 = a bit softer). |
| `SNOW_SPEC` | Flake counts for the two snow loops. `dense` is the "+30%" version 2 snow. |

---

## Decisions made so far

- **Rick works only on an iPad and isn't technical**, so everything is explained in plain English.
- **Approved look:** five paintings, each with a slow camera move, flickering lights in the
  glowing areas, and gentle falling snow. **Version 2 (snow +30%) is the current approved version.**
- **The first method (`build_clip.py`) is the reference** for the approved look. It's slow (about
  90 seconds per 14-second clip).
- **The fast method (`fast_engine.py`)** builds a 60-second seamless light loop per painting and
  two 90-second seamless snow loops once, then uses ffmpeg to build long videos. About 1.3× the
  video length to build. One-time prep: snow about 6 minutes; each painting 2 to 3.5 minutes.
- **YouTube rules:** the videos must have real variety (different paintings, different effects,
  chapters, original visuals) and the **"altered or synthetic content" / AI-music disclosure
  must be switched ON** (the music is made with Suno). **Don't repeat one short loop for hours.**
- **Money:** Rick has chosen **not to pay for a server yet**. He'll wait until the channel
  shows traction. A Replit "Reserved VM" would cost about $50/month (2 cores) or $130/month
  (4 cores).

## Known weak spots (to improve later)

1. **The snow step is the slowest part.** Laying the snow over the painting is done in a slow
   colour format (`gbrp`).
2. **The camera zoom resizes the picture on every frame** (`scale ... eval=frame`), which is slow.
3. **Joining paintings together isn't done yet.** `seg` builds one painting at a time. The
   soft cross-fades between paintings still need to be added (plan: an ffmpeg "xfade" chain with
   2-second fades, or doing everything in one ffmpeg pass).

## Planned next steps (not done yet)

1. **Test a 10-minute video** with one Suno music track.
2. **A simple Replit page** where Rick picks a Google Drive folder of paintings and a folder of
   music, sets the length, and presses **Build**.
3. **Finished videos are saved to Google Drive** and then **uploaded to YouTube through
   Make.com** (already connected). This route is needed because YouTube only lets
   unapproved ("unaudited") apps upload private videos.
4. **A Reserved VM server on Replit** will probably be needed for long builds. On hold until the
   channel shows traction.
