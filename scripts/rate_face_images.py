#!/usr/bin/env python3
"""
rate_face_images.py
批量评级人脸图片质量，为LoRA训练素材筛选服务

依赖（与 extract_face_frames.py 相同，无新增）:
    pip install insightface opencv-python onnxruntime-gpu numpy<2.0

用法:
    python scripts/rate_face_images.py --input E:\AI\downloads\LZJ\01_faces
    python scripts/rate_face_images.py --input E:\AI\downloads\LZJ --recursive
    python scripts/rate_face_images.py --input ./faces --export-grade A --export-dir ./selected

参数说明:
    --input       输入图片目录
    --recursive   递归扫描子目录（适合批量多集）
    --db          SQLite数据库输出路径（默认: input目录下的 ratings.db）
    --export-grade 导出指定等级图片到目录（A/B/C）
    --export-dir  导出目标目录
    --weights     评分权重 JSON，默认 {"blur":25,"angle":25,"size":20,"completeness":15,"aspect":15}
    --thresholds  ABC分界线，默认 "80,60"（>=80为A，>=60为B，<60为C）
    --batch-size  每批处理图片数（默认500，控制内存）
    --model-dir   InsightFace模型目录
"""

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

# CUDA DLL路径（与extract_face_frames.py一致）
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
    print("❌ 请先安装依赖: pip install insightface opencv-python onnxruntime-gpu numpy")
    sys.exit(1)


# ============================================================
# 评分函数
# ============================================================

def score_blur(img_gray, face_box=None):
    """清晰度评分 (0-100)
    基于Laplacian方差对数映射，如果有face_box则只评估人脸区域
    参考: <30严重模糊, 30-55模糊, 55-75尚可, 75-90清晰, >90非常清晰
    对数映射: lap_var≈10→25, ≈100→50, ≈1000→75, ≈10000→100
    """
    if face_box is not None:
        x1, y1, x2, y2 = face_box
        roi = img_gray[y1:y2, x1:x2]
        if roi.size == 0:
            roi = img_gray
    else:
        roi = img_gray
    lap_var = cv2.Laplacian(roi, cv2.CV_64F).var()
    if lap_var <= 0:
        return 0.0
    # 对数映射: log10(lap_var+1)/4 * 100, lap_var=10000时满分
    return min(float(np.log10(lap_var + 1) / 4.0 * 100), 100.0)


def score_blur_landmarks(img_gray, face, face_box=None):
    """清晰度评分——关键点改进版 (0-100)
    基于人脸5点关键点，分别计算双眼(各40%)和嘴巴(20%)区域的清晰度，加权合并。

    度量方式：Laplacian 绝对值的 top-10% 像素均值（而非全区域方差）。
    原因：方差会被 patch 内大面积光滑皮肤稀释——近景脸大 patch 大导致分低，
    远景脸小 patch 小反而分高。高百分位均值只看最锐利边缘，不受平滑区影响。

    对数映射比例系数 2.0：top-10%均值典型范围 ~2-100（vs 方差 ~10-10000），
    log10(100+1)/2.0≈100，与 score_blur 量纲兼容。
    """
    kps = face.kps  # [左眼, 右眼, 鼻尖, 左嘴角, 右嘴角]
    h, w = img_gray.shape[:2]

    eye_dist = abs(float(kps[1][0]) - float(kps[0][0]))
    if eye_dist < 4:
        return score_blur(img_gray, face_box)

    half = max(int(eye_dist * 0.38), 10)

    def _roi_sharpness(cx, cy, hw, hh):
        x1 = max(0, int(cx - hw))
        y1 = max(0, int(cy - hh))
        x2 = min(w, int(cx + hw))
        y2 = min(h, int(cy + hh))
        if (x2 - x1) < 4 or (y2 - y1) < 4:
            return None
        roi = img_gray[y1:y2, x1:x2]
        lap = np.abs(cv2.Laplacian(roi, cv2.CV_64F))
        # top-10% 像素均值：只看最锐利边缘，不被平滑皮肤区拖低
        threshold = np.percentile(lap, 90)
        return float(lap[lap >= threshold].mean())

    val_le = _roi_sharpness(kps[0][0], kps[0][1], half, half)
    val_re = _roi_sharpness(kps[1][0], kps[1][1], half, half)

    mx = (float(kps[3][0]) + float(kps[4][0])) / 2
    my = (float(kps[3][1]) + float(kps[4][1])) / 2
    mouth_hw = max(int(abs(float(kps[4][0]) - float(kps[3][0])) * 0.6), int(half * 0.6))
    mouth_hh = max(int(eye_dist * 0.22), 8)
    val_mouth = _roi_sharpness(mx, my, mouth_hw, mouth_hh)

    regions = [(val_le, 0.4), (val_re, 0.4), (val_mouth, 0.2)]
    total_w = sum(wt for v, wt in regions if v is not None)
    if total_w == 0:
        return score_blur(img_gray, face_box)

    sharpness = sum(v * wt for v, wt in regions if v is not None) / total_w
    if sharpness <= 0:
        return 0.0
    # 对数映射：除数 2.0 对应 top-10%均值量级（满分约 val≈100）
    return min(float(np.log10(sharpness + 1) / 2.0 * 100), 100.0)


