#!/usr/bin/env python3
"""
classify_faces.py
将人脸图片按 角度×表情 分类到子文件夹，用于 LoRA 训练数据集策展。

依赖（与 rate_face_images.py 相同 + hsemotion）:
    pip install insightface opencv-python onnxruntime-gpu numpy<2.0
    pip install hsemotion-onnx   # 表情识别（可选，不装则用规则分类）

用法:
    # 基本用法
    python scripts/classify_faces.py --input ./faces --output ./classified

    # 递归扫描 + 指定每桶最大数量
    python scripts/classify_faces.py --input ./faces --output ./classified --recursive --max-per-bin 30

    # 跳过表情分类（只按角度分）
    python scripts/classify_faces.py --input ./faces --output ./classified --no-expression

    # 使用符号链接而非复制（节省磁盘）
    python scripts/classify_faces.py --input ./faces --output ./classified --symlink

    # 生成统计报告
    python scripts/classify_faces.py --input ./faces --output ./classified --report

参数说明:
    --input         输入图片目录
    --output        输出分类目录
    --recursive     递归扫描子目录
    --max-per-bin   每个桶最多保留几张（按质量排序取top，0=不限）
    --no-expression 不做表情分类，只按角度分
    --symlink       用符号链接代替复制文件
    --copy          复制文件（默认）
    --move          移动文件
    --dedup-thresh  去重阈值，embedding余弦相似度超过此值视为重复（默认0.92）
    --min-quality   最低质量阈值，低于此分数直接丢弃（默认0，不过滤）
    --model-dir     InsightFace模型目录
    --batch-size    批处理大小（默认200）
    --report        生成分类统计报告
    --workers       并行worker数（默认1，>1时用多进程）
"""

import argparse
import json
import os
import shutil
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

# CUDA DLL路径（Windows ComfyUI环境适配）
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
    print("❌ 请先安装依赖: pip install insightface opencv-python onnxruntime-gpu numpy<2.0")
    sys.exit(1)

# 表情识别（可选）
try:
    from hsemotion_onnx.facial_emotions import HSEmotionRecognizer
    HAS_HSEMOTION = True
except ImportError:
    HAS_HSEMOTION = False


# ============================================================
# 角度分桶
# ============================================================

YAW_BINS = [
    ("left60",  -90, -45),
    ("left30",  -45, -15),
    ("front",   -15,  15),
    ("right30",  15,  45),
    ("right60",  45,  90),
]

PITCH_BINS = [
    ("up",    15,  90),
    ("level", -15,  15),
    ("down",  -90, -15),
]


def get_yaw_bin(yaw: float) -> str:
    for name, lo, hi in YAW_BINS:
        if lo <= yaw < hi:
            return name
    return "right60" if yaw >= 90 else "left60"


def get_pitch_bin(pitch: float) -> str:
    for name, lo, hi in PITCH_BINS:
        if lo <= pitch < hi:
            return name
    return "up" if pitch >= 90 else "down"


def get_angle_bin(yaw: float, pitch: float) -> str:
    """返回角度桶名，如 front_level, left30_up"""
    return f"{get_yaw_bin(yaw)}_{get_pitch_bin(pitch)}"


# ============================================================
# 表情分类
# ============================================================

# HSEmotion → 简化映射
EMOTION_MAP = {
    "Anger": "serious",
    "Contempt": "serious",
    "Disgust": "serious",
    "Fear": "surprise",
    "Happiness": "smile",
    "Neutral": "neutral",
    "Sadness": "serious",
    "Surprise": "surprise",
}


def get_expression_rule_based(face) -> str:
    """基于关键点的简单表情规则（不需要额外模型）"""
    kps = face.kps  # [左眼, 右眼, 鼻尖, 左嘴角, 右嘴角]
    left_eye, right_eye = kps[0], kps[1]
    left_mouth, right_mouth = kps[3], kps[4]

    eye_dist = abs(float(right_eye[0]) - float(left_eye[0]))
    if eye_dist < 3:
        return "neutral"

    # 嘴角上扬程度（相对于鼻尖高度）
    nose_y = float(kps[2][1])
    mouth_center_y = (float(left_mouth[1]) + float(right_mouth[1])) / 2
    mouth_width = abs(float(right_mouth[0]) - float(left_mouth[0]))

    # 嘴角宽度/眼距 比例 — 笑的时候嘴角拉宽
    width_ratio = mouth_width / eye_dist

    if width_ratio > 1.1:
        return "smile"
    elif width_ratio < 0.7:
        return "mouth_open"  # 嘴巴收窄通常是张嘴（O型）
    else:
        return "neutral"


