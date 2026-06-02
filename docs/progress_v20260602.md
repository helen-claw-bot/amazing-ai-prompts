# 换脸工作流进度

> 最后更新：2026-06-02

---

## 目标

用 ComfyUI + Klein-9B 模型，给"成何体统"视频素材做换脸，并支持姿势编辑，最终为 LoRA 训练准备人像数据集。

---

## 当前状态：卡在姿势编辑

| 子任务 | 状态 | 问题 |
|---|---|---|
| 换脸/换头（参考图+主体脸） | ✅ 通过 | 头偏大，像大头娃娃 |
| 手动摆姿势再换脸 | ✅ 通过 | 坐/站姿切换做不到；改姿势后人脸跟着变 |
| DWPose 提取姿势 → 3D Editor 微调 | ❌ 阻塞 | DWPose 输出坐标是几十万级大整数，3D Editor 期望像素值，直接溢出 NaN |

**当前 workflow 文件**：  
`C:\Users\home\Documents\ComfyUI\user\default\workflows\faceswap_test2.json`  
`extract_pose.json`（同目录）

---

## 姿势编辑阻塞的绕过方案（待选一）

1. **放弃 3D Editor，直接用 DWPose 骨骼图**：只做同姿势换脸，不改姿势
2. **手动摆姿势（不接 DWPose）**：在 3D Editor 里从零摆，换脸效果会跟着姿势跑
3. **找能接受 DWPose 输出的其他 3D Editor 节点**

---

## LoRA 素材进度

- 视频来源：`E:\AI\downloads\CHTT` S01 系列
- **S01E21 / S01E22**：HDR 色彩空间问题，抽帧结果灰蒙蒙 → 需要 ffmpeg tonemap（见坑6）
- 素材需求：正脸+高清+中性表情（已用 `extract_face_frames.py` + InsightFace 筛选）
- 已筛选结果放在：`E:\AI\ComfyUI_data\input\`

---

## 模型 & 环境

- **换脸模型**：`Flux/flux-2-klein-9b-fp8.safetensors` + `DarkKlein9b`（换脸强，但姿势编辑弱于 Klein v1）
- **ComfyUI**：`C:\Users\home\Documents\ComfyUI`，Python 3.12，torch 2.8.0+cu129
- **InsightFace/faceextract**：conda 环境，torch 2.11.0+cu128
- 环境坑已全部解决，见 [ComfyUI 换脸工作流踩坑记录.md](../ComfyUI%20换脸工作流踩坑记录.md)

---

## 下一步（按优先级）

1. **决策**：姿势编辑用哪个绕过方案（见上）
2. **修头大问题**：换脸后头偏大，调整 faceswap_test2.json 里的融合/缩放参数
3. **补 HDR 素材**：对 S01E21/E22 视频跑 ffmpeg tonemap 重新抽帧，补充 LoRA 训练集
