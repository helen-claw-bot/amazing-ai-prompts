# extract_face_frames.py — 从视频中提取指定人物的优质人脸帧

## 这个脚本是干什么的

你有一段视频，里面有很多人，你只想要**某个人**出现的帧，而且要质量够好（清晰、正脸、没遮挡）。这个脚本帮你自动筛出来。

---

## 原理（大白话）

**第一步：认脸**
你给几张目标人物的参考照片，脚本提取她的"人脸特征向量"（就是一组数字，代表这张脸长什么样）。

**第二步：逐帧扫描**
按你设定的频率（默认每秒1帧）把视频切开，对每一帧：
1. 检测这帧里有没有人脸
2. 把检测到的每张脸和参考向量比较相似度（余弦相似度）
3. 相似度超过阈值（默认0.45）= 目标人物出现了

**第三步：质量过滤**
找到目标人物之后，还要过滤掉质量差的：
- 偏角太大（侧脸超过40°丢弃）
- 模糊（Laplacian方差 < 80丢弃）

**第四步：综合评分排序**
`综合分 = 相似度×0.6 + 清晰度×0.4`
取分最高的前N张，按时间顺序保存。

**输出：**
- 推荐帧图片（文件名含时间码+相似度）
- `report.csv`：每帧的详细评分

---

## 环境搭建

### 方式一：Conda 虚拟环境（推荐，适配 Windows + NVIDIA GPU）

```powershell
# 1. 创建虚拟环境（Python 3.10 对 onnxruntime-gpu 兼容性最好）
conda create -n faceextract python=3.10 -y
conda activate faceextract
> Get-Command python

```

```powershell
问题：为什么 conda activate faceextract 在 powershell上行不通，在CMD上就可以？
这是 Conda 的经典 Windows 问题。Conda 默认只初始化了 CMD，没初始化 PowerShell。
解决方法：conda init powershell
然后关闭并重新打开 PowerShell，之后 conda activate 就能用了

```

# 2. 安装 CUDA 工具包（通过 conda，免去手动装 CUDA）
conda install -c conda-forge cudatoolkit=11.8 cudnn=8.9 -y

# 3. 安装 Python 依赖（GPU 版，注意版本锁定）
pip install numpy==1.26.4 opencv-python-headless==4.11.0.86 insightface
pip install onnxruntime-gpu

# 4. 验证 GPU 可用
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
> 应输出: ['CUDAExecutionProvider', 'CPUExecutionProvider']

python -c "import cv2; print(cv2.__version__)"

```

> ⚠️ **不要同时装 `onnxruntime` 和 `onnxruntime-gpu`**，会冲突！
> 如果之前装过 CPU 版：`pip uninstall onnxruntime -y && pip install onnxruntime-gpu`

### 方式二：pip 直装（CPU 模式，Mac / 无 GPU 机器）

```bash
pip install insightface opencv-python onnxruntime numpy
```

### 方式三：Conda + CPU（Mac M系列芯片）

```bash
conda create -n faceextract python=3.10 -y
conda activate faceextract
pip install insightface opencv-python onnxruntime numpy
```

---

## GPU vs CPU 速度对比

| 环境 | 40分钟视频 @ 1fps | 说明 |
|------|------------------|------|
| **RTX 3060 12GB** (CUDA) | **~2-3 分钟** | 推荐 ✅ |
| M2 MacBook Air (CPU) | ~12 分钟 | 可用但慢 |
| i7-11700K (CPU) | ~8 分钟 | 仅 CPU 核心 |

脚本会自动检测：有 GPU 用 GPU，没有自动回退 CPU，无需手动切换。

---

## 使用方法

### 基础用法

```bash
# 先激活环境
conda activate faceextract

# 运行
python extract_face_frames.py \
    --video /path/to/video.mp4 \
    --refs ref1.jpg ref2.jpg ref3.jpg \
    --output ./output_frames
```

### Windows PowerShell 示例

```powershell
conda activate faceextract

