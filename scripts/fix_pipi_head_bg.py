from PIL import Image
import numpy as np
import os

# Fix existing pipi-head.gif black background by replacing near-black pixels with white.
# This is a fallback when the source video is no longer available.

INPUT = 'miniprogram/images/pipi-head.gif'
OUTPUT = 'miniprogram/images/pipi-head.gif'
BG = np.array([255, 255, 255])
THRESH = 10  # max channel value treated as background

img = Image.open(INPUT)
frames = []
durations = []

try:
    while True:
        frame = img.copy().convert('RGB')
        arr = np.array(frame)
        lum = np.max(arr, axis=2)
        bg_mask = lum < THRESH
        arr[bg_mask] = BG

        pil_img = Image.fromarray(arr)
        pil_p = pil_img.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)

        # Ensure palette index 0 is white (background color)
        pal = np.array(pil_p.getpalette()).reshape(-1, 3)
        white_idx = int(np.argmin(np.sum((pal - BG) ** 2, axis=1)))
        if white_idx != 0:
            pal[[0, white_idx]] = pal[[white_idx, 0]]
            data = np.array(pil_p)
            new_data = np.where(data == white_idx, 0, np.where(data == 0, white_idx, data))
            pil_p = Image.fromarray(new_data.astype(np.uint8), mode='P')
            pil_p.putpalette(pal.flatten().tolist())

        frames.append(pil_p)
        durations.append(img.info.get('duration', 100))
        img.seek(img.tell() + 1)
except EOFError:
    pass

frames[0].save(OUTPUT, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)
print(f'Saved {OUTPUT}: {len(frames)} frames, {os.path.getsize(OUTPUT)/1024:.1f} KB')
