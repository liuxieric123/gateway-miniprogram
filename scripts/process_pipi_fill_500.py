#!/usr/bin/env python3
"""
生成皮皮充满画面的 500x500 GIF：
1. 读取视频
2. 抠图
3. 找到皮皮主体边界框
4. 以主体为中心裁剪，并留少量边距
5. 输出 500x500 GIF
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
TARGET_SIZE = 480
TARGET_FPS = 8
PROCESS_HEIGHT = 960
PADDING_RATIO = 0.05  # 主体周围留 5% 边距


def resize_keep_aspect(frame, target_height):
    h, w = frame.shape[:2]
    scale = target_height / h
    new_w = int(w * scale)
    return cv2.resize(frame, (new_w, target_height), interpolation=cv2.INTER_AREA)


def get_subject_bbox(alpha, padding_ratio):
    """根据 alpha 找到主体边界框，并加边距"""
    mask = alpha > 30
    if not np.any(mask):
        return None

    ys, xs = np.where(mask)
    y1, y2 = ys.min(), ys.max()
    x1, x2 = xs.min(), xs.max()

    h, w = alpha.shape
    bbox_h = y2 - y1
    bbox_w = x2 - x1

    # 加边距
    pad_h = int(bbox_h * padding_ratio)
    pad_w = int(bbox_w * padding_ratio)

    # 扩展为正方形（以较长边为准）
    size = max(bbox_h + 2 * pad_h, bbox_w + 2 * pad_w)
    cy = (y1 + y2) // 2
    cx = (x1 + x2) // 2

    half = size // 2
    top = max(0, cy - half)
    left = max(0, cx - half)
    bottom = min(h, top + size)
    right = min(w, left + size)

    # 如果越界，调整
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

    print("开始处理帧...")
    for frame in tqdm(reader, total=n_frames):
        if frame_count % frame_interval != 0:
            frame_count += 1
            continue

        # 缩放加速抠图
        small = resize_keep_aspect(frame, PROCESS_HEIGHT)

        # pad 成方形
        h, w = small.shape[:2]
        size = max(h, w)
        pad_h = size - h
        pad_w = size - w
        padded = np.pad(
            small,
            ((pad_h // 2, pad_h - pad_h // 2), (pad_w // 2, pad_w - pad_w // 2), (0, 0)),
            constant_values=0
        )

        # 抠图
        rgba = remove(padded, session=session)
        alpha = rgba[:, :, 3]

        # 找到主体边界框
        bbox = get_subject_bbox(alpha, PADDING_RATIO)
        if bbox is None:
            # fallback：中心裁剪
            cy, cx = size // 2, size // 2
            half = TARGET_SIZE // 2
            bbox = (cy - half, cx - half, cy + half, cx + half)

        top, left, bottom, right = bbox
        cropped = rgba[top:bottom, left:right]

        # 缩放到目标尺寸
        img = Image.fromarray(cropped).resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)

        # 合成到背景色 #F7F6F3（避免小程序黑底问题）
        bg = Image.new('RGB', (TARGET_SIZE, TARGET_SIZE), (0xF7, 0xF6, 0xF3))
        bg.paste(img, mask=img.split()[3])

        # 转调色板（64 色控制文件大小）
        pil_p = bg.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        gif_frames.append(pil_p)

        frame_count += 1

    reader.close()

    if not gif_frames:
        print("没有处理到任何帧")
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