def score_angle(face):
    """角度评分 (0-100)
    正脸=100, 侧面45°=50, 90°=0
    """
    kps = face.kps  # 5点: 左眼,右眼,鼻尖,左嘴角,右嘴角
    left_eye, right_eye = kps[0], kps[1]
    nose = kps[2]
    eye_center_x = (left_eye[0] + right_eye[0]) / 2
    eye_width = abs(right_eye[0] - left_eye[0])
    if eye_width < 1:
        return 0.0
    # yaw估算
    offset = abs(nose[0] - eye_center_x)
    yaw = min((offset / eye_width) * 90, 90.0)
    # pitch粗略估算（鼻尖相对眼睛中心的垂直偏移）
    eye_center_y = (left_eye[1] + right_eye[1]) / 2
    vert_offset = nose[1] - eye_center_y
    expected_vert = eye_width * 0.6  # 正脸时鼻尖大约在眼睛下方0.6个眼距
    pitch = abs(vert_offset - expected_vert) / max(eye_width, 1) * 60
    pitch = min(pitch, 45.0)
    # 综合角度
    total_angle = (yaw * 0.7 + pitch * 0.3)
    return max(0, 100 - total_angle * (100 / 45))


def score_face_size(face_box, img_shape):
    """人脸大小占比评分 (0-100)
    人脸占图面积15-50%为最佳(半身), <5%太小, >80%过度特写
    """
    x1, y1, x2, y2 = face_box
    face_area = (x2 - x1) * (y2 - y1)
    img_area = img_shape[0] * img_shape[1]
    ratio = face_area / max(img_area, 1)
    # 最佳区间 10%-60%
    if 0.10 <= ratio <= 0.60:
        return 100.0
    elif ratio < 0.10:
        return max(0, ratio / 0.10 * 100)
    else:  # >60%
        return max(0, 100 - (ratio - 0.60) / 0.40 * 80)


def score_completeness(face):
    """人脸完整度评分 (0-100)
    基于检测置信度 + landmark点分布合理性
    """
    det_score = float(face.det_score) * 100  # 0-1 → 0-100
    # 检查landmark点是否都在合理位置（不在图片边缘）
    kps = face.kps
    box = face.bbox
    w = box[2] - box[0]
    h = box[3] - box[1]
    if w < 1 or h < 1:
        return det_score * 0.5
    # 所有关键点应在bbox内或附近
    in_box_count = 0
    for kp in kps:
        if box[0] - w * 0.1 <= kp[0] <= box[2] + w * 0.1 and \
           box[1] - h * 0.1 <= kp[1] <= box[3] + h * 0.1:
            in_box_count += 1
    landmark_score = (in_box_count / 5.0) * 100
    return det_score * 0.6 + landmark_score * 0.4


