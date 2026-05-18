#!/usr/bin/env python3
"""
cut_video.py
用 ffmpeg 快速切割视频片段

依赖: ffmpeg（系统级，不是Python包）
安装:
    Windows: winget install ffmpeg  或  choco install ffmpeg
    Mac:     brew install ffmpeg
    Linux:   sudo apt install ffmpeg

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
        print("   Windows: winget install ffmpeg  或  choco install ffmpeg")
        print("            或从 https://www.gyan.dev/ffmpeg/builds/ 下载后加入 PATH")
        print("   Mac:     brew install ffmpeg")
        print("   Linux:   sudo apt install ffmpeg")
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
        "-to", str(end),
        "-i", video_in,
        "-c", "copy",        # 直接复制流，不重新编码，快！
    ]
    if overwrite:
        cmd.append("-y")
    cmd.append(output)

    print(f"  ✂️  {start} → {end}  →  {output}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ❌ 失败: {result.stderr[-300:]}")
        return False
    size_mb = os.path.getsize(output) / 1024 / 1024
    print(f"  ✅ 完成，{size_mb:.1f} MB")
    return True


def batch_mode(video, output_dir, clips):
    """批量模式：处理预定义的 CLIPS 列表"""
    video_stem = os.path.splitext(os.path.basename(video))[0]
    print(f"📹 批量切割：{len(clips)} 个片段")
    success = 0
    for start, end, name in clips:
        stem, ext = os.path.splitext(name)
        out = os.path.join(output_dir, f"{video_stem}_{stem}{ext}")
        if cut_clip(video, start, end, out):
            success += 1
    print(f"\n✅ 完成：{success}/{len(clips)} 个片段 → {output_dir}/")


# ──────────────────────────────────────────────
# 批量模式配置区：直接编辑这里，然后跑
#   python cut_video.py --batch --video your_video.mp4
#   python scripts\cut_video.py --batch --video "E:\AI\downloads\SHZY_LDF\01.mp4"
#   python scripts\cut_video.py --batch --video "E:\AI\downloads\CHTT\S01E01.mp4"
# ──────────────────────────────────────────────
BATCH_CLIPS = [
    # (开始时间,    结束时间,    后缀名)  → 输出为 原始视频名_后缀名
    ("00:00:00", "00:03:15", "clip_02.mp4"),
    # ("00:27:08", "00:29:36", "clip_02.mp4"),
    # ("00:30:00", "00:31:59", "clip_03.mp4"),
    # ("01:42:12", "01:52:22", "clip_04.mp4"),
]

# 捕风捉影
# 00:04:50 - 00:18:38
# 00:27:08 - 00:29:36
# 00:30:00 - 00:31:59
# 01:42:12 - 01:52:22

# 李东方


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
        output_dir = os.path.join(os.path.dirname(os.path.abspath(args.video)), "clips")
        batch_mode(args.video, output_dir, BATCH_CLIPS)

    # 打印帮助信息
    else:
        print("❌ 参数不足，请使用 --help 查看用法")
        parser.print_help()
        


if __name__ == "__main__":
    main()
