#!/usr/bin/env python3
"""
extract_face_frames.py
从视频中提取指定人物的优质人脸帧

依赖安装:
    # CPU 模式
    pip install insightface opencv-python onnxruntime numpy
    # GPU 模式（NVIDIA CUDA，推荐）
    pip install insightface opencv-python onnxruntime-gpu numpy

用法:
    python extract_face_frames.py \
        --video /path/to/video.mp4 \
        --refs /path/to/ref1.jpg /path/to/ref2.jpg \
        --output ./output_frames \
        --top 100 \
        --fps 1

参数说明:
    --video     输入视频路径
    --refs      目标人物参考照片（1-5张，正脸清晰最佳）
    --output    输出目录（自动创建）
    --top       保留评分最高的N张帧（默认100）
    --fps       每秒采样帧数（默认1，40min视频约2400帧）
    --sim       人脸相似度阈值（默认0.45，越高越严格）
    --angle     最大允许偏角°（默认40）
    --blur      最低清晰度分（默认80，Laplacian方差）
"""

import argparse
import csv
import os
import sys
from pathlib import Path

import cv2
import numpy as np

try:
    import insightface
    from insightface.app import FaceAnalysis
except ImportError:
    print("❌ 请先安装依赖: pip install insightface opencv-python onnxruntime numpy")
    sys.exit(1)


def load_face_app():
    """初始化 InsightFace，使用 buffalo_l 模型（含检测+识别）"""
    # 自动检测 GPU：优先 CUDA，回退 CPU
    import onnxruntime as ort
    available = ort.get_available_providers()
    if "CUDAExecutionProvider" in available:
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        print("🚀 使用 GPU (CUDA) 加速")
    else:
        providers = ["CPUExecutionProvider"]
        print("💻 使用 CPU 模式")
    app = FaceAnalysis(name="buffalo_l", providers=providers)
    app.prepare(ctx_id=0, det_size=(640, 640))
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


def process_video(video_path, ref_embeddings, output_dir, top_n, sample_fps, sim_thresh, angle_thresh, blur_thresh):
    app = load_face_app()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"❌ 无法打开视频: {video_path}")
        sys.exit(1)

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / video_fps
    step = max(1, int(video_fps / sample_fps))

    print(f"📹 视频: {video_path}")
    print(f"   时长: {duration_sec/60:.1f} 分钟 | 总帧数: {total_frames} | 采样步长: {step}帧")
    print(f"   预计处理帧数: {total_frames // step}")
    print(f"🔍 开始扫描...")

    results = []
    frame_idx = 0
    processed = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % step == 0:
            processed += 1
            if processed % 200 == 0:
                ts = frame_idx / video_fps
                print(f"   已处理 {processed} 帧 ({ts/60:.1f} min)...")

            faces = app.get(frame)
            if not faces:
                frame_idx += 1
                continue

            # 找到与目标人物最相似的人脸
            best_sim = 0.0
            best_face = None
            for face in faces:
                if not hasattr(face, 'normed_embedding') or face.normed_embedding is None:
                    continue
                sim = max(cosine_similarity(face.normed_embedding, ref_emb) for ref_emb in ref_embeddings)
                if sim > best_sim:
                    best_sim = sim
                    best_face = face

            if best_face is None or best_sim < sim_thresh:
                frame_idx += 1
                continue

            # 偏角过滤
            yaw = estimate_yaw(best_face)
            if yaw > angle_thresh:
                frame_idx += 1
                continue

            # 清晰度（只对人脸区域）
            box = best_face.bbox.astype(int)
            x1, y1, x2, y2 = max(0, box[0]), max(0, box[1]), min(frame.shape[1], box[2]), min(frame.shape[0], box[3])
            face_crop = frame[y1:y2, x1:x2]
            if face_crop.size == 0:
                frame_idx += 1
                continue
            gray_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
            blur_score = laplacian_variance(gray_crop)

            if blur_score < blur_thresh:
                frame_idx += 1
                continue

            # 综合评分：相似度60% + 清晰度40%（清晰度归一化到0-1，cap at 2000）
            blur_norm = min(blur_score / 2000.0, 1.0)
            composite = best_sim * 0.6 + blur_norm * 0.4

            ts = frame_idx / video_fps
            results.append({
                "frame_idx": frame_idx,
                "timecode": f"{int(ts//60):02d}:{ts%60:05.2f}",
                "similarity": round(best_sim, 4),
                "blur_score": round(blur_score, 1),
                "yaw_deg": round(yaw, 1),
                "composite": round(composite, 4),
                "frame": frame.copy(),
            })

        frame_idx += 1

    cap.release()

    print(f"\n✅ 扫描完成，找到符合条件的帧: {len(results)} 张")

    if not results:
        print("⚠️  没有找到目标人物，请检查参考照片或降低 --sim 阈值")
        return

    # 按综合评分排序，取 top N
    results.sort(key=lambda x: x["composite"], reverse=True)
    top_results = results[:top_n]
    top_results.sort(key=lambda x: x["frame_idx"])  # 按时间顺序排列输出

    print(f"💾 保存 Top {len(top_results)} 张到: {output_dir}")

    csv_path = output_dir / "report.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["frame_idx", "timecode", "similarity", "blur_score", "yaw_deg", "composite", "filename"])
        writer.writeheader()
        for i, r in enumerate(top_results):
            fname = f"frame_{r['frame_idx']:07d}_{r['timecode'].replace(':', '-')}_sim{r['similarity']:.2f}.jpg"
            cv2.imwrite(str(output_dir / fname), r["frame"])
            writer.writerow({k: v for k, v in r.items() if k != "frame"} | {"filename": fname})

    print(f"📊 报告已保存: {csv_path}")
    print(f"\n🏆 Top 5 最优帧:")
    for r in top_results[:5]:
        print(f"   {r['timecode']} | 相似度:{r['similarity']} | 清晰度:{r['blur_score']:.0f} | 偏角:{r['yaw_deg']}° | 综合:{r['composite']}")


def main():
    parser = argparse.ArgumentParser(description="从视频中提取指定人物的优质人脸帧")
    parser.add_argument("--video", required=True, help="输入视频路径")
    parser.add_argument("--refs", required=True, nargs="+", help="目标人物参考照片路径（1-5张）")
    parser.add_argument("--output", default="./output_frames", help="输出目录")
    parser.add_argument("--top", type=int, default=100, help="保留最优帧数量（默认100）")
    parser.add_argument("--fps", type=float, default=1.0, help="每秒采样帧数（默认1）")
    parser.add_argument("--sim", type=float, default=0.45, help="相似度阈值 0-1（默认0.45）")
    parser.add_argument("--angle", type=float, default=40.0, help="最大允许偏角°（默认40）")
    parser.add_argument("--blur", type=float, default=80.0, help="最低清晰度分（默认80）")
    args = parser.parse_args()

    print("🦐 人脸帧提取工具 v1.0")
    print("=" * 50)

    app = load_face_app()
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

    process_video(
        video_path=args.video,
        ref_embeddings=ref_embeddings,
        output_dir=args.output,
        top_n=args.top,
        sample_fps=args.fps,
        sim_thresh=args.sim,
        angle_thresh=args.angle,
        blur_thresh=args.blur,
    )


if __name__ == "__main__":
    main()
