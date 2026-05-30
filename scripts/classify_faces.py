#!/usr/bin/env python3
"""
classify_faces.py
将人脸图片按 角度×表情 分类到子文件夹，用于 LoRA 训练数据集策展。

设计为 extract_face_frames.py 的下游工具：
    extract → 提取人脸帧
    classify → 按角度×表情分桶、去重、质量排序

依赖（与 extract_face_frames.py 相同 + 可选 hsemotion）:
    pip install insightface opencv-python onnxruntime-gpu numpy<2.0
    pip install hsemotion-onnx   # 可选，表情识别更准

用法:
    # 对 extract 输出的目录分类
    python scripts/classify_faces.py --input E:\\AI\\LZJ_faces --output E:\\AI\\LZJ_classified --report

    # 递归扫描多个子目录
    python scripts/classify_faces.py --input E:\\AI\\downloads\\LZJ --output E:\\AI\\classified -r --report

    # 去重 + 每桶限30张（用于 LoRA 训练集）
    python scripts/classify_faces.py -i ./faces -o ./dataset --dedup 0.92 --max-per-bin 30

    # 只按角度分（不分表情）
    python scripts/classify_faces.py -i ./faces -o ./classified --no-expression

    # 符号链接模式（节省磁盘，Windows 需管理员权限）
    python scripts/classify_faces.py -i ./faces -o ./classified --symlink

参数说明:
    --input         输入图片目录（支持 extract 输出的 *_faces 目录）
    --output        输出分类目录
    --recursive     递归扫描子目录
    --max-per-bin   每个桶最多保留几张（按质量排序取top，0=不限）
    --no-expression 不做表情分类，只按角度分
    --symlink       用符号链接代替复制文件
    --move          移动文件而非复制
    --dedup         去重阈值，embedding余弦相似度超过此值视为重复（默认0.92，0=禁用）
    --min-quality   最低质量阈值，低于此分数直接丢弃（默认0，不过滤）
    --model-dir     InsightFace模型目录
    --report        生成分类统计报告
"""

import argparse
import csv
import os
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

# CUDA DLL 路径（与 extract_face_frames.py 一致）
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


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif"}


# ============================================================
# 模型初始化（复用 extract 的逻辑）
# ============================================================

def load_face_app(model_dir=None):
    """初始化 InsightFace，使用 buffalo_l 模型（含检测+识别）"""
    import onnxruntime as ort
    available = ort.get_available_providers()
    if "CUDAExecutionProvider" not in available:
        print("⚠️  CUDA 不可用，回退到 CPU（速度较慢）")
        providers = ["CPUExecutionProvider"]
    else:
        providers = ["CUDAExecutionProvider"]
        print("🚀 使用 GPU (CUDA) 加速")

    kwargs = {"name": "buffalo_l", "providers": providers}
    if model_dir:
        kwargs["root"] = model_dir
        print(f"📁 模型目录: {model_dir}")
    app = FaceAnalysis(**kwargs)
    app.prepare(ctx_id=0, det_size=(640, 640))

    # 验证 GPU
    if "CUDAExecutionProvider" in providers:
        for name, model in app.models.items():
            session = getattr(model, "session", None)
            if session is None:
                continue
            active = session.get_providers()
            if "CUDAExecutionProvider" not in active:
                print(f"⚠️  模型 {name} 未使用 CUDA，实际 provider: {active}")
        print(f"   已加载 {len(app.models)} 个子模型")
    return app


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
    return f"{get_yaw_bin(yaw)}_{get_pitch_bin(pitch)}"


# ============================================================
# 表情分类
# ============================================================

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
    """基于关键点的简易表情判断（无需额外模型）"""
    kps = face.kps
    left_eye, right_eye = kps[0], kps[1]
    left_mouth, right_mouth = kps[3], kps[4]

    eye_dist = abs(float(right_eye[0]) - float(left_eye[0]))
    if eye_dist < 3:
        return "neutral"

    mouth_width = abs(float(right_mouth[0]) - float(left_mouth[0]))
    width_ratio = mouth_width / eye_dist

    if width_ratio > 1.1:
        return "smile"
    elif width_ratio < 0.7:
        return "mouth_open"
    return "neutral"


