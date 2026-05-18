#!/usr/bin/env python3
"""
extract_face_frames.py
从视频中提取指定人物的优质人脸帧

依赖安装:
    # CPU 模式
    pip install insightface opencv-python onnxruntime numpy
    # GPU 模式（NVIDIA CUDA，推荐）
    pip install insightface opencv-python onnxruntime-gpu numpy

用法（单视频）:
    python extract_face_frames.py \
        --video /path/to/video.mp4 \
        --refs /path/to/ref1.jpg /path/to/ref2.jpg \
        --output ./output_frames \
        --top 100 --fps 1 --solo

用法（批量目录）:
    python extract_face_frames.py \
        --dir /path/to/videos/ \
        --refs /path/to/ref1.jpg /path/to/ref2.jpg \
        --output ./output_frames \
        --top 100 --fps 1 --solo

参数说明:
    --video     输入视频路径（与 --dir 二选一）
    --dir       视频目录，自动遍历所有 .mp4 文件（与 --video 二选一）
    --refs      目标人物参考照片（1-5张，正脸清晰最佳）
    --output    输出目录（默认：视频所在目录下的 {视频名}_faces；批量时为各视频子目录的父目录）
    --top       保留评分最高的N张帧（默认100）
    --fps       每秒采样帧数（默认1，40min视频约2400帧）
    --sim       人脸相似度阈值（默认0.45，越高越严格）
    --angle     最大允许偏角°（默认40）
    --blur      最低清晰度分（默认80，Laplacian方差）
    --min-face  人脸短边最小像素数（默认100px，过小的脸无法用于训练）
    --solo          只保留目标人物单独出现的帧（过滤多人画面）
    --skip-intro    跳过片头的秒数（默认0，例如 --skip-intro 90 跳过前1.5分钟）
    --skip-outro    跳过片尾的秒数（默认0，例如 --skip-outro 60 跳过最后1分钟）
"""

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# 让 onnxruntime-gpu 能找到 PyTorch 自带的 CUDA 12 DLL
_TORCH_LIB = Path(r"C:\Users\home\Documents\ComfyUI\.venv\Lib\site-packages\torch\lib")
if _TORCH_LIB.exists():
    os.environ["PATH"] = str(_TORCH_LIB) + os.pathsep + os.environ.get("PATH", "")
    os.add_dll_directory(str(_TORCH_LIB))

import cv2
import numpy as np

try:
    import insightface
    from insightface.app import FaceAnalysis
except ImportError:
    print("❌ 请先安装依赖: pip install insightface opencv-python onnxruntime numpy")
    sys.exit(1)


def load_face_app(model_dir=None):
    """初始化 InsightFace，使用 buffalo_l 模型（含检测+识别）"""
    import onnxruntime as ort
    available = ort.get_available_providers()
    if "CUDAExecutionProvider" not in available:
        print("❌ CUDA 不可用，当前环境支持的 provider:", available)
        sys.exit(1)
    # 不加 CPUExecutionProvider，防止 session 级别静默 fallback
    providers = ["CUDAExecutionProvider"]
    print("🚀 使用 GPU (CUDA) 加速")
    kwargs = {"name": "buffalo_l", "providers": providers}
    if model_dir:
        kwargs["root"] = model_dir
        print(f"📁 模型目录: {model_dir}")
    app = FaceAnalysis(**kwargs)
    app.prepare(ctx_id=0, det_size=(640, 640))
    # 验证各子模型确实挂载在 CUDA EP 上
    for name, model in app.models.items():
        session = getattr(model, "session", None)
        if session is None:
            continue
        active = session.get_providers()
        if "CUDAExecutionProvider" not in active:
            print(f"❌ 模型 {name} 未使用 CUDA，实际 provider: {active}")
            sys.exit(1)
    print(f"   已验证 {len(app.models)} 个子模型均在 GPU 上运行")
    return app