class ExpressionClassifier:
    """表情分类器，优先用HSEmotion，fallback到规则"""

    def __init__(self, use_model=True):
        self.fer = None
        if use_model and HAS_HSEMOTION:
            try:
                self.fer = HSEmotionRecognizer(model_name='enet_b0_8_va_mtl')
                print("✅ 使用 HSEmotion 模型进行表情分类")
            except Exception as e:
                print(f"⚠️  HSEmotion 加载失败({e})，回退到规则分类")
        if self.fer is None:
            print("ℹ️  使用规则进行表情分类（精度有限，可安装 hsemotion-onnx 提升）")

    def classify(self, face, face_crop_bgr) -> str:
        if self.fer is not None:
            try:
                face_rgb = cv2.cvtColor(face_crop_bgr, cv2.COLOR_BGR2RGB)
                emotion, _ = self.fer.predict_emotions(face_rgb)
                return EMOTION_MAP.get(emotion, "neutral")
            except Exception:
                pass
        return get_expression_rule_based(face)


# ============================================================
# 质量评分（精简版，复用 rate_face_images.py 的逻辑）
# ============================================================

def quick_quality_score(img_gray, face) -> float:
    """快速质量评分 0-100，用于桶内排序"""
    box = face.bbox.astype(int)
    x1, y1, x2, y2 = max(0, box[0]), max(0, box[1]), box[2], box[3]
    h, w = img_gray.shape[:2]
    x2, y2 = min(w, x2), min(h, y2)

    if (x2 - x1) < 10 or (y2 - y1) < 10:
        return 0.0

    roi = img_gray[y1:y2, x1:x2]

    # Laplacian top-10% (抗皮肤稀释)
    lap = np.abs(cv2.Laplacian(roi, cv2.CV_64F))
    threshold = np.percentile(lap, 90)
    sharpness = float(lap[lap >= threshold].mean()) if lap[lap >= threshold].size > 0 else 0.0

    # 检测置信度
    det_score = float(face.det_score) * 100

    # 综合 (锐度60% + 检测置信度40%)
    sharp_score = min(sharpness / 30.0 * 100, 100.0)  # 30 为经验基准
    return sharp_score * 0.6 + det_score * 0.4


# ============================================================
# 去重
# ============================================================

def deduplicate(items: list, thresh: float = 0.92) -> list:
    """基于embedding余弦相似度去重，保留质量最高的"""
    if not items or thresh <= 0:
        return items

    # 按质量降序
    items.sort(key=lambda x: x["quality"], reverse=True)
    keep = []

    for item in items:
        is_dup = False
        for kept in keep:
            sim = np.dot(item["embedding"], kept["embedding"]) / (
                np.linalg.norm(item["embedding"]) * np.linalg.norm(kept["embedding"]) + 1e-8
            )
            if sim > thresh:
                is_dup = True
                break
        if not is_dup:
            keep.append(item)

    return keep


# ============================================================
# 主流程
# ============================================================

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif"}


def scan_images(input_dir: str, recursive: bool) -> list:
    """扫描目录获取所有图片路径"""
    input_path = Path(input_dir)
    if recursive:
        files = [p for p in input_path.rglob("*") if p.suffix.lower() in IMAGE_EXTS]
    else:
        files = [p for p in input_path.iterdir() if p.suffix.lower() in IMAGE_EXTS]
    return sorted(files)


