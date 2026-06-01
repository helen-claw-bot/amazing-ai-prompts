#!/usr/bin/env python3
"""
recover_skipped_frames.py
遍历目录下每个子目录，找到 report.csv，
将 filename 为空但 similarity >= 阈值 的行补充截帧保存，并回写 report.csv。

用法:
    python recover_skipped_frames.py --dir /path/to/output_root --sim 0.3
    python recover_skipped_frames.py --dir E://AI//downloads//CHTT//S01E01_faces --sim 0.3
    
"""

import argparse
import csv
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def seek_and_write_ffmpeg(video_path, ts_sec, output_path):
    for hw_args in [["-hwaccel", "cuda"], []]:
        cmd = (
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
            + hw_args
            + ["-ss", f"{ts_sec:.3f}",
               "-i", str(video_path),
               "-frames:v", "1",
               "-q:v", "2",
               str(output_path)]
        )
        ret = subprocess.run(cmd, capture_output=True)
        if ret.returncode == 0:
            return True
    return False


def timecode_to_sec(timecode):
    """'MM:SS.ss' -> float seconds"""
    parts = timecode.split(":")
    return int(parts[0]) * 60 + float(parts[1])


def find_video(faces_dir):
    """从目录名推断视频文件，或从 batch_progress.json 查找。"""
    dir_name = faces_dir.name
    stem = dir_name[:-6] if dir_name.endswith("_faces") else dir_name
    parent = faces_dir.parent

    for ext in [".mp4", ".MP4", ".mkv", ".MKV", ".avi", ".AVI"]:
        candidate = parent / (stem + ext)
        if candidate.exists():
            return candidate

    progress_path = parent / "batch_progress.json"
    if progress_path.exists():
        with open(progress_path, "r", encoding="utf-8") as f:
            progress = json.load(f)
        target = str(faces_dir.resolve())
        for video_path_str, info in progress.items():
            if info.get("output_dir") == target:
                p = Path(video_path_str)
                if p.exists():
                    return p

    return None


def process_faces_dir(faces_dir, sim_thresh):
    csv_path = faces_dir / "report.csv"
    if not csv_path.exists():
        return

    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return

    targets = [
        r for r in rows
        if not r.get("filename", "").strip()
        and float(r.get("similarity", 0)) >= sim_thresh
    ]

    if not targets:
        print(f"  {faces_dir.name}: 无符合条件的帧（similarity≥{sim_thresh} 且 filename 为空）")
        return

    video_path = find_video(faces_dir)
    if video_path is None:
        print(f"  ⚠️  {faces_dir.name}: 找不到原始视频，跳过")
        return

    print(f"  {faces_dir.name}: {len(targets)} 帧待截取（视频: {video_path.name}）")

    new_filenames = {}
    failed = 0

    def _save(row):
        frame_idx = int(row["frame_idx"])
        timecode = row["timecode"]
        similarity = float(row["similarity"])
        face_count = int(row.get("face_count", 1))
        ts_sec = timecode_to_sec(timecode)
        multi_tag = f"_multi{face_count}" if face_count > 1 else ""
        fname = f"frame_{frame_idx:07d}_{timecode.replace(':', '-')}_sim{similarity:.2f}{multi_tag}.jpg"
        success = seek_and_write_ffmpeg(video_path, ts_sec, faces_dir / fname)
        return frame_idx, fname if success else None

    done = 0
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_save, row): row for row in targets}
        for future in as_completed(futures):
            frame_idx, fname = future.result()
            done += 1
            print(f"\r    [{done}/{len(targets)}] 截取中...", end="", flush=True)
            if fname:
                new_filenames[frame_idx] = fname
            else:
                failed += 1
                print(f"\n    ⚠️  frame {frame_idx} 截取失败")

    saved = len(new_filenames)
    print(f"\r    完成: {saved} 张保存，{failed} 张失败          ")

    if new_filenames:
        for row in rows:
            fi = int(row["frame_idx"])
            if fi in new_filenames:
                row["filename"] = new_filenames[fi]

        fieldnames = list(rows[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"    📊 report.csv 已回写 {saved} 行")


def main():
    parser = argparse.ArgumentParser(description="补充截取 report.csv 中被跳过但相似度达标的帧")
    parser.add_argument("--dir", required=True, help="输出根目录，包含各 *_faces 子目录")
    parser.add_argument("--sim", type=float, default=0.3, help="相似度阈值（默认 0.3）")
    args = parser.parse_args()

    base_dir = Path(args.dir)
    if not base_dir.exists():
        print(f"❌ 目录不存在: {base_dir}")
        return

    if (base_dir / "report.csv").exists():
        print(f"🔍 直接处理: {base_dir}  相似度阈值: {args.sim}")
        print("=" * 50)
        process_faces_dir(base_dir, args.sim)
    else:
        subdirs = [d for d in sorted(base_dir.iterdir()) if d.is_dir()]
        has_csv = [d for d in subdirs if (d / "report.csv").exists()]
        print(f"🔍 扫描: {base_dir}")
        print(f"   子目录共 {len(subdirs)} 个，含 report.csv 的 {len(has_csv)} 个，相似度阈值: {args.sim}")
        print("=" * 50)
        for subdir in subdirs:
            process_faces_dir(subdir, args.sim)

    print("\n✅ 全部完成")


if __name__ == "__main__":
    main()
