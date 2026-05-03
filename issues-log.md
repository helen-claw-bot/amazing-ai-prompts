# AI 生图踩坑记录

> 记录实际使用中遇到的问题、平台、以及解决方案。
> 持续更新 📝

---

## 问题记录

### ❓ 全身图人脸模糊/分辨率不足

**平台：** ChatGPT (GPT Image-2)
**时间：** 2026-05-03
**现象：** 生成全身图时人物五官糊烂，放大看像马赛克；整体分辨率约 1024×1536，Plus 会员也无法突破

**原因：**
- 全身图中人脸占画面比例小，AI 分配给脸部的像素不足
- GPT Image 平台输出上限约 1024×1536，72 PPI 是元数据默认值，不影响屏幕效果但打印不够用

**解决方案：**
- 提示词加 `upper body portrait` / `bust shot` 改为半身构图，让脸占更大比例
- 生完全身图后，单独再生一张面部特写
- 用 **CodeFormer**（免费在线）修复人脸：https://huggingface.co/spaces/sczhou/CodeFormer
- 用 **Real-ESRGAN**（免费）或 Topaz Gigapixel（付费）放大整图
- 换用 FLUX.1 dev（最高约 2048px）或 Midjourney（默认更高分辨率）
- 本地跑 SD/ComfyUI 时开启 **ADetailer 插件**，自动检测人脸并重绘

---

## 📌 待研究问题

> 遇到新问题随时追加
