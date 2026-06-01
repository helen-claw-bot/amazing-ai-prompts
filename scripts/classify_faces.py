#!/usr/bin/env python3
"""
classify_faces.py  v2.0
将人脸图片按 角度×表情 分类到子文件夹，用于 LoRA 训练数据集策展。

方案来源：
    InsightFace（人脸检测+身份确认）
    FaceXFormer（角度/表情/遮挡/闭眼 多任务一体）
    imagededup（PHash感知哈希去重，Windows/Linux/Mac兼容）

设计为 extract_face_frames.py 的下游工具：
    extract → 提取人脸帧
    classify → 按角度×表情分桶、去重

依赖安装（numpy 1.26.4 兼容）:
    pip install insightface opencv-python onnxruntime-gpu numpy<2.0
    pip install facexformer_pipeline    # 角度+表情+属性（首次运行自动下载模型）
    pip install imagededup              # 感知哈希去重（Windows/Linux/Mac 兼容）

用法:
    # 基本用法（对 extract 输出目录分类）
    python scripts/classify_faces.py -i E:\\AI\\downloads\\CHTT\\S01E01_faces -o E:\\AI\\data\\lora_results\\CHTT\\EP01_classified --report

    # 完整 pipeline（去重 + 每桶限30张）
    python scripts/classify_faces.py -i ./faces -o ./dataset --max-per-bin 30 --report

    # 跳过 imagededup（不去重，只分类）
    python scripts/classify_faces.py -i E:\\AI\\downloads\\CHTT\\S01E01_faces -o E:\\AI\\data\\lora_results\\CHTT\\EP01_classified --no-imagededup

参数说明:
    --input, -i         输入图片目录
    --output, -o        输出分类目录
    --recursive, -r     递归扫描子目录
    --max-per-bin       每个桶最多保留几张（0=不限）
    --no-expression     不做表情分类，只按角度分
    --no-imagededup     不用 imagededup 去重
    --symlink           符号链接代替复制
    --move              移动而非复制
    --model-dir         InsightFace 模型目录
    --report            生成统计报告
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
    print("❌ 请先安装: pip install insightface opencv-python onnxruntime-gpu numpy<2.0")
    sys.exit(1)

# FaceXFormer（可选）
try:
    from facexformer_pipeline import FacexformerPipeline
    HAS_FACEXFORMER = True
except ImportError:
    HAS_FACEXFORMER = False

# imagededup（可选）
try:
    from imagededup.methods import PHash
    HAS_IMAGEDEDUP = True
except ImportError:
    HAS_IMAGEDEDUP = False


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif"}


# ============================================================
# 角度分桶 (8 类)
# ============================================================

def yaw_pitch_to_angle_bin(yaw: float, pitch: float) -> str:
    """
    8类角度分桶：
    front, left_30, right_30, left_60, right_60, profile, up, down
    """
    # pitch 优先：明显仰/俯视单独归类
    if pitch > 20:
        return "up"
    if pitch < -20:
        return "down"

    # yaw 分桶
    abs_yaw = abs(yaw)
    if abs_yaw < 15:
        return "front"
    elif abs_yaw < 45:
        return "left_30" if yaw < 0 else "right_30"
    elif abs_yaw < 70:
        return "left_60" if yaw < 0 else "right_60"
    else:
        return "profile"


ANGLE_BINS = ["front", "left_30", "right_30", "left_60", "right_60", "profile", "up", "down"]


# ============================================================
# 表情分桶 (6 类)
# ============================================================

EXPRESSION_BINS = ["neutral", "smile", "laugh", "serious", "mouth_open", "eyes_closed"]


# ============================================================
# FaceXFormer 封装
# ============================================================

class FaceXFormerAnalyzer:
    """使用 FaceXFormer 进行角度+表情+属性分析"""

    def __init__(self):
        print("🔄 加载 FaceXFormer 模型...")
        self.pipeline = FacexformerPipeline(
            debug=False,
            tasks=['headpose', 'attributes']
        )
        print("✅ FaceXFormer 就绪")

    def analyze(self, img_bgr, face_box=None) -> dict:
        """
        返回 {"yaw", "pitch", "roll", "expression_bin"}
        """
        try:
            # FaceXFormer 需要 RGB
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

            # 如果有 face_box，传入坐标避免重复检测
            kwargs = {}
            if face_box is not None:
                x1, y1, x2, y2 = face_box
                kwargs["face_coordinates"] = [int(x1), int(y1), int(x2), int(y2)]

            results = self.pipeline.run_model(img_rgb, **kwargs)

            # headpose: [yaw, pitch, roll]
            headpose = results.get("headpose")
            if headpose is not None:
                yaw, pitch, roll = float(headpose[0]), float(headpose[1]), float(headpose[2])
            else:
                yaw, pitch, roll = 0.0, 0.0, 0.0

            # attributes: 包含表情/遮挡/闭眼等
            attrs = results.get("attributes", {})
            expr_bin = self._map_expression(attrs)

            return {
                "yaw": yaw,
                "pitch": pitch,
                "roll": roll,
                "expression_bin": expr_bin,
                "attributes": attrs,
            }
        except Exception as e:
            return {"yaw": 0, "pitch": 0, "roll": 0, "expression_bin": "neutral", "attributes": {}, "error": str(e)}

    def _map_expression(self, attrs: dict) -> str:
        """从 FaceXFormer attributes 映射到 6 类表情"""
        # FaceXFormer attributes 格式取决于模型版本
        # 常见输出：expression 字段或多个属性字段

        # 闭眼优先
        if attrs.get("eyes_closed") or attrs.get("Narrow_Eyes"):
            return "eyes_closed"

        # 嘴巴张开
        if attrs.get("Mouth_Slightly_Open") or attrs.get("mouth_open"):
            return "mouth_open"

        # 笑容
        smiling = attrs.get("Smiling") or attrs.get("smiling")
        if smiling:
            # 区分 smile 和 laugh（如果有强度信息）
            if attrs.get("Big_Lips") or attrs.get("mouth_open"):
                return "laugh"
            return "smile"

        # 严肃（皱眉/生气）
        if attrs.get("Frowning") or attrs.get("Angry"):
            return "serious"

        return "neutral"


# ============================================================
# 模型初始化
# ============================================================

def load_face_app(model_dir=None):
    """初始化 InsightFace（与 extract_face_frames.py 一致）"""
    import onnxruntime as ort
    available = ort.get_available_providers()
    if "CUDAExecutionProvider" in available:
        providers = ["CUDAExecutionProvider"]
        print("🚀 InsightFace: GPU (CUDA)")
    else:
        providers = ["CPUExecutionProvider"]
        print("⚠️  InsightFace: CPU（较慢）")

    kwargs = {"name": "buffalo_l", "providers": providers}
    if model_dir:
        kwargs["root"] = model_dir
    app = FaceAnalysis(**kwargs)
    app.prepare(ctx_id=0, det_size=(640, 640))

    if "CUDAExecutionProvider" in providers:
        for name, model in app.models.items():
            session = getattr(model, "session", None)
            if session and "CUDAExecutionProvider" not in session.get_providers():
                print(f"⚠️  {name} 未使用 CUDA")
        print(f"   {len(app.models)} 个子模型已加载")
    return app


# ============================================================
# imagededup 去重（PHash 感知哈希）
# ============================================================

def run_imagededup_dedup(image_dir: str, threshold: int = 10) -> set:
    """
    用 imagededup PHash 找出近似重复图片，返回应该被移除的文件名集合。
    threshold: 汉明距离阈值，越小越严格（默认10，适合视频连续帧）
    """
    if not HAS_IMAGEDEDUP:
        return set()

    print(f"\n🔄 imagededup PHash 去重分析 (阈值={threshold})...")

    try:
        phasher = PHash()
        encodings = phasher.encode_images(image_dir=image_dir)
        duplicates = phasher.find_duplicates(encoding_map=encodings, max_distance_threshold=threshold)

        # 贪心选择：每组保留第一个，标记其余为重复
        remove_set = set()
        for filename, dups in duplicates.items():
            if filename in remove_set:
                continue
            for dup in dups:
                if dup not in remove_set:
                    remove_set.add(dup)

        print(f"   imagededup 标记 {len(remove_set)} 张为重复")
        return remove_set
    except Exception as e:
        print(f"⚠️  imagededup 运行失败: {e}，跳过去重")
        return set()


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
    print(f"  🦐 人脸分类工具 v2.0 — LoRA 数据集策展")
    print(f"{'='*60}")
    print(f"  输入: {args.input}")
    print(f"  输出: {args.output}")
    print(f"  递归: {'是' if args.recursive else '否'}")
    print(f"  FaceXFormer: {'可用' if HAS_FACEXFORMER else '未安装'}")
    print(f"  imagededup: {'关闭' if args.no_imagededup else ('可用' if HAS_IMAGEDEDUP else '未安装')}")
    print(f"  每桶上限: {args.max_per_bin or '不限'}")
    print(f"  表情分类: {'关闭' if args.no_expression else '开启'}")
    print(f"{'='*60}\n")

    # 扫描
    images = scan_images(args.input, args.recursive)
    print(f"📂 扫描到 {len(images)} 张图片")
    if not images:
        print("⚠️  没找到图片")
        return

    # ---- Stage 0: imagededup 预去重 ----
    imagededup_remove = set()
    if not args.no_imagededup and HAS_IMAGEDEDUP:
        imagededup_remove = run_imagededup_dedup(args.input, threshold=10)
        if imagededup_remove:
            images = [p for p in images if p.name not in imagededup_remove]
            print(f"   imagededup 后剩余: {len(images)} 张")

    # ---- Stage 1: 加载模型 ----
    app = load_face_app(args.model_dir)

    if not HAS_FACEXFORMER:
        print("❌ FaceXFormer 未安装: pip install facexformer_pipeline")
        sys.exit(1)
    fxf = FaceXFormerAnalyzer()

    # ---- Stage 2: 逐图分析 ----
    print(f"\n🔍 分析人脸...")
    bins = defaultdict(list)
    skipped = {"no_face": 0}
    t0 = time.time()

    for i, img_path in enumerate(images):
        if (i + 1) % 100 == 0 or i == 0:
            elapsed = time.time() - t0
            speed = (i + 1) / max(elapsed, 0.01)
            eta = (len(images) - i - 1) / max(speed, 0.01)
            print(f"\r   [{i+1}/{len(images)}] {speed:.1f} img/s | ETA {eta:.0f}s", end="", flush=True)

        img = cv2.imread(str(img_path))
        if img is None:
            continue

        # InsightFace 检测（获取 bbox + embedding）
        faces = app.get(img)
        if not faces:
            skipped["no_face"] += 1
            continue

        face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]))

        # 质量评分
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        q = quality_score(img_gray, face)
        if q < args.min_quality:
            skipped["low_quality"] += 1
            continue

        # ---- 角度 + 表情 ----
        box = face.bbox.astype(int)
        fxf_result = fxf.analyze(img, face_box=box)
        yaw = fxf_result["yaw"]
        pitch = fxf_result["pitch"]
        expr_bin = fxf_result["expression_bin"] if not args.no_expression else None

        angle_bin = yaw_pitch_to_angle_bin(yaw, pitch)

        # 组合桶名
        if expr_bin and not args.no_expression:
            bin_name = f"{angle_bin}/{expr_bin}"
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
            "expression": expr_bin or "",
            "angle_bin": angle_bin,
        })

    print(f"\r   分析完成{'':40}")
    elapsed = time.time() - t0
    total_classified = sum(len(v) for v in bins.values())
    print(f"\n✅ 分析完成 ({elapsed:.1f}s, {len(images)/max(elapsed,0.01):.1f} img/s)")
    print(f"   通过: {total_classified} 张 → {len(bins)} 个桶")
    print(f"   跳过: 无人脸 {skipped['no_face']}, 质量过低 {skipped['low_quality']}")

    # ---- Stage 3: 桶内 embedding 去重 ----
    if args.dedup > 0 and not imagededup_remove:
        # 如果 fastdup 没跑或没装，用 embedding 去重
        print(f"\n🔄 桶内 embedding 去重 (阈值={args.dedup})...")
        before = sum(len(v) for v in bins.values())
        for bin_name in bins:
            has_emb = any(item["embedding"] is not None for item in bins[bin_name])
            if has_emb:
                bins[bin_name] = deduplicate_by_embedding(bins[bin_name], args.dedup)
            else:
                bins[bin_name].sort(key=lambda x: x["quality"], reverse=True)
        after = sum(len(v) for v in bins.values())
        print(f"   {before} → {after} (去除 {before - after} 张)")

    # 每桶取 top
    if args.max_per_bin and args.max_per_bin > 0:
        for bin_name in bins:
            bins[bin_name].sort(key=lambda x: x["quality"], reverse=True)
            bins[bin_name] = bins[bin_name][:args.max_per_bin]
        total_after = sum(len(v) for v in bins.values())
        print(f"   每桶限 {args.max_per_bin}，最终: {total_after} 张")

    # ---- Stage 4: 输出文件 ----
    print(f"\n💾 写入: {args.output}")
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    # 创建 review/ 和 rejected/ 目录
    (output_path / "review").mkdir(exist_ok=True)
    (output_path / "rejected").mkdir(exist_ok=True)

    total_output = 0
    csv_rows = []
    similarity_group_id = 0

    for bin_name, items in sorted(bins.items()):
        bin_dir = output_path / bin_name
        bin_dir.mkdir(parents=True, exist_ok=True)
        similarity_group_id += 1

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
                "angle_bin": item["angle_bin"],
                "expression": item["expression"],
                "quality": round(item["quality"], 1),
                "yaw": item["yaw"],
                "pitch": item["pitch"],
                "face_size": "",  # TODO: 从 bbox 计算
                "similarity_group": similarity_group_id,
                "selected": "yes",
                "dest": str(dst.relative_to(output_path)),
            })
            total_output += 1

    print(f"   ✅ {total_output} 张 → {len(bins)} 个文件夹")

    # metadata.csv
    csv_path = output_path / "metadata.csv"
    fieldnames = ["filename", "angle_bin", "expression", "quality", "yaw", "pitch",
                  "face_size", "similarity_group", "selected", "dest"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"📊 metadata.csv: {csv_path}")

    # 统计报告
    if args.report:
        report = generate_report(bins)
        report_path = output_path / "report.txt"
        report_path.write_text(report, encoding="utf-8")
        print(f"📊 report.txt: {report_path}")
        print(report)

    print(f"\n🎉 完成！目录结构:")
    print(f"   {args.output}/")
    for bin_name in sorted(list(bins.keys()))[:10]:
        print(f"   ├── {bin_name}/  ({len(bins[bin_name])} 张)")
    if len(bins) > 10:
        print(f"   └── ... ({len(bins) - 10} more)")
    print(f"   ├── review/     (人工复核)")
    print(f"   ├── rejected/   (废片)")
    print(f"   └── metadata.csv")


def generate_report(bins: dict) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("  人脸分类统计报告")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"{'桶':<30} {'数量':>6} {'平均质量':>10}")
    lines.append("-" * 50)

    angle_counts = defaultdict(int)
    expr_counts = defaultdict(int)

    for bin_name in sorted(bins.keys()):
        items = bins[bin_name]
        count = len(items)
        avg_q = np.mean([it["quality"] for it in items]) if items else 0
        lines.append(f"{bin_name:<30} {count:>6} {avg_q:>10.1f}")

        parts = bin_name.split("/")
        angle_counts[parts[0]] += count
        if len(parts) > 1:
            expr_counts[parts[1]] += count

    # 角度分布
    lines.append("")
    lines.append("--- 角度分布 ---")
    for angle in ANGLE_BINS:
        count = angle_counts.get(angle, 0)
        bar = "█" * min(count // 3, 40)
        lines.append(f"  {angle:<12} {count:>5}  {bar}")

    # 表情分布
    if expr_counts:
        lines.append("")
        lines.append("--- 表情分布 ---")
        for expr in EXPRESSION_BINS:
            count = expr_counts.get(expr, 0)
            bar = "█" * min(count // 3, 40)
            lines.append(f"  {expr:<12} {count:>5}  {bar}")

    # 空桶告警
    empty_angles = [a for a in ANGLE_BINS if angle_counts.get(a, 0) == 0]
    if empty_angles:
        lines.append("")
        lines.append("⚠️  缺失角度（需补充素材）:")
        for a in empty_angles:
            lines.append(f"  ❌ {a}")

    if expr_counts:
        empty_expr = [e for e in EXPRESSION_BINS if expr_counts.get(e, 0) == 0]
        if empty_expr:
            lines.append("")
            lines.append("⚠️  缺失表情:")
            for e in empty_expr:
                lines.append(f"  ❌ {e}")

    lines.append("")
    total = sum(len(v) for v in bins.values())
    lines.append(f"总计: {total} 张 | {len(bins)} 个桶")
    lines.append("")
    lines.append("建议: LoRA 训练集每桶 10-30 张，总计 300-800 张为宜")
    return "\n".join(lines)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="人脸分类 v2.0 — 角度×表情分桶（LoRA 数据集策展）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", "-i", required=True, help="输入图片目录")
    parser.add_argument("--output", "-o", required=True, help="输出分类目录")
    parser.add_argument("--recursive", "-r", action="store_true", help="递归扫描子目录")
    parser.add_argument("--max-per-bin", type=int, default=0, help="每桶最多保留几张（0=不限）")
    parser.add_argument("--no-expression", action="store_true", help="不做表情分类")
    parser.add_argument("--no-imagededup", action="store_true", help="不用 imagededup 去重")
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
