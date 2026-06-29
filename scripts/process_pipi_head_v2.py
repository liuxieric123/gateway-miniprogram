#!/usr/bin/env python3
"""重新生成皮皮头部 GIF：透明背景、清理边缘杂斑、5fps、300x300"""

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
TARGET_FPS = 5
PROCESS_HEIGHT = 720
HEAD_CROP_RATIO = 0.55


def resize_keep_aspect(frame, target_height):
    h, w = frame.shape[:2]
    scale = target_height / h
    new_w = int(w * scale)
    return cv2.resize(frame, (new_w, target_height), interpolation=cv2.INTER_AREA)


def clean_alpha(alpha):
    """清理 alpha 通道：去小噪点、保留最大连通区域"""
    # 二值化
    binary = (alpha > 60).astype(np.uint8) * 255

    # 形态学开运算去小噪点
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

    # 闭运算填补小洞
    kernel2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel2, iterations=1)

    # 只保留最大连通区域
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(cleaned, connectivity=8)
    if num_labels > 1:
        # 跳过背景（label 0），找最大的前景区域
        largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        mask = (labels == largest_label).astype(np.uint8) * 255
    else:
        mask = cleaned

    # 边缘稍微羽化
    mask = cv2.GaussianBlur(mask, (5, 5), 0)

    return mask.astype(np.float32) / 255.0


def get_head_bbox(alpha, head_ratio=0.45):
    mask = alpha > 0.3
    if not np.any(mask):
        return None
    ys, xs = np.where(mask)
    y1, y2 = ys.min(), ys.max()
    x1, x2 = xs.min(), xs.max()
    h, w = alpha.shape
    bbox_h = y2 - y1
    bbox_w = x2 - x1
    head_h = int(bbox_h * head_ratio)
    # 头部宽度只取主体的 60%，靠左一点，去掉右侧的木板/柱子
    head_w = int(bbox_w * 0.60)
    cy = y1 + head_h // 2
    cx = x1 + head_w // 2  # 中心偏左
    size = max(head_h, head_w)
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

        # 清理 alpha
        alpha_clean = clean_alpha(alpha)

        # 应用清理后的 alpha
        rgba_clean = rgba.copy()
        rgba_clean[:, :, 3] = (alpha_clean * 255).astype(np.uint8)

        bbox = get_head_bbox(alpha_clean)
        if bbox is None:
            frame_count += 1
            continue

        top, left, bottom, right = bbox
        head = rgba_clean[top:bottom, left:right]

        img = Image.fromarray(head).resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)

        # 透明背景 GIF
        pil_p = img.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=255)
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
        transparency=0,
        disposal=2,
        optimize=True
    )

    size_kb = os.path.getsize(OUTPUT_GIF) / 1024
    print(f"完成！输出: {OUTPUT_GIF}")
    print(f"文件大小: {size_kb:.2f} KB")


if __name__ == "__main__":
    main()
