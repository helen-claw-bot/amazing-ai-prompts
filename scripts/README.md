# LoRA 训练素材处理工具集

从视频到 LoRA 训练数据集的完整 pipeline，包含视频切割、人脸提取、质量评级、可视化选图、角度表情分桶。

## Pipeline 总览

```
视频文件
  │
  ├─ cut_video.py          ← 切割出目标片段
  │
  ├─ extract_face_frames.py ← 按人物提取高质量人脸帧
  │
  ├─ recover_skipped_frames.py  ← 补救被跳过的帧（可选）
  │
  ├─ rate_face_images.py   ← 批量评级，写入 SQLite
  │
  ├─ web_selector/server.py ← 浏览器可视化筛选
  │
  └─ classify_faces.py     ← 按角度×表情分桶 → LoRA 数据集
```

---

## Setup

### 系统依赖：ffmpeg

```powershell
winget install ffmpeg
```

验证：`ffmpeg -version`

---

### Python 环境：faceextract（所有脚本共用）

```powershell
# 创建环境（Python 3.10，对 onnxruntime-gpu 兼容最好）
conda create -n faceextract python=3.10 -y
conda activate faceextract
```

> PowerShell 第一次用 conda activate 报错？运行 `conda init powershell` 后重开终端。

#### 基础依赖（extract / rate / recover 脚本）

```powershell
pip install numpy==1.26.4
pip install opencv-python-headless==4.11.0.86
pip install insightface
pip install onnxruntime-gpu
```

> ⚠️ `onnxruntime` 和 `onnxruntime-gpu` 不能共存，冲突！如已装 CPU 版先卸载：
> `pip uninstall onnxruntime -y`

验证 GPU 可用：
```powershell
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
# 应含 CUDAExecutionProvider
```

#### classify_faces.py 额外依赖

**1. PyTorch CUDA 版（必须，默认 pip 装的是 CPU 版！）**

CPU 版 torch 会让 FaceXFormer 跑在 CPU 上，速度慢 5-10 倍、CPU 占用接近 100%。

```powershell
# 查 CUDA wheel 可用版本（取最新的那个）
pip index versions torch --index-url https://download.pytorch.org/whl/cu128

# 安装（以 2.11.0+cu128 为例）
pip install torch==2.11.0+cu128 torchvision --index-url https://download.pytorch.org/whl/cu128 --force-reinstall
```

验证：
```powershell
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
# 应输出: 2.11.0+cu128  True
```

**2. FaceXFormer**

```powershell
pip install facexformer_pipeline
```

首次运行自动从 HuggingFace 下载模型（~400MB），存到**当前工作目录**的 `ckpts/model.pt`，建议固定在项目根目录运行脚本。

**3. imagededup（可选，PHash 去重）**

```powershell
pip install imagededup
```

#### web_selector 额外依赖

```powershell
pip install fastapi uvicorn aiofiles
```

---

### 依赖版本速查

| 包 | 版本 | 用途 |
|---|------|------|
| Python | 3.10.x | 环境 |
| numpy | **1.26.4**（必须 <2.0） | 基础计算 |
| opencv-python-headless | **4.11.x**（不要 4.12+） | 图像处理 |
| insightface | 0.7.3+ | 人脸检测 + embedding |
| onnxruntime-gpu | 1.17+ | InsightFace GPU 推理 |
| torch | **CUDA 版**（如 2.11.0+cu128） | FaceXFormer 推理 |
| facexformer_pipeline | 0.2.8+ | 角度 + 表情分析 |
| imagededup | 任意 | PHash 去重（可选） |
| fastapi / uvicorn | 最新 | Web 选图服务 |

---

## 脚本说明

### cut_video.py — 视频切割

仅依赖系统 ffmpeg，不需要 Python 包。`-c copy` 模式，不重新编码，速度极快。

```powershell
# 单段切割
python scripts/cut_video.py --video input.mp4 --start 00:10:30 --end 00:15:45 --output clip.mp4

# 批量模式（编辑脚本内 BATCH_CLIPS 列表后运行）
python scripts/cut_video.py --batch --video E:\AI\downloads\S01E01.mp4
```

---

### extract_face_frames.py — 人脸帧提取

给定参考照片，从视频里找目标人物的优质帧，按相似度+清晰度综合评分排序。

```powershell
conda activate faceextract

python scripts/extract_face_frames.py \
    --video E:\AI\downloads\S01E01.mp4 \
    --refs E:\AI\data\ref1.jpg E:\AI\data\ref2.jpg \
    --output E:\AI\downloads\S01E01_faces \
    --top 500 --fps 2 --blur 10 \
    --model-dir D:\AI\ComfyUI_models\insightface
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `--video` / `--dir` | 必填 | 单视频或目录批处理 |
| `--refs` | 必填 | 目标人物参考照片（1-5张，正脸清晰最佳） |
| `--top` | 100 | 最多保留几张 |
| `--fps` | 1 | 每秒采样帧数 |
| `--sim` | 0.45 | 相似度阈值 |
| `--blur` | 80 | 最低清晰度分 |
| `--skip-intro/outro` | 0 | 跳过片头/片尾秒数 |

输出：图片文件 + `report.csv`（含每帧详细评分）

---

### recover_skipped_frames.py — 补救跳过帧

`extract_face_frames.py` 有时因保存限制跳过部分帧（report.csv 里 filename 为空）。此脚本找回这些帧。

```powershell
python scripts/recover_skipped_frames.py \
    --dir E:\AI\downloads\CHTT \
    --sim 0.3
```

---

### rate_face_images.py — 图片质量评级

对人脸图片从清晰度、角度、人脸大小、完整度、宽高比五个维度评分，结果写入 SQLite 供后续筛选。

```powershell
conda activate faceextract

python scripts/rate_face_images.py \
    --input E:\AI\downloads\S01E01_faces \
    --recursive
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `--input` | 必填 | 图片目录 |
| `--recursive` | — | 递归扫描子目录 |
| `--db` | input/ratings.db | SQLite 输出路径 |
| `--export-grade` | — | 导出指定等级（A/B/C/AB） |
| `--export-dir` | — | 导出目标目录 |
| `--thresholds` | 80,60 | A/B/C 分界线 |

---

### web_selector/server.py — Web 可视化选图

启动本地 Web 服务，在浏览器里用滑块筛选、预览、导出图片。

```powershell
conda activate faceextract

python scripts/web_selector/server.py \
    --db E:\AI\downloads\S01E01_faces\ratings.db \
    --images E:\AI\downloads\S01E01_faces

# 浏览器访问 http://localhost:8765
```

---

### classify_faces.py — 角度×表情分桶

将人脸图片自动分到 `front/smile`、`left_30/neutral` 等子文件夹，LoRA 训练前的最后一步。

```powershell
conda activate faceextract

# 基础
python scripts/classify_faces.py -i ./faces -o ./dataset --report

# 每桶最多30张（LoRA 推荐）
python scripts/classify_faces.py -i ./faces -o ./dataset --max-per-bin 30 --report
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `--input, -i` | 必填 | 输入图片目录 |
| `--output, -o` | 必填 | 输出目录 |
| `--max-per-bin` | 0（不限） | 每桶保留张数（按质量取 top） |
| `--no-expression` | — | 只按角度分，不做表情分类 |
| `--no-imagededup` | — | 跳过 PHash 去重 |
| `--dedup` | 0.92 | embedding 去重阈值 |
| `--report` | — | 生成统计报告 |

输出：按 `角度/表情` 分层的文件夹 + `metadata.csv`