def score_aspect_ratio(face_box, img_shape):
    """宽高比评分 (0-100)
    评估裁剪图是否适合训练（接近正方形或4:5最佳）
    """
    h, w = img_shape[:2]
    if w == 0 or h == 0:
        return 0
    ratio = max(w, h) / min(w, h)
    # 1:1 = 100, 4:5=95, 16:9≈60, 超宽/超高扣分
    if ratio <= 1.25:
        return 100.0
    elif ratio <= 1.5:
        return 90.0
    elif ratio <= 1.8:
        return 70.0
    else:
        return max(0, 100 - (ratio - 1) * 40)


def classify_composition(face_box, img_shape):
    """构图分类: closeup / halfbody / fullbody / distant
    用脸高占图高的比值判断，比面积比更符合摄影构图直觉。
    closeup  : 脸高 > 45% 图高（特写）
    halfbody : 25%–45%（中近景/半身）
    fullbody : 10%–25%（中景/全身）
    distant  : < 10%（远景）
    """
    _, y1, _, y2 = face_box
    face_h = y2 - y1
    img_h = img_shape[0]
    h_ratio = face_h / max(img_h, 1)
    if h_ratio > 0.45:
        return "closeup"
    elif h_ratio > 0.25:
        return "halfbody"
    elif h_ratio > 0.10:
        return "fullbody"
    else:
        return "distant"


# ============================================================
# 数据库
# ============================================================