class ExpressionClassifier:
    """表情分类器：优先 HSEmotion，fallback 到规则"""

    def __init__(self, use_model=True):
        self.fer = None
        if use_model and HAS_HSEMOTION:
            try:
                self.fer = HSEmotionRecognizer(model_name='enet_b0_8_va_mtl')
                print("✅ 表情分类: HSEmotion 模型")
            except Exception as e:
                print(f"⚠️  HSEmotion 加载失败({e})，回退到规则")
        if self.fer is None:
            print("ℹ️  表情分类: 规则模式（安装 hsemotion-onnx 可提升精度）")

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
# 质量评分（使用 top-10% percentile，抗皮肤稀释）
# ============================================================

def quality_score(img_gray, face) -> float:
    """质量评分 0-100
    锐度用 Laplacian top-10% 均值（不被大面积皮肤稀释），
    结合检测置信度加权。
    """
    box = face.bbox.astype(int)
    h, w = img_gray.shape[:2]
    x1, y1 = max(0, box[0]), max(0, box[1])
    x2, y2 = min(w, box[2]), min(h, box[3])

    if (x2 - x1) < 10 or (y2 - y1) < 10:
        return 0.0

    roi = img_gray[y1:y2, x1:x2]
    lap = np.abs(cv2.Laplacian(roi, cv2.CV_64F))

    # top-10% 均值：只看最锐利的边缘像素
    threshold = np.percentile(lap, 90)
    top_pixels = lap[lap >= threshold]
    sharpness = float(top_pixels.mean()) if top_pixels.size > 0 else 0.0

    det_score = float(face.det_score) * 100
    sharp_score = min(sharpness / 30.0 * 100, 100.0)

    return sharp_score * 0.6 + det_score * 0.4


# ============================================================
# 去重（基于 embedding 余弦相似度）
# ============================================================

def cosine_similarity(a, b):
    return float(np.dot(a, b))


def deduplicate(items: list, thresh: float) -> list:
    """贪心去重：按质量降序，逐个比对已选集，相似度超阈值的丢弃"""
    if not items or thresh <= 0:
        return items

    items.sort(key=lambda x: x["quality"], reverse=True)
    keep = [items[0]]

    for item in items[1:]:
        if item["embedding"] is None:
            keep.append(item)
            continue
        is_dup = False
        for kept in keep:
            if kept["embedding"] is None:
                continue
            sim = cosine_similarity(item["embedding"], kept["embedding"])
            if sim > thresh:
                is_dup = True
                break
        if not is_dup:
            keep.append(item)

    return keep


# ============================================================
# 主流程
# ============================================================

