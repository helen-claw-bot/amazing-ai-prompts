# Web 选图服务 - 需求设计文档

## 1. 概述

基于 `rate_face_images.py` 生成的 SQLite 评分数据，提供 Web 界面进行可视化筛选、预览和导出，服务于 LoRA 训练素材的最终挑选。

**目标用户：** 本地 Windows 机器上运行，浏览器访问  
**数据规模：** ~100,000 张图片，评分数据存储在 SQLite  

---

## 2. 技术选型

| 层 | 技术 | 理由 |
|---|---|---|
| 后端 | FastAPI (Python) | 与评级脚本同生态，共享依赖 |
| 前端 | Vue 3 + Vite | 轻量、响应快、组件化 |
| 图片服务 | FastAPI StaticFiles + 缩略图缓存 | 避免前端直接加载原图 |
| 数据库 | SQLite (ratings.db) | 零部署、已有数据 |
| 通信 | REST API + SSE (可选) | 简单、无需WebSocket |

**备选极简方案：** 纯 Python (FastAPI + Jinja2 模板)，无需Node/npm，适合快速上线。

---

## 3. 功能需求

### 3.1 筛选面板

| 筛选项 | 类型 | 说明 |
|--------|------|------|
| 综合评分 | 范围滑块 | 0-100 |
| 清晰度 (blur_score) | 范围滑块 | 0-100 |
| 角度 (angle_score) | 范围滑块 | 0-100 |
| 人脸大小 (size_score) | 范围滑块 | 0-100 |
| 完整度 (completeness) | 范围滑块 | 0-100 |
| 等级 | 多选 | A / B / C |
| 构图类型 | 多选 | closeup / halfbody / fullbody / distant |
| 来源文件夹 | 下拉/多选 | 按集/来源筛选 |
| 偏角 (yaw_deg) | 范围滑块 | 0-90° |

### 3.2 图片浏览

- **缩略图网格** — 默认 200×200px 缩略图，懒加载
- **分页/虚拟滚动** — 支持10万张不卡（每页100-200张）
- **排序** — 按综合分/清晰度/角度/时间排序
- **点击放大** — Lightbox 查看原图 + 评分详情
- **批量选择** — Shift+点击多选、全选当前筛选结果

### 3.3 标记与操作

- **手动标记** — 👍保留 / 👎淘汰 / ⭐精选（存入DB新字段）
- **批量导出** — 将当前筛选/选中结果复制到指定目录
- **批量删除** — 移除评分记录（可选同时删源文件）
- **去重预览** — 相似图并排展示，一键保留最优

### 3.4 统计仪表盘

- 等级分布饼图 (A/B/C)
- 各维度评分直方图
- 构图类型分布
- 每集/文件夹数量统计

---

## 4. API 设计

```
GET  /api/images?blur_min=50&angle_min=70&grade=A,B&composition=halfbody&sort=composite_score&order=desc&page=1&page_size=100
GET  /api/images/{id}            — 单张详情
GET  /api/stats                  — 统计数据
GET  /api/folders                — 所有来源文件夹列表
POST /api/images/mark            — 批量标记 {ids: [...], mark: "keep"|"reject"|"star"}
POST /api/images/export          — 导出 {filter: {...}, target_dir: "..."}
GET  /api/thumbnail/{filename}   — 缩略图（按需生成并缓存）
GET  /api/original/{filename}    — 原图
```

---

## 5. 缩略图策略

原图可能很大（3840宽），前端不能直接加载。

- 首次访问时后端自动生成 300px 宽缩略图
- 缓存到 `{db_dir}/.thumbnails/` 目录
- 使用 OpenCV resize，JPEG quality 85
- 预生成模式：启动服务时后台线程批量生成

预估缩略图磁盘占用：100,000 × ~15KB = ~1.5GB

---

## 6. 性能设计

| 场景 | 目标 | 方案 |
|------|------|------|
| 筛选查询 | <100ms | SQLite索引 + 参数化SQL |
| 缩略图加载 | 首屏<1s | 懒加载 + 缓存 + CDN-like headers |
| 10万图浏览 | 不卡 | 虚拟滚动 or 分页 (100/页) |
| 导出1000张 | <30s | 异步复制 + 进度SSE推送 |

---

## 7. 目录结构

```
scripts/
├── rate_face_images.py          # 评级脚本（已完成）
├── web_selector/
│   ├── server.py                # FastAPI 后端
│   ├── requirements.txt         # fastapi, uvicorn, aiofiles
│   ├── static/                  # 前端构建产物 (或 Jinja2 模板)
│   │   ├── index.html
│   │   ├── app.js
│   │   └── style.css
│   └── README.md                # 使用说明
```

---

## 8. 启动方式

```bash
# 评级完成后启动Web服务
python scripts/web_selector/server.py --db E:\AI\downloads\LZJ\ratings.db --images E:\AI\downloads\LZJ

# 浏览器访问
# http://localhost:8765
```

---

## 9. 开发计划

| 阶段 | 内容 | 预计 |
|------|------|------|
| P1 | 后端API + 缩略图 + 纯HTML筛选页 | 1天 |
| P2 | 前端美化 + 虚拟滚动 + Lightbox | 1天 |
| P3 | 标记/导出/去重功能 | 0.5天 |
| P4 | 统计仪表盘 | 0.5天 |

**P1 交付即可用**，后续迭代优化体验。

---

## 10. 开放问题

1. **是否需要多人物支持？** — 如果图片中混有多个角色，是否需要按人物分组筛选
2. **是否需要在线重新评分？** — 修改权重后Web端实时重算分数
3. **是否需要标注/打标功能？** — 在Web上直接给图片写caption（为后续训练准备）
4. **部署方式？** — 纯本地 or 也考虑局域网内其他设备访问

---

## 11. 依赖清单

```
# 后端（无新增重量级依赖）
fastapi>=0.100
uvicorn>=0.20
aiofiles>=23.0
python-multipart>=0.0.6

# 前端（如果用Vue方案）
node >= 18
vue@3
vite
```

**极简方案（零前端构建）：** FastAPI + Jinja2 + HTMX + TailwindCSS CDN → 一个 server.py 搞定，无需 Node。
