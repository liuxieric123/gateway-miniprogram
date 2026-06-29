#!/usr/bin/env python3
"""生成 720x720 高清透明皮皮 GIF"""

import os
import numpy as np
from PIL import Image
import imageio
from rembg import remove, new_session
from tqdm import tqdm

INPUT_PATH = "miniprogram/pipi.mov"
OUTPUT_GIF = "miniprogram/images/pipi.gif"
TARGET_SIZE = 720
TARGET_FPS = 8
PROCESS_HEIGHT = 960


def resize_keep_aspect(frame, target_height):
    h, w = frame.shape[:2]
    scale = target_height / h
    new_w = int(w * scale)
    return np.array(Image.fromarray(frame).resize((new_w, target_height), Image.Resampling.LANCZOS))


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

        # 缩放
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

        # 以主体为中心裁剪
        alpha = rgba[:, :, 3]
        mask = alpha > 30
        if np.any(mask):
            ys, xs = np.where(mask)
            cy, cx = int(np.mean(ys)), int(np.mean(xs))
        else:
            cy, cx = size // 2, size // 2

        half = size // 2
        top = max(0, cy - half)
        left = max(0, cx - half)
        cropped = rgba[top:top+size, left:left+size]

        # 缩放到目标尺寸
        img = Image.fromarray(cropped).resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)

        # 转调色板
        pil_p = img.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=255)
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
        transparency=0,
        disposal=2,
        optimize=True
    )

    size_kb = os.path.getsize(OUTPUT_GIF) / 1024
    print(f"完成！输出: {OUTPUT_GIF}")
    print(f"文件大小: {size_kb:.2f} KB")


if __name__ == "__main__":
    main()