python D:\AI\amazing-ai-prompts\scripts\extract_face_frames.py `
    --video "D:\Videos\drama_ep01.mp4" `
    --refs "D:\Photos\actress_front.jpg" "D:\Photos\actress_side.jpg" `
    --output "D:\AI\face_output" `
    --top 200
```

### 完整参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--video` | （必填） | 输入视频路径（mp4/mov/avi 均可） |
| `--refs` | （必填） | 目标人物参考照片（1-5张，正脸清晰最佳） |
| `--output` | `./output_frames` | 输出目录（自动创建） |
| `--top` | 100 | 最多保留多少张 |
| `--fps` | 1 | 每秒采样几帧（越高越慢但不漏帧） |
| `--sim` | 0.45 | 相似度阈值（0-1，越高越严格） |
| `--angle` | 40 | 最大偏角°（过滤大角度侧脸） |
| `--blur` | 80 | 最低清晰度分（Laplacian 方差） |

---

## 参考照片要求

- 正脸或轻微侧脸（偏角 < 45°）
- 面部清晰，无运动模糊
- 光线均匀，无强逆光
- 分辨率建议 512px 以上
- 提供 2-3 张不同角度效果更好

---

## 输出说明

```
output_frames/
├── frame_0001234_00-41.20_sim0.78.jpg   # 文件名: 帧号_时间码_相似度
├── frame_0002567_01-25.67_sim0.82.jpg
├── ...
└── report.csv   # 详细报告
```

`report.csv` 列说明：

| 列名 | 说明 |
|------|------|
| frame_idx | 帧序号 |
| timecode | 时间码（分:秒） |
| similarity | 与目标人物的相似度（0-1） |
| blur_score | 清晰度分（越高越清晰） |
| yaw_deg | 人脸偏角（越小越正脸） |
| composite | 综合评分（排序依据） |
| filename | 图片文件名 |

---

## 常见问题

**Q: 找不到目标人物（结果为0）**
- 降低 `--sim` 阈值（试试 0.35）
- 检查参考照片质量（是否正脸清晰）
- 确认视频里真的有这个人

**Q: 找到了很多不像的人**
- 提高 `--sim` 阈值（试试 0.55-0.65）

**Q: 帧都很模糊**
- 降低 `--blur` 阈值（试试 50）
- 或者 `--fps 2` 提高采样率，选更多候选帧

**Q: 运行报错找不到模型**
- 确保网络畅通，首次运行会自动下载 InsightFace buffalo_l 模型（~500MB）
- 或手动下载到 `~/.insightface/models/`（Windows 为 `C:\Users\<用户名>\.insightface\models\`）

**Q: `onnxruntime-gpu` 安装后仍然用 CPU**
- 检查 CUDA 版本兼容性：`nvidia-smi` 查看驱动版本
- onnxruntime-gpu 1.17+ 需要 CUDA 11.8 或 12.x
- 如果 conda 装了 cudatoolkit 还不行，试试设环境变量：
  ```powershell
  $env:CUDA_PATH = "C:\Users\<用户名>\miniconda3\envs\faceextract\Library"
  ```

**Q: Windows 上报 `DLL load failed`**
- 安装 Visual C++ Redistributable：https://aka.ms/vs/17/release/vc_redist.x64.exe
- 重启终端后重试

---

## 依赖版本参考（已测试）

| 包 | 版本 | 说明 |
|---|------|------|
| Python | 3.10.x | 3.11 也可，3.12 对 insightface 兼容性待验证 |
| insightface | 0.7.3+ | 人脸检测+识别 |
| opencv-python | 4.11.x | 视频读取、图像处理（**不要用 4.12+**，它要求 numpy≥2 与 insightface 冲突） |
| onnxruntime-gpu | 1.17+ | GPU 推理（需 CUDA 11.8/12.x） |
| numpy | 1.26.4 | **必须 <2.0**（insightface 的 Cython 扩展不兼容 numpy 2.x） |
| cudatoolkit | 11.8 | 通过 conda 安装 |
| cudnn | 8.9 | 通过 conda 安装 |

---

> 首次运行需下载 InsightFace buffalo_l 模型，约 500MB，之后缓存本地。
