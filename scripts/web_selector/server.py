#!/usr/bin/env python3
"""
Web 选图服务 - LoRA训练素材筛选
基于 FastAPI + HTMX + TailwindCSS CDN

启动:
    python scripts/web_selector/server.py --db E:\AI\downloads\LZJ\ratings.db --images E:\AI\downloads\LZJ
    # 浏览器访问 http://localhost:8765

依赖:
    pip install fastapi uvicorn aiofiles
"""

import argparse
import io
import os
import shutil
import sqlite3
import sys
from pathlib import Path
from contextlib import contextmanager

from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# ============================================================
# 配置
# ============================================================

DB_PATH: Path = None
IMAGES_ROOT: Path = None
THUMB_DIR: Path = None
THUMB_SIZE = 300  # 缩略图宽度


# ============================================================
# 数据库
# ============================================================

@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ============================================================
# App
# ============================================================

app = FastAPI(title="LoRA素材选图服务")


# ============================================================
# API 路由
# ============================================================

@app.get("/api/images")
def list_images(
    blur_min: float = Query(0),
    blur_max: float = Query(100),
    angle_min: float = Query(0),
    angle_max: float = Query(100),
    size_min: float = Query(0),
    size_max: float = Query(100),
    composite_min: float = Query(0),
    composite_max: float = Query(100),
    grade: str = Query("A,B,C"),
    composition: str = Query("closeup,halfbody,fullbody,distant"),
    folder: str = Query(""),
    sort: str = Query("composite_score"),
    order: str = Query("desc"),
    page: int = Query(1),
    page_size: int = Query(100),
):
    """筛选图片列表"""
    grades = [g.strip() for g in grade.split(",") if g.strip()]
    compositions = [c.strip() for c in composition.split(",") if c.strip()]

    # 构建SQL
    conditions = [
        "blur_score >= ? AND blur_score <= ?",
        "angle_score >= ? AND angle_score <= ?",
        "size_score >= ? AND size_score <= ?",
        "composite_score >= ? AND composite_score <= ?",
    ]
    params = [blur_min, blur_max, angle_min, angle_max, size_min, size_max, composite_min, composite_max]

    if grades:
        placeholders = ",".join("?" * len(grades))
        conditions.append(f"grade IN ({placeholders})")
        params.extend(grades)

    if compositions:
        placeholders = ",".join("?" * len(compositions))
        conditions.append(f"composition IN ({placeholders})")
        params.extend(compositions)

    if folder:
        conditions.append("folder = ?")
        params.append(folder)

    where = " AND ".join(conditions)
    allowed_sorts = {"composite_score", "blur_score", "angle_score", "size_score", "completeness_score", "yaw_deg", "filename"}
    if sort not in allowed_sorts:
        sort = "composite_score"
    order_dir = "DESC" if order.lower() == "desc" else "ASC"

    offset = (page - 1) * page_size

    with get_db() as conn:
        # 总数
        count_row = conn.execute(f"SELECT COUNT(*) FROM images WHERE {where}", params).fetchone()
        total = count_row[0]

        # 数据
        rows = conn.execute(
            f"SELECT * FROM images WHERE {where} ORDER BY {sort} {order_dir} LIMIT ? OFFSET ?",
            params + [page_size, offset]
        ).fetchall()

    images = [dict(r) for r in rows]
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "images": images,
    }


@app.get("/api/stats")
def get_stats():
    """统计数据"""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM images").fetchone()[0]
        grades = conn.execute("SELECT grade, COUNT(*) as cnt FROM images GROUP BY grade").fetchall()
        compositions = conn.execute("SELECT composition, COUNT(*) as cnt FROM images GROUP BY composition").fetchall()
        folders = conn.execute("SELECT folder, COUNT(*) as cnt FROM images GROUP BY folder ORDER BY folder").fetchall()
        avg_scores = conn.execute("""
            SELECT 
                ROUND(AVG(blur_score),1) as avg_blur,
                ROUND(AVG(angle_score),1) as avg_angle,
                ROUND(AVG(size_score),1) as avg_size,
                ROUND(AVG(composite_score),1) as avg_composite
            FROM images
        """).fetchone()

    return {
        "total": total,
        "grades": {r["grade"]: r["cnt"] for r in grades},
        "compositions": {r["composition"]: r["cnt"] for r in compositions},
        "folders": {r["folder"]: r["cnt"] for r in folders},
        "averages": dict(avg_scores) if avg_scores else {},
    }


