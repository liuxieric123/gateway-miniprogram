#!/usr/bin/env python3
"""
处理皮皮视频（优化版）：
1. 读取 MOV 视频
2. 缩放到合适尺寸
3. 用 rembg 抠出狗狗主体
4. 合成到纯色背景
5. 裁剪为正方形
6. 输出 MP4
"""

import os
import cv2
import numpy as np
from PIL import Image
import imageio
from rembg import remove, new_session
from tqdm import tqdm

# 配置
INPUT_PATH = "miniprogram/pipi.MOV"
OUTPUT_PATH = "miniprogram/images/pipi.mp4"
TARGET_SIZE = 540  # 输出正方形边长
TARGET_FPS = 12    # 输出帧率
BG_COLOR = (0xF7, 0xF6, 0xF3)  # 首页背景色 #F7F6F3
PROCESS_HEIGHT = 540  # 抠图前先缩放到这个高度，加快速度


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


def pad_to_square(img, size, bg_color):
    """用背景色填充到指定正方形"""
    h, w = img.shape[:2]
    if h == size and w == size:
        return img
    pad_h = size - h
    pad_w = size - w
    return np.pad(
        img,
        ((pad_h // 2, pad_h - pad_h // 2), (pad_w // 2, pad_w - pad_w // 2), (0, 0)),
        constant_values=bg_color[0]
    )


def process_video():
    print(f"正在读取视频: {INPUT_PATH}")

    reader = imageio.get_reader(INPUT_PATH)
    meta = reader.get_meta_data()
    fps = meta.get('fps', 30)
    n_frames = meta.get('nframes', None)
    size = meta.get('size', None)

    print(f"视频信息: 分辨率={size}, 帧率={fps}, 时长={meta.get('duration', 'unknown')}s")

    frame_interval = max(1, int(round(fps / TARGET_FPS)))
    session = new_session("u2net")

    frames = []
    frame_count = 0
    processed_count = 0

    print("开始处理帧...")
    for frame in tqdm(reader, total=n_frames):
        if frame_count % frame_interval != 0:
            frame_count += 1
            continue

        # 1. 缩放以加速抠图
        small = resize_keep_aspect(frame, PROCESS_HEIGHT)

        # 2. 如果缩放后宽度不够正方形，先 pad 成方形再抠
        # 实际上缩放到 540 高后宽度约为 304，不够 540
        # 我们直接 pad 到 540x540 再抠图，确保狗狗完整
        square_input = pad_to_square(small, TARGET_SIZE, BG_COLOR)

        # 3. 抠图
        rgba = remove(square_input, session=session)

        # 4. 合成到背景色
        bg = np.full((TARGET_SIZE, TARGET_SIZE, 3), BG_COLOR, dtype=np.uint8)
        alpha = rgba[:, :, 3].astype(np.float32) / 255.0
        rgb = rgba[:, :, :3].astype(np.float32)
        bg_f = bg.astype(np.float32)
        composed = (rgb * alpha[:, :, None] + bg_f * (1 - alpha[:, :, None])).astype(np.uint8)

        # 5. 中心裁剪出 540x540（已经满足）
        final = center_crop_square(composed, TARGET_SIZE)
        frames.append(final)

        frame_count += 1
        processed_count += 1

    reader.close()

    if not frames:
        print("没有处理到任何帧")
        return

    print(f"共处理 {processed_count} 帧，开始写入视频...")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    writer = imageio.get_writer(
        OUTPUT_PATH,
        fps=TARGET_FPS,
        codec='libx264',
        quality=8,
        pixelformat='yuv420p'
    )
    for frame in frames:
        writer.append_data(frame)
    writer.close()

    print(f"完成！输出: {OUTPUT_PATH}")
    size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
    print(f"文件大小: {size_mb:.2f} MB")


if __name__ == "__main__":
    process_video()
