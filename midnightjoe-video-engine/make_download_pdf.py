"""The PDF a buyer downloads from Etsy: thank-you, the Google Drive link, and how to save and send the cards.

Usage:  python make_download_pdf.py
Writes: ../etsy/downloads/<listing>.pdf
"""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

OUT = '../etsy/downloads/'
INK, GOLD, SOFT, PAPER, NIGHT = HexColor('#2b211a'), HexColor('#a8803f'), HexColor('#6e5b4a'), HexColor('#f4ede1'), HexColor('#16110d')

LISTINGS = [
    dict(file='Christmas-After-Dark-Complete-Collection-Download.pdf',
         title='The Complete Collection', count='16 animated Christmas cards',
         link='https://drive.google.com/drive/folders/1N05S7vsqbvcXnk0o6t5G8TzO9gFWevC1',
         hero='work/listing/complete/01-hero.jpg',
         inside='Two folders: "Animated Cards" (5 cards) and "Animated Cards Set 2" (11 cards). '
                'Each card has its own folder.'),
    dict(file='Christmas-After-Dark-Set-of-5-Download.pdf',
         title='Set of 5', count='5 animated Christmas cards',
         link='https://drive.google.com/drive/folders/1RnIG_41f7ak4nQ4gHXEZf8vpQJdbTdic',
         hero='work/listing/01-hero.jpg',
         inside='Five card folders: Front Door with Wreath, Amber Candle, Lamplight Corner, '
                'Corner Shop and Holiday Shoppers.'),
]

FILES = [('Opening Card', 'phones: iPhone texts, WhatsApp, Messenger'),
         ('Computer Card', 'wide version for laptops, computers and email'),
         ('Opening Card (small, for Android texts)', 'Android picture messages'),
         ('Looping Card', 'Facebook, Instagram and WhatsApp posts and stories'),
         ('Email GIF', 'plays by itself inside an email'),
         ('Still Card Front / Inside', 'plain pictures, if you need them')]

STEPS = [('iPhone or iPad', ['Tap the link above. Install the free Google Drive app if asked.',
                             'Open a card folder and tap the "Opening Card" video.',
                             'Tap the three dots, then "Send a copy", then "Save Video".',
                             'Send it from your Photos in Messages, like any video.']),
         ('Android', ['Tap the link and open a card folder.',
                      'Tap the three dots next to a file, then "Download".',
                      'For picture messages, use the "small, for Android texts" version.']),
         ('Computer', ['Open the link, right-click a card folder and choose "Download".',
                       'Attach the "Computer Card" or the GIF to an email.'])]


def wrap(c, text, x, y, width, font, size, color, leading=None):
    c.setFont(font, size)
    c.setFillColor(color)
    leading = leading or size * 1.35
    words, line = text.split(), ''
    for w in words:
        trial = (line + ' ' + w).strip()
        if c.stringWidth(trial, font, size) > width:
            c.drawString(x, y, line)
            y -= leading
            line = w
        else:
            line = trial
    if line:
        c.drawString(x, y, line)
        y -= leading
    return y


def make(L):
    W, H = letter
    c = canvas.Canvas(OUT + L['file'], pagesize=letter)
    c.setTitle('Christmas After Dark ' + L['title'] + ' - your download')
    c.setAuthor('MidnightJoeArt')
    c.setFillColor(PAPER)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    # header band with the cards
    band = 180
    c.setFillColor(NIGHT)
    c.rect(0, H - band, W, band, stroke=0, fill=1)
    img = ImageReader(L['hero'])
    iw, ih = img.getSize()
    h = band - 20
    w = h * iw / ih
    c.drawImage(img, (W - w) / 2, H - band + 10, w, h)
    m = 54
    y = H - band - 36
    c.setFont('Times-Italic', 15)
    c.setFillColor(GOLD)
    c.drawString(m, y, 'Christmas After Dark')
    y -= 34
    c.setFont('Times-Bold', 28)
    c.setFillColor(INK)
    c.drawString(m, y, 'Thank you! Your cards are ready.')
    y -= 22
    y = wrap(c, f"{L['title']}: {L['count']}. Send them to as many friends and family as you like.",
             m, y, W - 2 * m, 'Helvetica', 11.5, SOFT)
    # the link, as a button
    y -= 14
    bh = 44
    c.setFillColor(INK)
    c.roundRect(m, y - bh, W - 2 * m, bh, 8, stroke=0, fill=1)
    c.setFont('Helvetica-Bold', 15)
    c.setFillColor(PAPER)
    c.drawCentredString(W / 2, y - bh / 2 - 5, 'TAP HERE TO OPEN YOUR CARDS')
    c.linkURL(L['link'], (m, y - bh, W - m, y), relative=0)
    y -= bh + 12
    c.setFont('Helvetica', 9)
    c.setFillColor(SOFT)
    c.drawString(m, y, 'Or copy this link:')
    y -= 13
    c.setFont('Helvetica-Bold', 9)
    c.setFillColor(INK)
    c.drawString(m, y, L['link'])
    c.linkURL(L['link'], (m, y - 3, W - m, y + 10), relative=0)
    y -= 26
    # what's inside
    c.setFont('Times-Bold', 16)
    c.setFillColor(INK)
    c.drawString(m, y, "What's inside")
    y -= 18
    y = wrap(c, L['inside'] + ' Every card folder has:', m, y, W - 2 * m, 'Helvetica', 10.5, SOFT)
    y -= 2
    for name, use in FILES:
        c.setFont('Helvetica-Bold', 10)
        c.setFillColor(INK)
        c.drawString(m + 10, y, '•  ' + name)
        c.setFont('Helvetica', 10)
        c.setFillColor(SOFT)
        c.drawString(m + 10 + c.stringWidth('•  ' + name, 'Helvetica-Bold', 10) + 6, y, '- ' + use)
        y -= 15
    y -= 12
    # how to save and send, three columns
    c.setFont('Times-Bold', 16)
    c.setFillColor(INK)
    c.drawString(m, y, 'How to save and send a card')
    y -= 20
    colw = (W - 2 * m - 2 * 18) / 3
    top = y
    for i, (head, lines) in enumerate(STEPS):
        x, yy = m + i * (colw + 18), top
        c.setFont('Helvetica-Bold', 10.5)
        c.setFillColor(GOLD)
        c.drawString(x, yy, head.upper())
        yy -= 16
        for n, line in enumerate(lines, 1):
            yy = wrap(c, f'{n}. {line}', x, yy, colw, 'Helvetica', 9.5, INK, 12.5) - 4
    # footer
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.6)
    c.line(m, 92, W - m, 92)
    wrap(c, 'Tip: download on Wi-Fi. Each card opens to a short seasonal greeting, so add your own message '
            'when you text or email it. For personal use only; please don\'t share or resell the files. '
            'Need help? Message me on Etsy and I\'ll make it right.', m, 76, W - 2 * m, 'Helvetica', 8.5, SOFT, 11)
    c.setFont('Times-Italic', 12)
    c.setFillColor(GOLD)
    c.drawCentredString(W / 2, 30, 'MidnightJoeArt')
    c.showPage()
    c.save()
    print('written', OUT + L['file'])


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for L in LISTINGS:
        make(L)