@app.get("/api/folders")
def get_folders():
    """获取所有文件夹列表"""
    with get_db() as conn:
        rows = conn.execute("SELECT DISTINCT folder FROM images ORDER BY folder").fetchall()
    return [r["folder"] for r in rows]


@app.post("/api/images/mark")
async def mark_images(request: Request):
    """批量标记图片"""
    data = await request.json()
    paths = data.get("paths", [])
    mark = data.get("mark", "keep")  # keep / reject / star

    if not paths:
        raise HTTPException(400, "paths is empty")

    with get_db() as conn:
        # 确保mark字段存在
        try:
            conn.execute("ALTER TABLE images ADD COLUMN mark TEXT DEFAULT ''")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # 字段已存在

        placeholders = ",".join("?" * len(paths))
        conn.execute(f"UPDATE images SET mark = ? WHERE path IN ({placeholders})", [mark] + paths)
        conn.commit()

    return {"updated": len(paths), "mark": mark}


@app.post("/api/images/export")
async def export_images(request: Request):
    """导出筛选结果到目录"""
    data = await request.json()
    paths = data.get("paths", [])
    target_dir = data.get("target_dir", "")

    if not paths or not target_dir:
        raise HTTPException(400, "paths and target_dir required")

    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)

    copied = 0
    for p in paths:
        src = Path(p)
        if src.exists():
            shutil.copy2(src, target / src.name)
            copied += 1

    return {"copied": copied, "target_dir": str(target)}


@app.post("/api/recalculate")
async def recalculate(request: Request):
    """用新权重重算综合分"""
    data = await request.json()
    weights = data.get("weights", {"blur": 25, "angle": 25, "size": 20, "completeness": 15, "aspect": 15})
    thresholds = data.get("thresholds", [80, 60])

    total_w = sum(weights.values())
    if total_w == 0:
        raise HTTPException(400, "weights sum cannot be 0")

    with get_db() as conn:
        conn.execute(f"""
            UPDATE images SET
                composite_score = ROUND(
                    (blur_score * {weights.get('blur', 25)} +
                     angle_score * {weights.get('angle', 25)} +
                     size_score * {weights.get('size', 20)} +
                     completeness_score * {weights.get('completeness', 15)} +
                     aspect_score * {weights.get('aspect', 15)}) / {total_w}, 2),
                grade = CASE
                    WHEN (blur_score * {weights.get('blur', 25)} +
                          angle_score * {weights.get('angle', 25)} +
                          size_score * {weights.get('size', 20)} +
                          completeness_score * {weights.get('completeness', 15)} +
                          aspect_score * {weights.get('aspect', 15)}) / {total_w} >= {thresholds[0]} THEN 'A'
                    WHEN (blur_score * {weights.get('blur', 25)} +
                          angle_score * {weights.get('angle', 25)} +
                          size_score * {weights.get('size', 20)} +
                          completeness_score * {weights.get('completeness', 15)} +
                          aspect_score * {weights.get('aspect', 15)}) / {total_w} >= {thresholds[1]} THEN 'B'
                    ELSE 'C'
                END
        """)
        conn.commit()
        new_stats = conn.execute("SELECT grade, COUNT(*) as cnt FROM images GROUP BY grade").fetchall()

    return {"recalculated": True, "grades": {r["grade"]: r["cnt"] for r in new_stats}}


# ============================================================
# 缩略图
# ============================================================

@app.get("/api/thumbnail/{folder}/{filename}")
def get_thumbnail(folder: str, filename: str):
    """获取缩略图（按需生成并缓存）"""
    # 原图路径
    original = IMAGES_ROOT / folder / filename
    if not original.exists():
        # 尝试不带folder
        original = IMAGES_ROOT / filename
        if not original.exists():
            raise HTTPException(404, "Image not found")

    # 缩略图缓存路径
    thumb_path = THUMB_DIR / folder / filename
    if not thumb_path.exists():
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        # 生成缩略图
        import cv2
        img = cv2.imread(str(original))
        if img is None:
            raise HTTPException(500, "Cannot read image")
        h, w = img.shape[:2]
        new_w = THUMB_SIZE
        new_h = int(h * new_w / w)
        thumb = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(thumb_path), thumb, [cv2.IMWRITE_JPEG_QUALITY, 85])

    return FileResponse(str(thumb_path), media_type="image/jpeg")


@app.get("/api/original/{folder}/{filename}")
def get_original(folder: str, filename: str):
    """获取原图"""
    original = IMAGES_ROOT / folder / filename
    if not original.exists():
        original = IMAGES_ROOT / filename
        if not original.exists():
            raise HTTPException(404, "Image not found")
    return FileResponse(str(original))