def init_db(db_path):
    """创建SQLite数据库和表"""
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS images (
            path TEXT PRIMARY KEY,
            filename TEXT,
            folder TEXT,
            width INTEGER,
            height INTEGER,
            blur_score REAL,
            angle_score REAL,
            size_score REAL,
            completeness_score REAL,
            aspect_score REAL,
            composite_score REAL,
            grade TEXT,
            composition TEXT,
            face_ratio REAL,
            yaw_deg REAL,
            det_confidence REAL,
            face_x1 INTEGER,
            face_y1 INTEGER,
            face_x2 INTEGER,
            face_y2 INTEGER
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_composite ON images(composite_score)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_grade ON images(grade)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_blur ON images(blur_score)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_angle ON images(angle_score)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_composition ON images(composition)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_folder ON images(folder)")
    conn.commit()
    return conn


def insert_rating(conn, data):
    """插入或更新一条评分记录"""
    conn.execute("""
        INSERT OR REPLACE INTO images VALUES (
            :path, :filename, :folder, :width, :height,
            :blur_score, :angle_score, :size_score, :completeness_score, :aspect_score,
            :composite_score, :grade, :composition, :face_ratio, :yaw_deg,
            :det_confidence, :face_x1, :face_y1, :face_x2, :face_y2
        )
    """, data)


# ============================================================
# 主逻辑
# ============================================================

def load_face_app(model_dir=None):
    """初始化 InsightFace"""
    import onnxruntime as ort
    available = ort.get_available_providers()
    if "CUDAExecutionProvider" in available:
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        print("🚀 使用 GPU (CUDA) 加速")
    else:
        providers = ["CPUExecutionProvider"]
        print("💻 使用 CPU 模式")
    kwargs = {"name": "buffalo_l", "providers": providers}
    if model_dir:
        kwargs["root"] = model_dir
    app = FaceAnalysis(**kwargs)
    app.prepare(ctx_id=0, det_size=(640, 640))
    return app


def collect_images(input_dir, recursive=False):
    """收集所有图片文件路径"""
    extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    input_path = Path(input_dir)
    if recursive:
        files = [p for p in input_path.rglob("*") if p.suffix.lower() in extensions]
    else:
        files = [p for p in input_path.iterdir() if p.is_file() and p.suffix.lower() in extensions]
    return sorted(files)


def rate_image(app, img_path, weights):
    """对单张图片评分，返回评分字典或None（无人脸时）"""
    img = cv2.imread(str(img_path))
    if img is None:
        return None

    faces = app.get(img)
    if not faces:
        return None

    # 取置信度最高的人脸
    face = max(faces, key=lambda f: f.det_score)
    box = face.bbox.astype(int)
    x1, y1, x2, y2 = max(0, box[0]), max(0, box[1]), min(img.shape[1], box[2]), min(img.shape[0], box[3])

    if x2 <= x1 or y2 <= y1:
        return None

    face_box = (x1, y1, x2, y2)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 各维度评分
    blur = score_blur_landmarks(gray, face, face_box)
    angle = score_angle(face)
    size = score_face_size(face_box, img.shape)
    completeness = score_completeness(face)
    aspect = score_aspect_ratio(face_box, img.shape)

    # 加权综合分
    w = weights
    total_weight = w["blur"] + w["angle"] + w["size"] + w["completeness"] + w["aspect"]
    composite = (
        blur * w["blur"] +
        angle * w["angle"] +
        size * w["size"] +
        completeness * w["completeness"] +
        aspect * w["aspect"]
    ) / total_weight

    # 构图分类
    composition = classify_composition(face_box, img.shape)

    # yaw角度（用于筛选）
    kps = face.kps
    left_eye, right_eye, nose = kps[0], kps[1], kps[2]
    eye_center_x = (left_eye[0] + right_eye[0]) / 2
    eye_width = abs(right_eye[0] - left_eye[0])
    yaw_deg = min(abs(nose[0] - eye_center_x) / max(eye_width, 1) * 90, 90.0)

    # 人脸占比
    face_area = (x2 - x1) * (y2 - y1)
    img_area = img.shape[0] * img.shape[1]
    face_ratio = face_area / max(img_area, 1)

    return {
        "path": str(img_path),
        "filename": img_path.name,
        "folder": img_path.parent.name,
        "width": img.shape[1],
        "height": img.shape[0],
        "blur_score": round(blur, 2),
        "angle_score": round(angle, 2),
        "size_score": round(size, 2),
        "completeness_score": round(completeness, 2),
        "aspect_score": round(aspect, 2),
        "composite_score": round(composite, 2),
        "grade": "",  # 后面统一分配
        "composition": composition,
        "face_ratio": round(face_ratio, 4),
        "yaw_deg": round(yaw_deg, 1),
        "det_confidence": round(float(face.det_score), 4),
        "face_x1": x1,
        "face_y1": y1,
        "face_x2": x2,
        "face_y2": y2,
    }


def assign_grade(score, thresholds):
    """根据综合分分配等级"""
    if score >= thresholds[0]:
        return "A"
    elif score >= thresholds[1]:
        return "B"
    else:
        return "C"


def main():
    parser = argparse.ArgumentParser(description="批量评级人脸图片质量")
    parser.add_argument("--input", required=True, help="输入图片目录")
    parser.add_argument("--recursive", action="store_true", help="递归扫描子目录")
    parser.add_argument("--db", default=None, help="SQLite输出路径（默认: input/ratings.db）")
    parser.add_argument("--export-grade", choices=["A", "B", "C", "AB"], default=None,
                        help="导出指定等级到目录")
    parser.add_argument("--export-dir", default=None, help="导出目标目录")
    parser.add_argument("--weights", default=None,
                        help='评分权重JSON，默认 {"blur":25,"angle":25,"size":20,"completeness":15,"aspect":15}')
    parser.add_argument("--thresholds", default="80,60",
                        help="ABC分界线，逗号分隔（默认 80,60）")
    parser.add_argument("--batch-size", type=int, default=500, help="每批处理数量（默认500）")
    parser.add_argument("--model-dir", default=None, help="InsightFace模型目录")
    args = parser.parse_args()

    # 解析权重
    import json
    if args.weights:
        weights = json.loads(args.weights)
    else:
        weights = {"blur": 25, "angle": 25, "size": 20, "completeness": 15, "aspect": 15}

    # 解析阈值
    thresholds = [float(x) for x in args.thresholds.split(",")]
    assert len(thresholds) == 2 and thresholds[0] > thresholds[1], "阈值格式: high,low (如 80,60)"

    # 数据库路径
    input_path = Path(args.input)
    db_path = Path(args.db) if args.db else input_path / "ratings.db"

    print("🦐 人脸图片评级工具 v1.0")
    print("=" * 50)
    print(f"📂 输入目录: {input_path}")
    print(f"📊 数据库: {db_path}")
    print(f"⚖️  权重: {weights}")
    print(f"📏 分级阈值: A≥{thresholds[0]}, B≥{thresholds[1]}, C<{thresholds[1]}")
    print()

    # 收集图片
    print("🔍 扫描图片文件...")
    images = collect_images(args.input, args.recursive)
    total = len(images)
    print(f"   找到 {total} 张图片")
    if total == 0:
        print("⚠️  未找到图片，退出")
        return

    # 初始化
    app = load_face_app(args.model_dir)
    conn = init_db(db_path)

    # 检查已处理的（支持断点续传）
    existing = set()
    cursor = conn.execute("SELECT path FROM images")
    for row in cursor:
        existing.add(row[0])
    skip_count = sum(1 for img in images if str(img) in existing)
    if skip_count:
        print(f"⏭  跳过已评分: {skip_count} 张")

    # 处理
    print(f"\n🔬 开始评级...")
    start_time = time.time()
    processed = 0
    no_face = 0
    grades = {"A": 0, "B": 0, "C": 0}

    for i, img_path in enumerate(images):
        if str(img_path) in existing:
            continue

        result = rate_image(app, img_path, weights)
        if result is None:
            no_face += 1
        else:
            result["grade"] = assign_grade(result["composite_score"], thresholds)
            grades[result["grade"]] += 1
            insert_rating(conn, result)

        processed += 1

        # 每batch提交一次 + 打印进度
        if processed % args.batch_size == 0:
            conn.commit()
            elapsed = time.time() - start_time
            rate = processed / elapsed
            remaining = (total - skip_count - processed) / rate if rate > 0 else 0
            print(f"\r   进度: {processed + skip_count}/{total} "
                  f"| A:{grades['A']} B:{grades['B']} C:{grades['C']} "
                  f"| 无脸:{no_face} "
                  f"| {rate:.1f}张/秒 "
                  f"| 剩余:{remaining/60:.1f}min",
                  end="", flush=True)

    conn.commit()
    elapsed = time.time() - start_time
    print(f"\n\n✅ 评级完成! 耗时 {elapsed/60:.1f} 分钟")
    print(f"   总计: {total} 张")
    print(f"   已评分: {processed + skip_count} 张（本次: {processed}）")
    print(f"   无人脸: {no_face} 张")
    print(f"   等级分布: A={grades['A']}  B={grades['B']}  C={grades['C']}")
    print(f"   数据库: {db_path}")

    # 导出功能
    if args.export_grade and args.export_dir:
        export_dir = Path(args.export_dir)
        export_dir.mkdir(parents=True, exist_ok=True)
        if args.export_grade == "AB":
            query = "SELECT path FROM images WHERE grade IN ('A', 'B')"
        else:
            query = f"SELECT path FROM images WHERE grade = '{args.export_grade}'"
        rows = conn.execute(query).fetchall()
        print(f"\n💾 导出 {args.export_grade} 级图片: {len(rows)} 张 → {export_dir}")
        import shutil
        for (src_path,) in rows:
            src = Path(src_path)
            if src.exists():
                shutil.copy2(src, export_dir / src.name)
        print(f"   ✅ 导出完成")

    # 打印查询示例
    print(f"\n💡 查询示例:")
    print(f'   sqlite3 "{db_path}" "SELECT filename, composite_score, grade FROM images WHERE blur_score>50 AND angle_score>70 ORDER BY composite_score DESC LIMIT 20"')
    print(f'   sqlite3 "{db_path}" "SELECT grade, COUNT(*) FROM images GROUP BY grade"')
    print(f'   sqlite3 "{db_path}" "SELECT composition, COUNT(*) FROM images GROUP BY composition"')

    conn.close()


if __name__ == "__main__":
    main()