def scan_images(input_dir: str, recursive: bool) -> list:
    input_path = Path(input_dir)
    if recursive:
        files = [p for p in input_path.rglob("*") if p.suffix.lower() in IMAGE_EXTS]
    else:
        files = [p for p in input_path.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    return sorted(files)


def process_images(args):
    print(f"\n{'='*60}")
    print(f"  🦐 人脸分类工具 — 角度×表情分桶")
    print(f"{'='*60}")
    print(f"  输入: {args.input}")
    print(f"  输出: {args.output}")
    print(f"  递归: {'是' if args.recursive else '否'}")
    print(f"  去重: {args.dedup if args.dedup > 0 else '禁用'}")
    print(f"  每桶上限: {args.max_per_bin or '不限'}")
    print(f"  表情分类: {'关闭' if args.no_expression else '开启'}")
    print(f"{'='*60}\n")

    # 扫描
    images = scan_images(args.input, args.recursive)
    print(f"📂 扫描到 {len(images)} 张图片")
    if not images:
        print("⚠️  没找到图片，检查路径和文件后缀")
        return

    # 初始化
    app = load_face_app(args.model_dir)

    expr_clf = None
    if not args.no_expression:
        expr_clf = ExpressionClassifier(use_model=True)

    # 处理
    print(f"\n🔍 分析人脸...")
    bins = defaultdict(list)
    skipped = {"no_face": 0, "low_quality": 0}
    t0 = time.time()

    for i, img_path in enumerate(images):
        if (i + 1) % 200 == 0 or i == 0:
            elapsed = time.time() - t0
            speed = (i + 1) / max(elapsed, 0.01)
            eta = (len(images) - i - 1) / max(speed, 0.01)
            print(f"\r   [{i+1}/{len(images)}] {speed:.1f} img/s | ETA {eta:.0f}s", end="", flush=True)

        img = cv2.imread(str(img_path))
        if img is None:
            continue

        faces = app.get(img)
        if not faces:
            skipped["no_face"] += 1
            continue

        # 取最大脸
        face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]))

        # 质量
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        q = quality_score(img_gray, face)
        if q < args.min_quality:
            skipped["low_quality"] += 1
            continue

        # 角度：优先用 face.pose，fallback 到关键点估算
        if hasattr(face, 'pose') and face.pose is not None and len(face.pose) >= 2:
            yaw, pitch = float(face.pose[0]), float(face.pose[1])
        else:
            # fallback（与 extract 的 estimate_yaw 一致）
            kps = face.kps
            left_eye, right_eye, nose = kps[0], kps[1], kps[2]
            eye_center_x = (left_eye[0] + right_eye[0]) / 2
            eye_width = abs(right_eye[0] - left_eye[0])
            if eye_width < 3:
                skipped["no_face"] += 1
                continue
            offset = (nose[0] - eye_center_x) / eye_width
            yaw = offset * 60
            pitch = 0.0

        angle_bin = get_angle_bin(yaw, pitch)

        # 表情
        if expr_clf:
            box = face.bbox.astype(int)
            h, w = img.shape[:2]
            x1, y1 = max(0, box[0]), max(0, box[1])
            x2, y2 = min(w, box[2]), min(h, box[3])
            face_crop = img[y1:y2, x1:x2]
            if face_crop.size > 0:
                expr_bin = expr_clf.classify(face, face_crop)
            else:
                expr_bin = "neutral"
            bin_name = f"{angle_bin}_{expr_bin}"
        else:
            bin_name = angle_bin

        # embedding
        embedding = None
        if hasattr(face, 'normed_embedding') and face.normed_embedding is not None:
            embedding = face.normed_embedding
        elif hasattr(face, 'embedding') and face.embedding is not None:
            embedding = face.embedding

        bins[bin_name].append({
            "path": str(img_path),
            "quality": q,
            "embedding": embedding,
            "yaw": round(yaw, 1),
            "pitch": round(pitch, 1),
        })

    print(f"\r   分析完成{'':30}")
    elapsed = time.time() - t0
    total_classified = sum(len(v) for v in bins.values())
    print(f"\n✅ Stage1 完成 ({elapsed:.1f}s, {len(images)/max(elapsed,0.01):.1f} img/s)")
    print(f"   通过: {total_classified} 张 → {len(bins)} 个桶")
    print(f"   跳过: 无人脸 {skipped['no_face']}, 质量过低 {skipped['low_quality']}")

    # 去重
    if args.dedup > 0:
        print(f"\n🔄 去重 (阈值={args.dedup})...")
        before = sum(len(v) for v in bins.values())
        for bin_name in bins:
            has_emb = any(item["embedding"] is not None for item in bins[bin_name])
            if has_emb:
                bins[bin_name] = deduplicate(bins[bin_name], args.dedup)
            else:
                bins[bin_name].sort(key=lambda x: x["quality"], reverse=True)
        after = sum(len(v) for v in bins.values())
        print(f"   {before} → {after} (去除 {before - after} 张重复)")

    # 每桶取 top
    if args.max_per_bin and args.max_per_bin > 0:
        for bin_name in bins:
            bins[bin_name].sort(key=lambda x: x["quality"], reverse=True)
            bins[bin_name] = bins[bin_name][:args.max_per_bin]
        total_after = sum(len(v) for v in bins.values())
        print(f"   每桶限 {args.max_per_bin} 张，最终: {total_after} 张")

    # 输出文件
    print(f"\n💾 写入分类结果: {args.output}")
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    total_output = 0
    csv_rows = []

    for bin_name, items in sorted(bins.items()):
        bin_dir = output_path / bin_name
        bin_dir.mkdir(parents=True, exist_ok=True)
        for item in items:
            src = Path(item["path"])
            dst = bin_dir / src.name
            if dst.exists():
                dst = bin_dir / f"{src.stem}_{hash(str(src)) % 10000}{src.suffix}"

            if args.symlink:
                dst.symlink_to(src.resolve())
            elif args.move:
                shutil.move(str(src), str(dst))
            else:
                shutil.copy2(str(src), str(dst))

            csv_rows.append({
                "filename": src.name,
                "bin": bin_name,
                "quality": round(item["quality"], 1),
                "yaw": item["yaw"],
                "pitch": item["pitch"],
                "dest": str(dst),
            })
            total_output += 1

    print(f"   ✅ 写入 {total_output} 张 → {len(bins)} 个文件夹")

    # CSV 报告
    csv_path = output_path / "classification.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "bin", "quality", "yaw", "pitch", "dest"])
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"📊 CSV: {csv_path}")

    # 统计报告
    if args.report:
        report = generate_report(bins)
        report_path = output_path / "report.txt"
        report_path.write_text(report, encoding="utf-8")
        print(f"📊 报告: {report_path}")
        print(report)

    print(f"\n🎉 完成！")


