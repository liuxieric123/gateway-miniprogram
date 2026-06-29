#!/usr/bin/env python3
"""
高清版皮皮 GIF 处理：
1. 读取原视频
2. 用 rembg 抠出狗狗
3. 直接输出透明背景 GIF
4. 尺寸更大、颜色更多
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
TARGET_SIZE = 480  # 放大尺寸
TARGET_FPS = 10
PROCESS_HEIGHT = 720  # 抠图前先缩放到这个高度，平衡速度和质量


def resize_keep_aspect(frame, target_height):
    """保持宽高比，缩放到指定高度"""
    h, w = frame.shape[:2]
    scale = target_height / h
    new_w = int(w * scale)
    return cv2.resize(frame, (new_w, target_height), interpolation=cv2.INTER_AREA)


def center_crop_square(img, size):
    """从图像中心裁剪出正方形"""
    h, w = img.shape[:2]
    min_dim = min(h, w)
    top = (h - min_dim) // 2
    left = (w - min_dim) // 2
    return img[top:top+min_dim, left:left+min_dim]


def pad_to_square(img, size):
    """用黑色填充到指定正方形（抠图后会变透明）"""
    h, w = img.shape[:2]
    if h == size and w == size:
        return img
    pad_h = size - h
    pad_w = size - w
    return np.pad(
        img,
        ((pad_h // 2, pad_h - pad_h // 2), (pad_w // 2, pad_w - pad_w // 2), (0, 0)),
        constant_values=0
    )


def main():
    print(f"读取视频: {INPUT_PATH}")
    reader = imageio.get_reader(INPUT_PATH)
    meta = reader.get_meta_data()
    fps = meta.get('fps', 30)
    n_frames = meta.get('nframes', None)

    print(f"视频信息: 分辨率={meta.get('size')}, 帧率={fps}, 时长={meta.get('duration', 'unknown')}s")

    frame_interval = max(1, int(round(fps / TARGET_FPS)))
    session = new_session("u2net")

    gif_frames = []
    frame_count = 0
    processed_count = 0

    print("开始处理帧...")
    for frame in tqdm(reader, total=n_frames):
        if frame_count % frame_interval != 0:
            frame_count += 1
            continue

        # 1. 缩放以加速抠图
        small = resize_keep_aspect(frame, PROCESS_HEIGHT)

        # 2. pad 成方形
        square_input = pad_to_square(small, PROCESS_HEIGHT)

        # 3. 抠图得到 RGBA
        rgba = remove(square_input, session=session)

        # 4. 裁剪为中心正方形（去掉 pad 的黑边）
        # 先根据 alpha 找到主体，然后以主体为中心裁剪
        alpha = rgba[:, :, 3]
        mask = alpha > 30
        if np.any(mask):
            ys, xs = np.where(mask)
            cy = int(np.mean(ys))
            cx = int(np.mean(xs))
        else:
            cy, cx = PROCESS_HEIGHT // 2, PROCESS_HEIGHT // 2

        half = PROCESS_HEIGHT // 2
        top = max(0, min(cy - half, PROCESS_HEIGHT - PROCESS_HEIGHT))
        left = max(0, min(cx - half, PROCESS_HEIGHT - PROCESS_HEIGHT))
        # 实际上直接中心裁剪就行，因为 pad 是均匀的
        cropped = center_crop_square(rgba, PROCESS_HEIGHT)

        # 5. 缩放到目标尺寸
        img = Image.fromarray(cropped)
        img = img.resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)
        resized = np.array(img)

        # 6. 转为 GIF 调色板模式
        pil_rgba = Image.fromarray(resized)
        pil_p = pil_rgba.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=255)
        gif_frames.append(pil_p)

        frame_count += 1
        processed_count += 1

    reader.close()

    if not gif_frames:
        print("没有处理到任何帧")
        return

    print(f"共处理 {processed_count} 帧，保存 GIF...")

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
