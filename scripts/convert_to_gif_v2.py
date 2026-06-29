#!/usr/bin/env python3
"""把处理好的皮皮视频转成高清透明背景 GIF"""

import os
import numpy as np
from PIL import Image
import imageio

INPUT_PATH = "miniprogram/images/pipi.mp4"
OUTPUT_PATH = "miniprogram/images/pipi.gif"
BG_COLOR = np.array([0xF7, 0xF6, 0xF3])
COLOR_THRESHOLD = 20  # 颜色差异阈值，越小越严格
TARGET_SIZE = 480     # GIF 尺寸放大
TARGET_FPS = 10


def make_transparent(frame, bg_color, threshold):
    """把接近背景色的像素设为透明"""
    diff = np.abs(frame[:, :, :3].astype(np.int16) - bg_color.astype(np.int16))
    mask = np.all(diff < threshold, axis=2)

    rgba = np.zeros((frame.shape[0], frame.shape[1], 4), dtype=np.uint8)
    rgba[:, :, :3] = frame[:, :, :3]
    rgba[:, :, 3] = np.where(mask, 0, 255)
    return rgba


def main():
    print(f"读取视频: {INPUT_PATH}")
    reader = imageio.get_reader(INPUT_PATH)
    meta = reader.get_meta_data()
    fps = meta.get('fps', 12)

    frame_interval = max(1, int(round(fps / TARGET_FPS)))

    gif_frames = []

    for i, frame in enumerate(reader):
        if i % frame_interval != 0:
            continue

        # 缩放到目标尺寸
        img = Image.fromarray(frame)
        img = img.resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)
        small = np.array(img)

        # 变透明
        rgba = make_transparent(small, BG_COLOR, COLOR_THRESHOLD)
        pil_rgba = Image.fromarray(rgba)

        # 转为 P 模式调色板
        pil_p = pil_rgba.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=255)
        gif_frames.append(pil_p)

    reader.close()

    if not gif_frames:
        print("没有帧")
        return

    print(f"共 {len(gif_frames)} 帧，保存 GIF...")

    gif_frames[0].save(
        OUTPUT_PATH,
        save_all=True,
        append_images=gif_frames[1:],
        duration=int(1000 / TARGET_FPS),
        loop=0,
        transparency=0,
        disposal=2,
        optimize=True
    )

    size_kb = os.path.getsize(OUTPUT_PATH) / 1024
    print(f"完成！输出: {OUTPUT_PATH}")
    print(f"文件大小: {size_kb:.2f} KB")


if __name__ == "__main__":
    main()