def process_images(args):
    """主处理流程"""
    print(f"\n{'='*60}")
    print(f"  人脸角度×表情 分类工具")
    print(f"{'='*60}")
    print(f"  输入: {args.input}")
    print(f"  输出: {args.output}")
    print(f"  去重阈值: {args.dedup_thresh}")
    print(f"  每桶上限: {args.max_per_bin or '不限'}")
    print(f"{'='*60}\n")

    # 扫描图片
    images = scan_images(args.input, args.recursive)
    print(f"📂 扫描到 {len(images)} 张图片")
    if not images:
        print("⚠️  没找到图片，检查路径和后缀")
        return

    # 初始化模型
    print("🔄 加载 InsightFace 模型...")
    kwargs = {}
    if args.model_dir:
        kwargs["root"] = args.model_dir
    app = FaceAnalysis(providers=['CUDAExecutionProvider', 'CPUExecutionProvider'], **kwargs)
    app.prepare(ctx_id=0, det_size=(640, 640))

    # 表情分类器
    expr_clf = None
    if not args.no_expression:
        expr_clf = ExpressionClassifier(use_model=True)

    # 处理图片 → 收集元数据
    print("🔍 分析人脸...")
    bins = defaultdict(list)  # bin_name → [{"path", "quality", "embedding"}, ...]
    skipped = {"no_face": 0, "low_quality": 0}
    t0 = time.time()

    for i, img_path in enumerate(images):
        if (i + 1) % 100 == 0 or i == 0:
            elapsed = time.time() - t0
            speed = (i + 1) / max(elapsed, 0.01)
            eta = (len(images) - i - 1) / max(speed, 0.01)
            print(f"  [{i+1}/{len(images)}] {speed:.1f} img/s, ETA {eta:.0f}s")

        img = cv2.imread(str(img_path))
        if img is None:
            continue

        faces = app.get(img)
        if not faces:
            skipped["no_face"] += 1
            continue

        # 取最大脸
        face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]))

        # 质量评分
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        quality = quick_quality_score(img_gray, face)
        if quality < args.min_quality:
            skipped["low_quality"] += 1
            continue

        # 角度
        # InsightFace face.pose 返回 [pitch, yaw, roll] 或需通过 embedding 模型
        # 不同版本可能不同，做兼容处理
        if hasattr(face, 'pose') and face.pose is not None:
            pose = face.pose
            # insightface buffalo_l: pose = [yaw, pitch, roll] (度)
            yaw, pitch = float(pose[0]), float(pose[1])
        else:
            # fallback: 用关键点估算 yaw
            kps = face.kps
            left_eye, right_eye, nose = kps[0], kps[1], kps[2]
            eye_center_x = (left_eye[0] + right_eye[0]) / 2
            eye_width = abs(right_eye[0] - left_eye[0])
            if eye_width < 3:
                skipped["no_face"] += 1
                continue
            offset = (nose[0] - eye_center_x) / eye_width
            yaw = offset * 60  # 粗估
            pitch = 0.0

        angle_bin = get_angle_bin(yaw, pitch)

        # 表情
        if expr_clf:
            box = face.bbox.astype(int)
            x1 = max(0, box[0])
            y1 = max(0, box[1])
            x2 = min(img.shape[1], box[2])
            y2 = min(img.shape[0], box[3])
            face_crop = img[y1:y2, x1:x2]
            if face_crop.size > 0:
                expr_bin = expr_clf.classify(face, face_crop)
            else:
                expr_bin = "neutral"
            bin_name = f"{angle_bin}_{expr_bin}"
        else:
            bin_name = angle_bin

        # embedding 用于去重
        embedding = face.embedding if hasattr(face, 'embedding') and face.embedding is not None else None

        bins[bin_name].append({
            "path": str(img_path),
            "quality": quality,
            "embedding": embedding,
        })

    elapsed = time.time() - t0
    total_classified = sum(len(v) for v in bins.values())
    print(f"\n✅ 分析完成 ({elapsed:.1f}s)")
    print(f"   分类: {total_classified} 张 → {len(bins)} 个桶")
    print(f"   跳过: 无人脸 {skipped['no_face']}, 质量过低 {skipped['low_quality']}")

    # 去重
    if args.dedup_thresh > 0:
        print(f"\n🔄 去重 (阈值={args.dedup_thresh})...")
        before = sum(len(v) for v in bins.values())
        for bin_name in bins:
            has_emb = all(item["embedding"] is not None for item in bins[bin_name])
            if has_emb:
                bins[bin_name] = deduplicate(bins[bin_name], args.dedup_thresh)
            else:
                # 没有embedding就按质量排序不去重
                bins[bin_name].sort(key=lambda x: x["quality"], reverse=True)
        after = sum(len(v) for v in bins.values())
        print(f"   去重: {before} → {after} (移除 {before - after} 张重复)")

    # 每桶取top
    if args.max_per_bin and args.max_per_bin > 0:
        for bin_name in bins:
            bins[bin_name].sort(key=lambda x: x["quality"], reverse=True)
            bins[bin_name] = bins[bin_name][:args.max_per_bin]

    # 输出
    print(f"\n📁 写入分类结果到: {args.output}")
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    total_output = 0
    for bin_name, items in sorted(bins.items()):
        bin_dir = output_path / bin_name
        bin_dir.mkdir(parents=True, exist_ok=True)
        for item in items:
            src = Path(item["path"])
            dst = bin_dir / src.name
            # 处理同名
            if dst.exists():
                dst = bin_dir / f"{src.stem}_{hash(str(src)) % 10000}{src.suffix}"

            if args.symlink:
                dst.symlink_to(src.resolve())
            elif args.move:
                shutil.move(str(src), str(dst))
            else:
                shutil.copy2(str(src), str(dst))
            total_output += 1

    print(f"   写入 {total_output} 张图片到 {len(bins)} 个文件夹")

    # 报告
    if args.report:
        report = generate_report(bins, args)
        report_path = output_path / "classification_report.txt"
        report_path.write_text(report, encoding="utf-8")
        print(f"\n📊 报告已保存: {report_path}")
        print(report)

    print("\n🎉 完成！")