def get_face_embedding(app, img_path):
    """从参考照片提取人脸特征向量"""
    img = cv2.imread(str(img_path))
    if img is None:
        print(f"⚠️  无法读取参考图: {img_path}")
        return None
    faces = app.get(img)
    if not faces:
        print(f"⚠️  未检测到人脸: {img_path}")
        return None
    # 取置信度最高的人脸
    face = max(faces, key=lambda f: f.det_score)
    return face.normed_embedding


def cosine_similarity(a, b):
    """余弦相似度，范围 -1 到 1，越接近1越像"""
    return float(np.dot(a, b))


def laplacian_variance(img_gray):
    """清晰度评分：Laplacian方差，越高越清晰"""
    return cv2.Laplacian(img_gray, cv2.CV_64F).var()


def estimate_yaw(face):
    """从 InsightFace 关键点估算水平偏角（粗略）"""
    kps = face.kps  # 5个关键点: 左眼, 右眼, 鼻尖, 左嘴角, 右嘴角
    left_eye, right_eye = kps[0], kps[1]
    nose = kps[2]
    eye_center_x = (left_eye[0] + right_eye[0]) / 2
    eye_width = abs(right_eye[0] - left_eye[0])
    if eye_width < 1:
        return 90.0
    offset = nose[0] - eye_center_x
    yaw = abs(offset / eye_width) * 90
    return min(yaw, 90.0)



def iter_frames_ffmpeg(video_path, sample_fps, start_sec, clip_dur, det_w, det_h):
    """Stage 1: yield (local_idx, frame_bgr) at det_w×det_h via FFmpeg pipe.
    Tries CUDA hw-decode first, falls back to software."""
    frame_bytes = det_w * det_h * 3
    for attempt, hw_args in enumerate([["-hwaccel", "cuda"], []]):
        cmd = (
            ["ffmpeg", "-hide_banner", "-loglevel", "error"]
            + hw_args
            + ["-ss", f"{start_sec:.3f}",
               "-i", str(video_path),
               "-t", f"{clip_dur:.3f}",
               "-vf", f"fps={sample_fps},scale={det_w}:{det_h}",
               "-f", "rawvideo", "-pix_fmt", "bgr24", "pipe:1"]
        )
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        local_idx = 0
        try:
            while True:
                raw = proc.stdout.read(frame_bytes)
                if len(raw) < frame_bytes:
                    break
                yield local_idx, np.frombuffer(raw, dtype=np.uint8).reshape((det_h, det_w, 3))
                local_idx += 1
        finally:
            proc.stdout.close()
            proc.wait()
        if local_idx > 0 or attempt == 1:
            return
        print("   ⚠️  CUDA 硬件解码失败，回退到软件解码...")


def seek_and_write_ffmpeg(video_path, ts_sec, output_path):
    """Stage 2: seek to ts_sec, write one JPEG directly via FFmpeg — no Python pipe."""
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