def generate_report(bins: dict) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("  人脸分类统计报告")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"{'桶名':<30} {'数量':>6} {'平均质量':>10}")
    lines.append("-" * 50)

    angle_counts = defaultdict(int)
    expr_counts = defaultdict(int)

    for bin_name in sorted(bins.keys()):
        items = bins[bin_name]
        count = len(items)
        avg_q = np.mean([it["quality"] for it in items]) if items else 0
        lines.append(f"{bin_name:<30} {count:>6} {avg_q:>10.1f}")

        parts = bin_name.split("_")
        if len(parts) >= 2:
            angle_key = f"{parts[0]}_{parts[1]}"
            angle_counts[angle_key] += count
        if len(parts) >= 3:
            expr_counts[parts[2]] += count

    lines.append("")
    lines.append("--- 角度分布 ---")
    for k, v in sorted(angle_counts.items(), key=lambda x: -x[1]):
        bar = "█" * min(v // 5, 30)
        lines.append(f"  {k:<15} {v:>5}  {bar}")

    if expr_counts:
        lines.append("")
        lines.append("--- 表情分布 ---")
        for k, v in sorted(expr_counts.items(), key=lambda x: -x[1]):
            bar = "█" * min(v // 5, 30)
            lines.append(f"  {k:<15} {v:>5}  {bar}")

    # 空桶告警
    all_angles = []
    for yaw_name, _, _ in YAW_BINS:
        for pitch_name, _, _ in PITCH_BINS:
            all_angles.append(f"{yaw_name}_{pitch_name}")

    empty = [a for a in all_angles if angle_counts.get(a, 0) == 0]
    if empty:
        lines.append("")
        lines.append("⚠️  缺失角度（需要补充素材）:")
        for a in empty:
            lines.append(f"  ❌ {a}")

    lines.append("")
    total = sum(len(v) for v in bins.values())
    lines.append(f"总计: {total} 张 | {len(bins)} 个桶")
    return "\n".join(lines)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="人脸图片按角度×表情分类（LoRA 训练数据集策展）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", "-i", required=True, help="输入图片目录")
    parser.add_argument("--output", "-o", required=True, help="输出分类目录")
    parser.add_argument("--recursive", "-r", action="store_true", help="递归扫描子目录")
    parser.add_argument("--max-per-bin", type=int, default=0, help="每桶最多保留几张（0=不限）")
    parser.add_argument("--no-expression", action="store_true", help="不做表情分类")
    parser.add_argument("--symlink", action="store_true", help="符号链接代替复制")
    parser.add_argument("--move", action="store_true", help="移动而非复制")
    parser.add_argument("--dedup", type=float, default=0.92, help="去重阈值 (默认0.92，0=禁用)")
    parser.add_argument("--min-quality", type=float, default=0, help="最低质量分 (默认0)")
    parser.add_argument("--model-dir", default=None, help="InsightFace 模型目录")
    parser.add_argument("--report", action="store_true", help="生成统计报告")

    args = parser.parse_args()
    process_images(args)


if __name__ == "__main__":
    main()
