# AI 生图踩坑记录

> 记录实际使用中遇到的问题、平台、以及解决方案。
> 持续更新 📝

---

## 问题记录

### ❓ 全身图人脸模糊/马赛克

**平台：** ChatGPT (GPT Image-2)
**时间：** 2026-05-03
**现象：** 生成全身图时，人物五官细节糊，放大看像马赛克

**原因：**
全身图中人脸占画面比例小，AI 分配给脸部的像素不足，细节无法呈现。

**解决方案：**
- 提示词加 `upper body portrait` / `bust shot` 改为半身构图
- 生完全身图后，单独再生一张面部特写
- 用 **CodeFormer**（免费）在线修复人脸：https://huggingface.co/spaces/sczhou/CodeFormer
- 本地跑 SD/ComfyUI 时开启 **ADetailer 插件**，自动检测人脸并重绘

---

### ❓ ChatGPT 生图分辨率只有 1086×1448 / 72PPI

**平台：** ChatGPT Plus (GPT Image-2)
**时间：** 2026-05-03
**现象：** 生成图片清晰度不高，元数据显示 72 像素/英寸

**原因：**
- GPT Image 最高输出约 1024×1536，这是平台上限，Plus 会员也一样
- 72 PPI 只是元数据默认值，不影响屏幕显示效果

**解决方案：**
- 用 AI 放大工具处理：Topaz Gigapixel（付费）/ Real-ESRGAN（免费开源）
- 换用 FLUX.1 dev 可输出更高分辨率（最高约 2048px）
- Midjourney 默认分辨率更高

---

## 📌 待研究问题

> 遇到新问题随时追加

