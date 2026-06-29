#!/usr/bin/env python3
"""测试皮皮视频的第一帧抠图效果"""

import os
import numpy as np
from PIL import Image
import imageio
from rembg import remove

INPUT_PATH = "miniprogram/皮皮.MOV"
OUTPUT_PATH = "scripts/pipi_test_first_frame.png"
BG_COLOR = (0xF7, 0xF6, 0xF3)

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

    print("正在抠图（首次会下载模型，可能需要几分钟）...")
    rgba = remove(frame_rgb)

    # 合成到背景色
    bg = np.full((rgba.shape[0], rgba.shape[1], 3), BG_COLOR, dtype=np.uint8)
    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
    rgb = rgba[:, :, :3].astype(np.float32)
    bg_f = bg.astype(np.float32)
    composed = (rgb * alpha + bg_f * (1 - alpha)).astype(np.uint8)

    # 裁剪为正方形
    h, w = composed.shape[:2]
    min_dim = min(h, w)
    top = (h - min_dim) // 2
    left = (w - min_dim) // 2
    cropped = composed[top:top+min_dim, left:left+min_dim]

    # 保存
    img = Image.fromarray(cropped)
    img.thumbnail((540, 540), Image.Resampling.LANCZOS)
    img.save(OUTPUT_PATH)

    print(f"测试图已保存: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