def generate_report(bins: dict, args) -> str:
    """生成分类统计报告"""
    lines = []
    lines.append("=" * 60)
    lines.append("  人脸分类统计报告")
    lines.append("=" * 60)
    lines.append(f"  输入: {args.input}")
    lines.append(f"  去重阈值: {args.dedup_thresh}")
    lines.append(f"  每桶上限: {args.max_per_bin or '不限'}")
    lines.append("")

    # 按角度聚合
    angle_counts = defaultdict(int)
    expr_counts = defaultdict(int)

    lines.append(f"{'桶名':<30} {'数量':>6} {'平均质量':>10}")
    lines.append("-" * 50)

    for bin_name in sorted(bins.keys()):
        items = bins[bin_name]
        count = len(items)
        avg_q = np.mean([it["quality"] for it in items]) if items else 0
        lines.append(f"{bin_name:<30} {count:>6} {avg_q:>10.1f}")

        parts = bin_name.split("_")
        if len(parts) >= 2:
            angle_key = "_".join(parts[:2])
            angle_counts[angle_key] += count
        if len(parts) >= 3:
            expr_counts[parts[2]] += count

    lines.append("")
    lines.append("--- 角度分布 ---")
    for k, v in sorted(angle_counts.items()):
        lines.append(f"  {k}: {v}")

    if expr_counts:
        lines.append("")
        lines.append("--- 表情分布 ---")
        for k, v in sorted(expr_counts.items()):
            lines.append(f"  {k}: {v}")

    # 空桶告警
    all_possible = []
    for yaw_name, _, _ in YAW_BINS:
        for pitch_name, _, _ in PITCH_BINS:
            all_possible.append(f"{yaw_name}_{pitch_name}")

    empty_angles = [a for a in all_possible if angle_counts.get(a, 0) == 0]
    if empty_angles:
        lines.append("")
        lines.append("⚠️  缺失角度（可能需要补充素材）:")
        for a in empty_angles:
            lines.append(f"  ❌ {a}")

    lines.append("")
    total = sum(len(v) for v in bins.values())
    lines.append(f"总计: {total} 张图片, {len(bins)} 个桶")
    return "\n".join(lines)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="人脸图片按角度×表情分类（LoRA训练数据集策展）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", "-i", required=True, help="输入图片目录")
    parser.add_argument("--output", "-o", required=True, help="输出分类目录")
    parser.add_argument("--recursive", "-r", action="store_true", help="递归扫描子目录")
    parser.add_argument("--max-per-bin", type=int, default=0, help="每桶最多保留几张（0=不限）")
    parser.add_argument("--no-expression", action="store_true", help="不做表情分类，只按角度分")
    parser.add_argument("--symlink", action="store_true", help="用符号链接代替复制")
    parser.add_argument("--move", action="store_true", help="移动文件而非复制")
    parser.add_argument("--dedup-thresh", type=float, default=0.92, help="去重余弦相似度阈值 (默认0.92)")
    parser.add_argument("--min-quality", type=float, default=0, help="最低质量分数 (默认0)")
    parser.add_argument("--model-dir", default=None, help="InsightFace模型目录")
    parser.add_argument("--batch-size", type=int, default=200, help="批处理大小")
    parser.add_argument("--report", action="store_true", help="生成分类统计报告")
    parser.add_argument("--workers", type=int, default=1, help="并行worker数")

    args = parser.parse_args()
    process_images(args)


if __name__ == "__main__":
    main()
