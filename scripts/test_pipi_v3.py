#!/usr/bin/env python3
"""测试皮皮视频的第一帧抠图效果（v3：形态学清理）"""

import os
import cv2
import numpy as np
from PIL import Image
import imageio
from rembg import remove

INPUT_PATH = "miniprogram/皮皮.MOV"
OUTPUT_PATH = "scripts/pipi_test_first_frame_v3.png"
BG_COLOR = (0xF7, 0xF6, 0xF3)
TARGET_SIZE = 540


def crop_around_subject(img, alpha, target_size):
    """根据 alpha 通道找到主体中心，并裁剪为正方形"""
    mask = alpha > 30
    if not np.any(mask):
        h, w = img.shape[:2]
        min_dim = min(h, w)
        top = (h - min_dim) // 2
        left = (w - min_dim) // 2
        return img[top:top+min_dim, left:left+min_dim]

    ys, xs = np.where(mask)
    cy = int(np.mean(ys))
    cx = int(np.mean(xs))

    h, w = img.shape[:2]
    half = target_size // 2

    top = max(0, min(cy - half, h - target_size))
    left = max(0, min(cx - half, w - target_size))

    return img[top:top+target_size, left:left+target_size]


def clean_alpha(alpha):
    """清理 alpha 通道：阈值 + 形态学开运算去噪"""
    alpha = alpha.astype(np.uint8)

    # 二值化
    _, binary = cv2.threshold(alpha, 60, 255, cv2.THRESH_BINARY)

    # 形态学开运算去小噪点
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

    # 轻微闭运算填补主体小洞
    kernel2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel2, iterations=1)

    # 边缘羽化
    cleaned = cv2.GaussianBlur(cleaned, (5, 5), 0)

    return cleaned.astype(np.float32) / 255.0


def main():
    print(f"读取视频: {INPUT_PATH}")
    reader = imageio.get_reader(INPUT_PATH)
    meta = reader.get_meta_data()
    print(f"视频信息: {meta}")

    print("读取第一帧...")
    frame = reader.get_data(0)
    reader.close()

    if frame.shape[2] == 4:
        frame_rgb = frame[:, :, :3]
    else:
        frame_rgb = frame

    print("正在抠图...")
    rgba = remove(frame_rgb)

    # 清理 alpha
    alpha_clean = clean_alpha(rgba[:, :, 3])

    # 合成到背景色
    bg = np.full((rgba.shape[0], rgba.shape[1], 3), BG_COLOR, dtype=np.uint8)
    rgb = rgba[:, :, :3].astype(np.float32)
    bg_f = bg.astype(np.float32)
    composed = (rgb * alpha_clean[:, :, None] + bg_f * (1 - alpha_clean[:, :, None])).astype(np.uint8)

    # 按主体中心裁剪
    alpha_uint8 = (alpha_clean * 255).astype(np.uint8)
    cropped = crop_around_subject(composed, alpha_uint8, TARGET_SIZE)

    # pad
    if cropped.shape[0] < TARGET_SIZE or cropped.shape[1] < TARGET_SIZE:
        pad_h = TARGET_SIZE - cropped.shape[0]
        pad_w = TARGET_SIZE - cropped.shape[1]
        cropped = np.pad(
            cropped,
            ((pad_h // 2, pad_h - pad_h // 2), (pad_w // 2, pad_w - pad_w // 2), (0, 0)),
            constant_values=BG_COLOR[0]
        )

    img = Image.fromarray(cropped)
    img = img.resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)
    img.save(OUTPUT_PATH)

    print(f"测试图已保存: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
