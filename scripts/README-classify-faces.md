# classify_faces.py — 人脸图片按角度×表情分桶

`extract_face_frames.py` 的下游工具，把人脸图片自动分到 `front/smile`、`left_30/neutral` 等子文件夹，用于 LoRA 训练数据集策展。

---

## Setup

与 `extract_face_frames.py` 共用 `faceextract` conda 环境，在此基础上追加以下依赖：

### 1. PyTorch CUDA 版（必须，不能用默认 CPU 版）

```powershell
# 查可用版本
pip index versions torch --index-url https://download.pytorch.org/whl/cu128

# 安装（取上面输出的最新版）
pip install torch==2.11.0+cu128 torchvision --index-url https://download.pytorch.org/whl/cu128 --force-reinstall
```

验证：
```powershell
python -c "import torch; print(torch.cuda.is_available())"
# 必须输出 True，否则 FaceXFormer 跑 CPU，速度慢 5-10 倍
```

### 2. FaceXFormer

```powershell
pip install facexformer_pipeline
```

首次运行自动从 HuggingFace 下载模型（~400MB），存到**当前目录**的 `ckpts/model.pt`，建议固定在项目根目录运行。

### 3. imagededup（可选，去重用）

```powershell
pip install imagededup
```

---

## 依赖版本

| 包 | 版本 |
|---|------|
| numpy | 1.26.4（必须 <2.0） |
| opencv-python-headless | 4.11.x（不要用 4.12+） |
| insightface | 0.7.3+ |
| onnxruntime-gpu | 1.17+ |
| torch | **CUDA 版**（如 2.11.0+cu128） |
| facexformer_pipeline | 0.2.8+ |
| imagededup | 任意（可选） |

---

## 使用方法

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
| `--no-expression` | — | 只按角度分桶 |
| `--no-imagededup` | — | 跳过 PHash 去重 |
| `--dedup` | 0.92 | embedding 去重阈值（0=禁用） |
| `--move` | — | 移动文件而非复制 |
| `--report` | — | 生成统计报告 |
