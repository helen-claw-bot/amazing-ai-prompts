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

## 安装依赖

```bash
pip install insightface opencv-python onnxruntime numpy
```

> M2 Mac 可正常运行，不需要独立显卡，首次运行会自动下载模型（约500MB）

---

## 使用方法

### 基础用法

```bash
python extract_face_frames.py \
    --video /path/to/video.mp4 \
    --refs ref1.jpg ref2.jpg ref3.jpg \
    --output ./output_frames
```

### 完整参数

```bash
python extract_face_frames.py \
    --video /path/to/video.mp4 \        # 视频路径（mp4/mov/avi均可）
    --refs ref1.jpg ref2.jpg \           # 参考照片（1-5张，正脸清晰最佳）
    --output ./output_frames \           # 输出目录（自动创建）
    --top 100 \                          # 最多保留多少张（默认100）
    --fps 1 \                            # 每秒采样几帧（默认1，越高越慢但不漏帧）
    --sim 0.45 \                         # 相似度阈值（0-1，越高越严格，默认0.45）
    --angle 40 \                         # 最大偏角°（默认40）
    --blur 80                            # 最低清晰度分（默认80）
```

### 实际示例

```bash
# 40分钟视频，提取女主角的优质帧
python extract_face_frames.py \
    --video drama_ep01.mp4 \
    --refs actress_front.jpg actress_side.jpg \
    --output ./actress_frames \
    --top 200 \
    --fps 1

# 如果找不到人（结果为0），尝试降低阈值
python extract_face_frames.py ... --sim 0.35

# 如果结果太多太杂，提高阈值
python extract_face_frames.py ... --sim 0.55
```

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

## 速度参考（M2 MacBook Air）

| 视频时长 | 采样fps | 预计时间 |
|---------|---------|---------|
| 10分钟 | 1fps | ~3分钟 |
| 40分钟 | 1fps | ~12分钟 |
| 40分钟 | 2fps | ~24分钟 |

> 首次运行需下载 InsightFace buffalo_l 模型，约500MB，之后缓存本地

---

## 常见问题

**Q: 找不到目标人物（结果为0）**
- 降低 `--sim` 阈值（试试0.35）
- 检查参考照片质量（是否正脸清晰）
- 确认视频里真的有这个人

**Q: 找到了很多不像的人**
- 提高 `--sim` 阈值（试试0.55-0.65）

**Q: 帧都很模糊**
- 降低 `--blur` 阈值（试试50）
- 或者 `--fps 2` 提高采样率，选更多候选帧

**Q: 运行报错找不到模型**
- 确保网络畅通，首次运行会自动下载
- 或手动下载 buffalo_l 模型到 `~/.insightface/models/`
