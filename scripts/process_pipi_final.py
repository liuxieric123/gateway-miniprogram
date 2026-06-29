#!/usr/bin/env python3
"""
最终版皮皮 GIF：
- 400x400
- 皮皮充满画面
- 深土黄色调
- 背景 #F7F6F3
"""

import os
import cv2
import numpy as np
from PIL import Image
import imageio
from rembg import remove, new_session
from tqdm import tqdm

INPUT_PATH = "miniprogram/pipi.mov"
OUTPUT_GIF = "miniprogram/images/pipi.gif"
TARGET_SIZE = 400
TARGET_FPS = 8
PROCESS_HEIGHT = 960
PADDING_RATIO = 0.04
BG_COLOR = (0xF7, 0xF6, 0xF3)


def resize_keep_aspect(frame, target_height):
    h, w = frame.shape[:2]
    scale = target_height / h
    new_w = int(w * scale)
    return cv2.resize(frame, (new_w, target_height), interpolation=cv2.INTER_AREA)


def get_subject_bbox(alpha, padding_ratio):
    mask = alpha > 30
    if not np.any(mask):
        return None
    ys, xs = np.where(mask)
    y1, y2 = ys.min(), ys.max()
    x1, x2 = xs.min(), xs.max()
    h, w = alpha.shape
    bbox_h = y2 - y1
    bbox_w = x2 - x1
    pad_h = int(bbox_h * padding_ratio)
    pad_w = int(bbox_w * padding_ratio)
    size = max(bbox_h + 2 * pad_h, bbox_w + 2 * pad_w)
    cy = (y1 + y2) // 2
    cx = (x1 + x2) // 2
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


def adjust_color(rgb):
    """调整为深土黄色：提高饱和度、降低亮度、色相偏向暖黄"""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)

    # 色相：整体往黄色/橙色偏移一点
    h = hsv[:, :, 0]
    # 黄色区域(15-45)保持，绿色区域(45-75)往黄色拉
    green_mask = (h > 40) & (h < 75)
    h[green_mask] = np.clip(h[green_mask] - 15, 20, 40)
    # 整体略微往暖色偏移
    h = np.clip(h - 3, 0, 179)
    hsv[:, :, 0] = h

    # 饱和度：提高更多
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.40, 0, 255)

    # 亮度：降低更多，显得更深
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * 0.82, 0, 255)

    rgb = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

    # 额外 RGB 微调：R 略增，G 略降，B 降低，让颜色更暖更深
    rgb = rgb.astype(np.float32)
    rgb[:, :, 0] = np.clip(rgb[:, :, 0] * 1.05, 0, 255)
    rgb[:, :, 1] = np.clip(rgb[:, :, 1] * 0.95, 0, 255)
    rgb[:, :, 2] = np.clip(rgb[:, :, 2] * 0.82, 0, 255)

    return rgb.astype(np.uint8)


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

    print("开始处理帧...")
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

        bbox = get_subject_bbox(alpha, PADDING_RATIO)
        if bbox is None:
            cy, cx = size // 2, size // 2
            half = TARGET_SIZE // 2
            bbox = (cy - half, cx - half, cy + half, cy + half)

        top, left, bottom, right = bbox
        cropped = rgba[top:bottom, left:right]

        # 缩放到目标尺寸
        img = Image.fromarray(cropped).resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)
        cropped_rgba = np.array(img)

        # 调整颜色
        rgb = cropped_rgba[:, :, :3]
        rgb = adjust_color(rgb)
        cropped_rgba[:, :, :3] = rgb

        # 合成到背景色
        pil_rgba = Image.fromarray(cropped_rgba)
        bg = Image.new('RGB', (TARGET_SIZE, TARGET_SIZE), BG_COLOR)
        bg.paste(pil_rgba, mask=pil_rgba.split()[3])

        # 转调色板
        pil_p = bg.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        gif_frames.append(pil_p)

        frame_count += 1

    reader.close()

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