def process_video(app, video_path, ref_embeddings, output_dir, top_n, sample_fps, sim_thresh, angle_thresh, blur_thresh, min_face_px, solo, overwrite=True, skip_intro_sec=0.0, skip_outro_sec=0.0):
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        if not overwrite:
            print(f"❌ 输出目录非空: {output_dir}，请用 --overwrite 覆盖或指定其他目录")
            sys.exit(1)
        shutil.rmtree(output_dir)
        print(f"🗑  已清空旧目录: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 只用 cap 读元数据，读完即释放
    cap = cv2.VideoCapture(str(video_path), cv2.CAP_FFMPEG)
    if not cap.isOpened():
        print(f"❌ 无法打开视频: {video_path}")
        sys.exit(1)
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    vid_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    vid_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    duration_sec = total_frames / video_fps
    start_sec = skip_intro_sec
    clip_dur = max(0.0, duration_sec - skip_outro_sec - start_sec)
    end_sec = start_sec + clip_dur
    total_to_process = int(clip_dur * sample_fps)

    # 检测用分辨率：高不超过 720，宽等比对齐偶数
    det_h = min(vid_h, 720)
    det_w = int(vid_w * det_h / vid_h) & ~1
    scale_to_orig = vid_h / det_h  # det 坐标 → 原始分辨率坐标的倍数

    print(f"📹 视频: {video_path}")
    print(f"   时长: {duration_sec/60:.1f} 分钟 | 总帧数: {total_frames} | 采样: {sample_fps}fps")
    if skip_intro_sec > 0:
        print(f"   跳过片头: {skip_intro_sec:.1f}s（从 {start_sec:.1f}s 开始）")
    if skip_outro_sec > 0:
        print(f"   跳过片尾: {skip_outro_sec:.1f}s（到 {end_sec:.1f}s 结束）")
    print(f"   预计处理帧数: {total_to_process}")
    if det_h < vid_h:
        print(f"   分辨率: {vid_w}×{vid_h} | Stage1 检测 {det_w}×{det_h}，Stage2 保存原始分辨率")
    else:
        print(f"   分辨率: {vid_w}×{vid_h}（无需降采样）")
    if solo:
        print(f"   模式: 单人独照（多人帧将跳过）")
    print(f"🔍 Stage1：扫描 + 过滤...")

    results = []
    processed = 0
    skipped_multi = 0
    start_time = time.time()
    _t = {"detect": 0.0, "filter": 0.0}

    for local_idx, frame in iter_frames_ffmpeg(video_path, sample_fps, start_sec, clip_dur, det_w, det_h):
        processed += 1
        ts = start_sec + local_idx / sample_fps
        actual_frame_idx = int(ts * video_fps)

        elapsed = time.time() - start_time
        fps_rate = processed / elapsed if elapsed > 0 else 0
        remaining = (total_to_process - processed) / fps_rate if fps_rate > 0 else 0
        pct = processed / total_to_process * 100 if total_to_process > 0 else 0
        passed_count = sum(1 for r in results if not r["filtered_reason"])
        print(
            f"\r   进度: {processed}/{total_to_process} ({pct:.1f}%)"
            f"  已找到: {passed_count}张"
            f"  剩余: {remaining/60:.1f}min",
            end="", flush=True
        )

        _t0 = time.perf_counter()
        faces = app.get(frame)
        _t["detect"] += time.perf_counter() - _t0

        if not faces:
            continue

        face_count = len(faces)
        filtered_reason = ""

        _t0 = time.perf_counter()
        if solo and face_count > 1:
            skipped_multi += 1
            filtered_reason = "multi_person"

        best_sim = 0.0
        best_face = None
        for face in faces:
            if not hasattr(face, 'normed_embedding') or face.normed_embedding is None:
                continue
            sim = max(cosine_similarity(face.normed_embedding, ref_emb) for ref_emb in ref_embeddings)
            if sim > best_sim:
                best_sim = sim
                best_face = face

        if best_face is None:
            _t["filter"] += time.perf_counter() - _t0
            continue

        if not filtered_reason and best_sim < sim_thresh:
            filtered_reason = "low_sim"

        yaw = estimate_yaw(best_face)
        if not filtered_reason and yaw > angle_thresh:
            filtered_reason = "high_angle"

        box = best_face.bbox.astype(int)
        x1, y1, x2, y2 = max(0, box[0]), max(0, box[1]), min(det_w, box[2]), min(det_h, box[3])
        face_crop_tight = frame[y1:y2, x1:x2]
        if face_crop_tight.size == 0:
            _t["filter"] += time.perf_counter() - _t0
            continue

        # face_size 换算回原始分辨率（粗估），阈值语义跨画质一致
        face_short_side = int(min(x2 - x1, y2 - y1) * scale_to_orig)
        if not filtered_reason and face_short_side < min_face_px:
            filtered_reason = "face_too_small"

        gray_crop = cv2.cvtColor(face_crop_tight, cv2.COLOR_BGR2GRAY)
        blur_score = laplacian_variance(gray_crop)
        if not filtered_reason and blur_score < blur_thresh:
            filtered_reason = "blurry"

        blur_norm = min(blur_score / 2000.0, 1.0)
        composite = best_sim * 0.75 + blur_norm * 0.25
        _t["filter"] += time.perf_counter() - _t0

        results.append({
            "frame_idx": actual_frame_idx,
            "ts_sec": ts,
            "timecode": f"{int(ts//60):02d}:{ts%60:05.2f}",
            "similarity": round(best_sim, 4),
            "blur_score": round(blur_score, 1),
            "yaw_deg": round(yaw, 1),
            "face_count": face_count,
            "face_size(px)": face_short_side,
            "composite": round(composite, 4),
            "filtered_reason": filtered_reason,
        })

    print()

    total_timed = sum(_t.values())
    print(f"\n⏱  Stage1 耗时（共 {processed} 帧）:")
    for key, label in {"detect": "人脸推理 app.get", "filter": "相似/质量过滤"}.items():
        secs = _t[key]
        pct = secs / total_timed * 100 if total_timed > 0 else 0
        avg_ms = secs / processed * 1000 if processed > 0 else 0
        print(f"   {label:<22} {secs:6.1f}s  {pct:5.1f}%  avg {avg_ms:5.1f}ms/帧  {'█' * int(pct / 5)}")

    if skipped_multi:
        print(f"   (跳过多人帧: {skipped_multi} 张)")

    elapsed_stage1 = time.time() - start_time
    passed = [r for r in results if not r["filtered_reason"]]
    print(f"✅ Stage1 完成，耗时 {elapsed_stage1/60:.1f} 分钟，通过过滤: {len(passed)} 张")

    if not passed:
        print("⚠️  没有找到目标人物，请检查参考照片或降低 --sim 阈值")

    # Stage 2：按 composite 排序，seek 原始帧并保存
    passed.sort(key=lambda x: x["composite"], reverse=True)
    top_results = passed[:top_n]
    print(f"\n💾 Stage2：seek 原始帧，保存 Top {len(top_results)} 张到: {output_dir}")

    fname_map = {}
    t2_start = time.time()
    done_count = 0

    def _seek_and_save(r):
        multi_tag = f"_multi{r['face_count']}" if r["face_count"] > 1 else ""
        fname = f"frame_{r['frame_idx']:07d}_{r['timecode'].replace(':', '-')}_sim{r['similarity']:.2f}{multi_tag}.jpg"
        success = seek_and_write_ffmpeg(video_path, r["ts_sec"], output_dir / fname)
        return r["frame_idx"], fname if success else None

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_seek_and_save, r): r for r in top_results}
        for future in as_completed(futures):
            frame_idx, fname = future.result()
            done_count += 1
            print(f"\r   [{done_count}/{len(top_results)}] seeking...", end="", flush=True)
            if fname:
                fname_map[frame_idx] = fname
            else:
                print(f"\n   ⚠️  无法读取帧 {futures[future]['timecode']}，跳过")
    print(f"\r   Stage2 完成，耗时 {time.time()-t2_start:.1f}s              ")

    # 写 CSV：全部有人脸的帧（含被过滤的），按时间顺序
    results.sort(key=lambda x: x["frame_idx"])
    csv_path = output_dir / "report.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["frame_idx", "timecode", "similarity", "blur_score", "yaw_deg", "face_count", "face_size(px)", "composite", "filtered_reason", "filename"])
        writer.writeheader()
        for r in results:
            writer.writerow({k: v for k, v in r.items() if k != "ts_sec"} | {"filename": fname_map.get(r["frame_idx"], "")})

    print(f"📊 报告已保存: {csv_path}")
    print(f"\n🏆 Top 5 最优帧:")
    for r in top_results[:5]:
        multi_info = f" | 画面人数:{r['face_count']}" if r["face_count"] > 1 else ""
        print(f"   {r['timecode']} | 相似度:{r['similarity']} | 清晰度:{r['blur_score']:.0f} | 偏角:{r['yaw_deg']}°{multi_info} | 综合:{r['composite']}")