# ============================================================
# 前端页面
# ============================================================

@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE


HTML_PAGE = """<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LoRA 素材选图</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <style>
        .thumb-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 8px; }
        .thumb-card { position: relative; cursor: pointer; border-radius: 8px; overflow: hidden; background: #1a1a2e; }
        .thumb-card img { width: 100%; aspect-ratio: 1; object-fit: cover; transition: transform 0.2s; }
        .thumb-card:hover img { transform: scale(1.05); }
        .thumb-card .badge { position: absolute; top: 4px; right: 4px; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
        .grade-A { background: #22c55e; color: white; }
        .grade-B { background: #f59e0b; color: white; }
        .grade-C { background: #ef4444; color: white; }
        .thumb-card .score { position: absolute; bottom: 0; left: 0; right: 0; padding: 4px; background: rgba(0,0,0,0.7); color: white; font-size: 11px; }
        .lightbox { position: fixed; inset: 0; background: rgba(0,0,0,0.9); z-index: 1000; display: none; justify-content: center; align-items: center; flex-direction: column; }
        .lightbox.active { display: flex; }
        .lightbox img { max-width: 90vw; max-height: 80vh; object-fit: contain; }
        .filter-panel { background: #0f172a; border-radius: 12px; padding: 16px; }
        .slider-group label { color: #94a3b8; font-size: 13px; }
        .slider-group input[type=range] { width: 100%; accent-color: #3b82f6; }
        body { background: #0a0a1a; color: #e2e8f0; }
        .stats-card { background: #1e293b; border-radius: 8px; padding: 12px 16px; text-align: center; }
    </style>
</head>
<body class="min-h-screen p-4">
    <div class="max-w-[1800px] mx-auto">
        <!-- Header -->
        <div class="flex items-center justify-between mb-4">
            <h1 class="text-2xl font-bold">🦐 LoRA 素材选图</h1>
            <div id="stats-bar" class="flex gap-3 text-sm"></div>
        </div>

        <div class="flex gap-4">
            <!-- 左侧筛选面板 -->
            <div class="w-72 flex-shrink-0">
                <div class="filter-panel sticky top-4 space-y-4">
                    <h2 class="text-lg font-semibold mb-2">筛选条件</h2>

                    <div class="slider-group">
                        <label>综合评分: <span id="v-composite">0-100</span></label>
                        <div class="flex gap-2">
                            <input type="range" id="composite_min" min="0" max="100" value="0" oninput="updateFilter()">
                            <input type="range" id="composite_max" min="0" max="100" value="100" oninput="updateFilter()">
                        </div>
                    </div>

                    <div class="slider-group">
                        <label>清晰度: <span id="v-blur">0-100</span></label>
                        <div class="flex gap-2">
                            <input type="range" id="blur_min" min="0" max="100" value="0" oninput="updateFilter()">
                            <input type="range" id="blur_max" min="0" max="100" value="100" oninput="updateFilter()">
                        </div>
                    </div>

                    <div class="slider-group">
                        <label>角度评分: <span id="v-angle">0-100</span></label>
                        <div class="flex gap-2">
                            <input type="range" id="angle_min" min="0" max="100" value="0" oninput="updateFilter()">
                            <input type="range" id="angle_max" min="0" max="100" value="100" oninput="updateFilter()">
                        </div>
                    </div>

                    <div class="slider-group">
                        <label>人脸大小: <span id="v-size">0-100</span></label>
                        <div class="flex gap-2">
                            <input type="range" id="size_min" min="0" max="100" value="0" oninput="updateFilter()">
                            <input type="range" id="size_max" min="0" max="100" value="100" oninput="updateFilter()">
                        </div>
                    </div>

                    <div>
                        <label class="text-sm text-slate-400">等级</label>
                        <div class="flex gap-2 mt-1">
                            <label class="flex items-center gap-1"><input type="checkbox" id="grade-A" checked onchange="updateFilter()"><span class="grade-A badge">A</span></label>
                            <label class="flex items-center gap-1"><input type="checkbox" id="grade-B" checked onchange="updateFilter()"><span class="grade-B badge">B</span></label>
                            <label class="flex items-center gap-1"><input type="checkbox" id="grade-C" checked onchange="updateFilter()"><span class="grade-C badge">C</span></label>
                        </div>
                    </div>

                    <div>
                        <label class="text-sm text-slate-400">构图</label>
                        <div class="flex flex-wrap gap-2 mt-1">
                            <label class="flex items-center gap-1 text-xs"><input type="checkbox" id="comp-closeup" checked onchange="updateFilter()">特写</label>
                            <label class="flex items-center gap-1 text-xs"><input type="checkbox" id="comp-halfbody" checked onchange="updateFilter()">半身</label>
                            <label class="flex items-center gap-1 text-xs"><input type="checkbox" id="comp-fullbody" checked onchange="updateFilter()">全身</label>
                            <label class="flex items-center gap-1 text-xs"><input type="checkbox" id="comp-distant" checked onchange="updateFilter()">远景</label>
                        </div>
                    </div>

                    <div>
                        <label class="text-sm text-slate-400">来源</label>
                        <select id="folder-select" class="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm" onchange="updateFilter()">
                            <option value="">全部</option>
                        </select>
                    </div>

                    <div>
                        <label class="text-sm text-slate-400">排序</label>
                        <select id="sort-select" class="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm" onchange="updateFilter()">
                            <option value="composite_score">综合分</option>
                            <option value="blur_score">清晰度</option>
                            <option value="angle_score">角度</option>
                            <option value="size_score">人脸大小</option>
                        </select>
                    </div>

                    <div class="pt-2 border-t border-slate-700">
                        <button onclick="exportSelected()" class="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm py-2 rounded">
                            导出筛选结果
                        </button>
                    </div>
                </div>
            </div>

            <!-- 右侧图片网格 -->
            <div class="flex-1">
                <div class="flex items-center justify-between mb-3">
                    <div id="result-count" class="text-sm text-slate-400"></div>
                    <div id="pagination" class="flex gap-2 text-sm"></div>
                </div>
                <div id="image-grid" class="thumb-grid"></div>
            </div>
        </div>
    </div>

    <!-- Lightbox -->
    <div id="lightbox" class="lightbox" onclick="closeLightbox()">
        <img id="lightbox-img" src="">
        <div id="lightbox-info" class="text-white text-sm mt-4 bg-black/50 p-3 rounded"></div>
    </div>

    <script>
    let currentPage = 1;
    const PAGE_SIZE = 100;

    async function loadFolders() {
        const res = await fetch('/api/folders');
        const folders = await res.json();
        const sel = document.getElementById('folder-select');
        folders.forEach(f => {
            const opt = document.createElement('option');
            opt.value = f; opt.textContent = f;
            sel.appendChild(opt);
        });
    }

    async function loadStats() {
        const res = await fetch('/api/stats');
        const data = await res.json();
        const bar = document.getElementById('stats-bar');
        bar.innerHTML = `
            <div class="stats-card">总计 <b>${data.total}</b></div>
            <div class="stats-card grade-A">A: <b>${data.grades.A || 0}</b></div>
            <div class="stats-card grade-B">B: <b>${data.grades.B || 0}</b></div>
            <div class="stats-card grade-C">C: <b>${data.grades.C || 0}</b></div>
        `;
    }

    function getFilterParams() {
        const grades = [];
        if (document.getElementById('grade-A').checked) grades.push('A');
        if (document.getElementById('grade-B').checked) grades.push('B');
        if (document.getElementById('grade-C').checked) grades.push('C');

        const comps = [];
        if (document.getElementById('comp-closeup').checked) comps.push('closeup');
        if (document.getElementById('comp-halfbody').checked) comps.push('halfbody');
        if (document.getElementById('comp-fullbody').checked) comps.push('fullbody');
        if (document.getElementById('comp-distant').checked) comps.push('distant');

        const params = new URLSearchParams({
            blur_min: document.getElementById('blur_min').value,
            blur_max: document.getElementById('blur_max').value,
            angle_min: document.getElementById('angle_min').value,
            angle_max: document.getElementById('angle_max').value,
            size_min: document.getElementById('size_min').value,
            size_max: document.getElementById('size_max').value,
            composite_min: document.getElementById('composite_min').value,
            composite_max: document.getElementById('composite_max').value,
            grade: grades.join(','),
            composition: comps.join(','),
            folder: document.getElementById('folder-select').value,
            sort: document.getElementById('sort-select').value,
            order: 'desc',
            page: currentPage,
            page_size: PAGE_SIZE,
        });

        // 更新显示
        document.getElementById('v-composite').textContent = `${params.get('composite_min')}-${params.get('composite_max')}`;
        document.getElementById('v-blur').textContent = `${params.get('blur_min')}-${params.get('blur_max')}`;
        document.getElementById('v-angle').textContent = `${params.get('angle_min')}-${params.get('angle_max')}`;
        document.getElementById('v-size').textContent = `${params.get('size_min')}-${params.get('size_max')}`;

        return params;
    }

    let filterTimeout;
    function updateFilter() {
        clearTimeout(filterTimeout);
        filterTimeout = setTimeout(() => {
            currentPage = 1;
            loadImages();
        }, 200);  // 防抖
    }

    async function loadImages() {
        const params = getFilterParams();
        const res = await fetch(`/api/images?${params}`);
        const data = await res.json();

        document.getElementById('result-count').textContent = `共 ${data.total} 张 (第 ${data.page}/${data.pages} 页)`;

        const grid = document.getElementById('image-grid');
        grid.innerHTML = data.images.map(img => `
            <div class="thumb-card" onclick="openLightbox('${img.folder}', '${img.filename}', ${JSON.stringify(img).replace(/"/g, '&quot;')})">
                <img src="/api/thumbnail/${img.folder}/${img.filename}" loading="lazy" alt="${img.filename}">
                <span class="badge grade-${img.grade}">${img.grade}</span>
                <div class="score">${img.composite_score} | 🔍${img.blur_score} 📐${img.angle_score}</div>
            </div>
        `).join('');

        // 分页
        const pag = document.getElementById('pagination');
        let pagHtml = '';
        if (data.page > 1) pagHtml += `<button onclick="goPage(${data.page-1})" class="px-2 py-1 bg-slate-700 rounded">← 上一页</button>`;
        if (data.page < data.pages) pagHtml += `<button onclick="goPage(${data.page+1})" class="px-2 py-1 bg-slate-700 rounded">下一页 →</button>`;
        pag.innerHTML = pagHtml;
    }

    function goPage(p) { currentPage = p; loadImages(); window.scrollTo(0, 0); }

    function openLightbox(folder, filename, info) {
        document.getElementById('lightbox-img').src = `/api/original/${folder}/${filename}`;
        document.getElementById('lightbox-info').innerHTML = `
            <b>${filename}</b><br>
            综合: ${info.composite_score} | 清晰度: ${info.blur_score} | 角度: ${info.angle_score}<br>
            大小: ${info.size_score} | 完整度: ${info.completeness_score} | 构图: ${info.composition}<br>
            偏角: ${info.yaw_deg}° | 检测置信度: ${info.det_confidence}
        `;
        document.getElementById('lightbox').classList.add('active');
    }

    function closeLightbox() { document.getElementById('lightbox').classList.remove('active'); }

    async function exportSelected() {
        const dir = prompt('导出目标目录路径:');
        if (!dir) return;
        const params = getFilterParams();
        // 获取所有符合条件的路径
        params.set('page_size', '100000');
        params.set('page', '1');
        const res = await fetch(`/api/images?${params}`);
        const data = await res.json();
        const paths = data.images.map(i => i.path);
        const expRes = await fetch('/api/images/export', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({paths, target_dir: dir}),
        });
        const result = await expRes.json();
        alert(`导出完成! 共 ${result.copied} 张 → ${result.target_dir}`);
    }

    // 初始化
    loadFolders();
    loadStats();
    loadImages();
    </script>
</body>
</html>"""


# ============================================================
# 启动
# ============================================================

def main():
    global DB_PATH, IMAGES_ROOT, THUMB_DIR

    parser = argparse.ArgumentParser(description="Web选图服务")
    parser.add_argument("--db", required=True, help="ratings.db 路径")
    parser.add_argument("--images", required=True, help="图片根目录")
    parser.add_argument("--port", type=int, default=8765, help="端口号（默认8765）")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址（默认0.0.0.0）")
    args = parser.parse_args()

    DB_PATH = Path(args.db)
    IMAGES_ROOT = Path(args.images)
    THUMB_DIR = IMAGES_ROOT / ".thumbnails"
    THUMB_DIR.mkdir(exist_ok=True)

    if not DB_PATH.exists():
        print(f"❌ 数据库不存在: {DB_PATH}")
        print(f"   请先运行评级脚本: python scripts/rate_face_images.py --input {IMAGES_ROOT}")
        sys.exit(1)

    print(f"🦐 Web选图服务启动中...")
    print(f"   数据库: {DB_PATH}")
    print(f"   图片目录: {IMAGES_ROOT}")
    print(f"   缩略图缓存: {THUMB_DIR}")
    print(f"   访问: http://localhost:{args.port}")
    print()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
