#!/usr/bin/env python3
"""把皮皮视频只抠出头部，生成 GIF"""

import os
import cv2
import numpy as np
from PIL import Image
import imageio
from rembg import remove, new_session
from tqdm import tqdm

INPUT_PATH = "miniprogram/pipi.2.mov"
OUTPUT_GIF = "miniprogram/images/pipi-head.gif"
TARGET_SIZE = 300
TARGET_FPS = 6
PROCESS_HEIGHT = 720


def resize_keep_aspect(frame, target_height):
    h, w = frame.shape[:2]
    scale = target_height / h
    new_w = int(w * scale)
    return cv2.resize(frame, (new_w, target_height), interpolation=cv2.INTER_AREA)


def get_head_bbox(alpha, head_ratio=0.55):
    """取主体上半部分作为头部"""
    mask = alpha > 30
    if not np.any(mask):
        return None
    ys, xs = np.where(mask)
    y1, y2 = ys.min(), ys.max()
    x1, x2 = xs.min(), xs.max()
    h, w = alpha.shape
    bbox_h = y2 - y1
    bbox_w = x2 - x1
    # 取上半部分
    head_h = int(bbox_h * head_ratio)
    cy = y1 + head_h // 2
    cx = (x1 + x2) // 2
    size = max(head_h, bbox_w)
    half = size // 2
    top = max(0, cy - half)
    left = max(0, cx - half)
    bottom = min(h, top + size)
    right = min(w, left + size)
    if bottom - top < size:
        top = max(0, bottom - size)
    if right - left < size:
        left = max(0, right - size)
    return top, left, bottom, right


def main():
    print(f"读取视频: {INPUT_PATH}")
    reader = imageio.get_reader(INPUT_PATH)
    meta = reader.get_meta_data()
    fps = meta.get('fps', 30)
    n_frames = meta.get('nframes', None)
    print(f"视频信息: 分辨率={meta.get('size')}, 帧率={fps}")

    frame_interval = max(1, int(round(fps / TARGET_FPS)))
    session = new_session("u2net")

    gif_frames = []
    frame_count = 0

    for frame in tqdm(reader, total=n_frames):
        if frame_count % frame_interval != 0:
            frame_count += 1
            continue

        small = resize_keep_aspect(frame, PROCESS_HEIGHT)
        h, w = small.shape[:2]
        size = max(h, w)
        pad_h = size - h
        pad_w = size - w
        padded = np.pad(
            small,
            ((pad_h // 2, pad_h - pad_h // 2), (pad_w // 2, pad_w - pad_w // 2), (0, 0)),
            constant_values=0
        )

        rgba = remove(padded, session=session)
        alpha = rgba[:, :, 3]

        bbox = get_head_bbox(alpha)
        if bbox is None:
            frame_count += 1
            continue

        top, left, bottom, right = bbox
        head = rgba[top:bottom, left:right]

        img = Image.fromarray(head).resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)
        # 用白色背景避免微信小程序黑底问题
        bg = Image.new('RGB', (TARGET_SIZE, TARGET_SIZE), (255, 255, 255))
        bg.paste(img, mask=img.split()[3])

        pil_p = bg.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        gif_frames.append(pil_p)
        frame_count += 1

    reader.close()

    if not gif_frames:
        print("没有处理到帧")
        return

    print(f"共 {len(gif_frames)} 帧，保存 GIF...")
    os.makedirs(os.path.dirname(OUTPUT_GIF), exist_ok=True)
    gif_frames[0].save(
        OUTPUT_GIF,
        save_all=True,
        append_images=gif_frames[1:],
        duration=int(1000 / TARGET_FPS),
        loop=0,
        optimize=True
    )

    size_kb = os.path.getsize(OUTPUT_GIF) / 1024
    print(f"完成！输出: {OUTPUT_GIF}")
    print(f"文件大小: {size_kb:.2f} KB")


if __name__ == "__main__":
    main()
