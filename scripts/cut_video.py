#!/usr/bin/env python3
"""
cut_video.py
用 ffmpeg 快速切割视频片段

依赖: ffmpeg（系统级，不是Python包）
安装: brew install ffmpeg

用法:
    # 交互模式（推荐新手）
    python cut_video.py

    # 命令行模式
    python cut_video.py --video input.mp4 --start 00:10:30 --end 00:15:45 --output clip.mp4

    # 批量切割（编辑脚本底部的 CLIPS 列表后运行）
    python cut_video.py --batch --video input.mp4
"""

import argparse
import os
import shutil
import subprocess
import sys


def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        print("❌ 未找到 ffmpeg，请先安装：")
        print("   Mac:   brew install ffmpeg")
        print("   Linux: sudo apt install ffmpeg")
        sys.exit(1)


def cut_clip(video_in, start, end, output, overwrite=True):
    """
    切割视频片段（-c copy 模式，不重新编码，速度极快）

    video_in : 输入视频路径
    start    : 开始时间，格式 HH:MM:SS 或 MM:SS 或秒数
    end      : 结束时间（同上）
    output   : 输出文件路径
    """
    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    cmd = [
        "ffmpeg",
        "-ss", str(start),
        "-i", video_in,
        "-to", str(end),
        "-c", "copy",        # 直接复制流，不重新编码，快！
        output,
    ]
    if overwrite:
        cmd.append("-y")

    print(f"  ✂️  {start} → {end}  →  {output}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ❌ 失败: {result.stderr[-300:]}")
        return False
    size_mb = os.path.getsize(output) / 1024 / 1024
    print(f"  ✅ 完成，{size_mb:.1f} MB")
    return True


def interactive_mode():
    """交互模式：逐步引导输入"""
    print("=" * 50)
    print("📹 视频切割工具（交互模式）")
    print("=" * 50)

    video = input("\n输入视频文件路径: ").strip().strip("'\"")
    if not os.path.exists(video):
        print(f"❌ 文件不存在: {video}")
        sys.exit(1)

    output_dir = input("输出目录 [默认: ./clips]: ").strip() or "./clips"

    print("\n输入片段（时间格式：HH:MM:SS 或 MM:SS）")
    print("留空开始时间 = 跳出循环\n")

    clips = []
    i = 1
    while True:
        start = input(f"片段 {i} 开始时间（回车结束）: ").strip()
        if not start:
            break
        end = input(f"片段 {i} 结束时间: ").strip()
        name = input(f"输出文件名 [默认: clip_{i:02d}.mp4]: ").strip() or f"clip_{i:02d}.mp4"
        clips.append((start, end, name))
        i += 1

    if not clips:
        print("没有输入任何片段，退出")
        sys.exit(0)

    print(f"\n开始切割 {len(clips)} 个片段...")
    success = 0
    for start, end, name in clips:
        out = os.path.join(output_dir, name)
        if cut_clip(video, start, end, out):
            success += 1

    print(f"\n✅ 完成：{success}/{len(clips)} 个片段成功 → {output_dir}/")


def batch_mode(video, output_dir, clips):
    """批量模式：处理预定义的 CLIPS 列表"""
    print(f"📹 批量切割：{len(clips)} 个片段")
    success = 0
    for start, end, name in clips:
        out = os.path.join(output_dir, name)
        if cut_clip(video, start, end, out):
            success += 1
    print(f"\n✅ 完成：{success}/{len(clips)} 个片段 → {output_dir}/")


# ──────────────────────────────────────────────
# 批量模式配置区：直接编辑这里，然后跑
#   python cut_video.py --batch --video your_video.mp4
# ──────────────────────────────────────────────
BATCH_OUTPUT_DIR = "./clips"
BATCH_CLIPS = [
    # (开始时间,    结束时间,    输出文件名)
    ("00:05:00", "00:08:30", "clip_01.mp4"),
    ("00:23:10", "00:27:00", "clip_02.mp4"),
    ("00:35:45", "00:38:20", "clip_03.mp4"),
    # 继续添加...
]
# ──────────────────────────────────────────────


def main():
    check_ffmpeg()

    parser = argparse.ArgumentParser(description="ffmpeg 视频切割工具")
    parser.add_argument("--video", help="输入视频路径")
    parser.add_argument("--start", help="开始时间（HH:MM:SS）")
    parser.add_argument("--end", help="结束时间（HH:MM:SS）")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--batch", action="store_true", help="批量模式（使用脚本内 BATCH_CLIPS 列表）")
    args = parser.parse_args()

    # 单段命令行模式
    if args.video and args.start and args.end and args.output:
        cut_clip(args.video, args.start, args.end, args.output)

    # 批量模式
    elif args.batch and args.video:
        batch_mode(args.video, BATCH_OUTPUT_DIR, BATCH_CLIPS)

    # 交互模式
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