PROGRESS_FILE = "batch_progress.json"


def load_progress(progress_path):
    """读取批量处理进度记录，key 为视频绝对路径"""
    if progress_path.exists():
        with open(progress_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(progress_path, progress):
    with open(progress_path, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def process_directory(app, video_dir, ref_embeddings, base_output, top_n, sample_fps,
                      sim_thresh, angle_thresh, blur_thresh, min_face_px, solo, overwrite,
                      skip_intro_sec=0.0, skip_outro_sec=0.0):
    video_dir = Path(video_dir)
    mp4_files = sorted(video_dir.glob("*.mp4")) + sorted(video_dir.glob("*.MP4"))
    # 去重（Windows 不区分大小写，可能重复）
    seen = set()
    mp4_files = [p for p in mp4_files if not (p.name.lower() in seen or seen.add(p.name.lower()))]

    if not mp4_files:
        print(f"⚠️  目录中未找到 .mp4 文件: {video_dir}")
        return

    if base_output is None:
        base_output = video_dir
    else:
        base_output = Path(base_output)
        base_output.mkdir(parents=True, exist_ok=True)

    progress_path = base_output / PROGRESS_FILE
    progress = load_progress(progress_path)

    total = len(mp4_files)
    print(f"📂 目录: {video_dir}")
    print(f"   共找到 {total} 个 MP4 文件")
    done_count = sum(1 for v in progress.values() if v.get("status") == "done")
    print(f"   已完成: {done_count} / {total}（进度记录: {progress_path}）")
    print("=" * 50)

    for idx, video_path in enumerate(mp4_files, 1):
        key = str(video_path.resolve())
        prev = progress.get(key, {})

        if prev.get("status") == "done":
            print(f"[{idx}/{total}] ⏭  跳过（已完成）: {video_path.name}")
            continue

        output_dir = base_output / f"{video_path.stem}_faces"
        print(f"\n[{idx}/{total}] 🎬 开始处理: {video_path.name}")

        start_time = datetime.now()
        progress[key] = {
            "status": "running",
            "video": str(video_path),
            "output_dir": str(output_dir),
            "start": start_time.isoformat(),
        }
        save_progress(progress_path, progress)

        try:
            process_video(
                app=app,
                video_path=video_path,
                ref_embeddings=ref_embeddings,
                output_dir=output_dir,
                top_n=top_n,
                sample_fps=sample_fps,
                sim_thresh=sim_thresh,
                angle_thresh=angle_thresh,
                blur_thresh=blur_thresh,
                min_face_px=min_face_px,
                solo=solo,
                overwrite=overwrite,
                skip_intro_sec=skip_intro_sec,
                skip_outro_sec=skip_outro_sec,
            )
            end_time = datetime.now()
            # 统计实际保存帧数
            saved = len(list(output_dir.glob("frame_*.jpg"))) if output_dir.exists() else 0
            progress[key] = {
                "status": "done",
                "video": str(video_path),
                "output_dir": str(output_dir),
                "frames_saved": saved,
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "elapsed_min": round((end_time - start_time).total_seconds() / 60, 2),
            }
        except Exception as e:
            end_time = datetime.now()
            progress[key] = {
                "status": "error",
                "video": str(video_path),
                "output_dir": str(output_dir),
                "error": str(e),
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            }
            print(f"❌ 处理失败: {video_path.name} — {e}")

        save_progress(progress_path, progress)

    print("\n" + "=" * 50)
    done = [v for v in progress.values() if v.get("status") == "done"]
    errors = [v for v in progress.values() if v.get("status") == "error"]
    print(f"🏁 批量处理完成: 成功 {len(done)} / {total}，失败 {len(errors)}")
    if errors:
        print("   失败列表:")
        for e in errors:
            print(f"   ❌ {Path(e['video']).name}: {e.get('error', '')}")
    print(f"📋 进度记录: {progress_path}")


def main():
    parser = argparse.ArgumentParser(description="从视频中提取指定人物的优质人脸帧")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--video", help="输入视频路径（单文件模式）")
    src.add_argument("--dir", help="视频目录，自动遍历所有 .mp4 文件（批量模式）")
    parser.add_argument("--refs", required=True, nargs="+", help="目标人物参考照片路径（1-5张）")
    parser.add_argument("--output", default=None, help="输出目录（单文件默认：视频旁的 {名}_faces；批量默认：视频目录本身）")
    parser.add_argument("--top", type=int, default=100, help="保留最优帧数量（默认100）")
    parser.add_argument("--fps", type=float, default=1.0, help="每秒采样帧数（默认1）")
    parser.add_argument("--sim", type=float, default=0.5, help="相似度阈值 0-1（默认0.5）")
    parser.add_argument("--angle", type=float, default=60.0, help="最大允许偏角°（默认60）")
    parser.add_argument("--blur", type=float, default=80.0, help="最低清晰度分（默认80）")
    parser.add_argument("--min-face", type=int, default=100, help="人脸短边最小像素数（默认100px）")
    parser.add_argument("--solo", action="store_true", help="只保留画面中只有目标人物单独出现的帧")
    parser.add_argument("--no-overwrite", action="store_true", help="输出目录非空时报错退出，而非自动清空")
    parser.add_argument("--model-dir", default=None, help="InsightFace 模型根目录（默认 ~/.insightface）")
    parser.add_argument("--skip-intro", type=float, default=0.0, metavar="SEC", help="跳过片头秒数（默认0，例如 90 表示跳过前1.5分钟）")
    parser.add_argument("--skip-outro", type=float, default=0.0, metavar="SEC", help="跳过片尾秒数（默认0，例如 60 表示跳过最后1分钟）")
    args = parser.parse_args()

    print("🦐 人脸帧提取工具 v1.2")
    print("=" * 50)

    app = load_face_app(args.model_dir)
    print(f"📷 加载参考照片 ({len(args.refs)} 张)...")
    ref_embeddings = []
    for ref_path in args.refs:
        emb = get_face_embedding(app, ref_path)
        if emb is not None:
            ref_embeddings.append(emb)
            print(f"   ✅ {ref_path}")

    if not ref_embeddings:
        print("❌ 没有成功加载任何参考照片，退出")
        sys.exit(1)

    overwrite = not args.no_overwrite

    if args.dir:
        process_directory(
            app=app,
            video_dir=args.dir,
            ref_embeddings=ref_embeddings,
            base_output=args.output,
            top_n=args.top,
            sample_fps=args.fps,
            sim_thresh=args.sim,
            angle_thresh=args.angle,
            blur_thresh=args.blur,
            min_face_px=args.min_face,
            solo=args.solo,
            overwrite=overwrite,
            skip_intro_sec=args.skip_intro,
            skip_outro_sec=args.skip_outro,
        )
    else:
        output = args.output
        if output is None:
            video_path = Path(args.video)
            output = str(video_path.parent / f"{video_path.stem}_faces")
        process_video(
            app=app,
            video_path=args.video,
            ref_embeddings=ref_embeddings,
            output_dir=output,
            top_n=args.top,
            sample_fps=args.fps,
            sim_thresh=args.sim,
            angle_thresh=args.angle,
            blur_thresh=args.blur,
            min_face_px=args.min_face,
            solo=args.solo,
            overwrite=overwrite,
            skip_intro_sec=args.skip_intro,
            skip_outro_sec=args.skip_outro,
        )


if __name__ == "__main__":
    main()
