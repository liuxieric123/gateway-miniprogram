#!/usr/bin/env python3
"""测试皮皮视频的第一帧抠图效果（改进版）"""

import os
import numpy as np
from PIL import Image
import imageio
from rembg import remove

INPUT_PATH = "miniprogram/皮皮.MOV"
OUTPUT_PATH = "scripts/pipi_test_first_frame_v2.png"
BG_COLOR = (0xF7, 0xF6, 0xF3)
TARGET_SIZE = 540


def crop_around_subject(img, alpha, target_size):
    """根据 alpha 通道找到主体中心，并裁剪为正方形"""
    # alpha 大于阈值的像素坐标
    mask = alpha > 128
    if not np.any(mask):
        #  fallback：中心裁剪
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

    # 计算裁剪区域，确保不越界
    top = max(0, min(cy - half, h - target_size))
    left = max(0, min(cx - half, w - target_size))

    return img[top:top+target_size, left:left+target_size]


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
    rgba = remove(
        frame_rgb,
        alpha_matting=True,
        alpha_matting_foreground_threshold=240,
        alpha_matting_background_threshold=10,
        alpha_matting_erode_size=10
    )

    # 合成到背景色
    bg = np.full((rgba.shape[0], rgba.shape[1], 3), BG_COLOR, dtype=np.uint8)
    alpha = rgba[:, :, 3].astype(np.float32) / 255.0
    rgb = rgba[:, :, :3].astype(np.float32)
    bg_f = bg.astype(np.float32)
    composed = (rgb * alpha[:, :, None] + bg_f * (1 - alpha[:, :, None])).astype(np.uint8)

    # 按主体中心裁剪
    cropped = crop_around_subject(composed, rgba[:, :, 3], TARGET_SIZE)

    # 如果裁剪后不够大，pad
    if cropped.shape[0] < TARGET_SIZE or cropped.shape[1] < TARGET_SIZE:
        pad_h = TARGET_SIZE - cropped.shape[0]
        pad_w = TARGET_SIZE - cropped.shape[1]
        cropped = np.pad(
            cropped,
            ((pad_h // 2, pad_h - pad_h // 2), (pad_w // 2, pad_w - pad_w // 2), (0, 0)),
            constant_values=BG_COLOR[0]
        )

    # 保存
    img = Image.fromarray(cropped)
    img = img.resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)
    img.save(OUTPUT_PATH)

    print(f"测试图已保存: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
