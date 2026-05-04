# 项目需求全景图 & 优先级

> 整理日期：2026-05-04
> 项目：AI 辅助影视剧前期制作（定妆照 + 静态分镜）
> 团队：2人小工作室
> 设备：MacBook Air M2 16GB（无独立显卡）

---

## 项目背景

两部剧同步筹备：
- **剧目A**：现代都市爱情剧（娱乐圈/名利场）
- **剧目B**：中国古代奇幻剧（志怪/妖/仙/法术）

核心目标：用 AI 工具完成传统需要大团队+高预算才能做的前期视觉工作，包括：
1. 角色**定妆照**（角色服装/造型视觉确认）
2. **静态分镜故事板**（漫画/绘本图册风格，用于剧本可视化）

已有资源：
- 真实模特面部照片（已授权 AI 使用）
- 约40分钟视频素材（含目标演员）

---

## 需求全景 & 优先级

### 🔴 P0 — 立即要做（验证期核心）

| # | 需求 | 目标 | 推荐工具 |
|---|------|------|---------|
| 1 | **真人换脸到AI角色图** | 把授权模特的脸注入到定妆照中，实现"这就是这个角色的样子" | TapNow Face Swap / liblib.art InstantID |
| 2 | **角色一致性验证** | 同一个角色在不同镜头/场景中保持五官、服装、气质统一 | TapNow Character Lock / liblib.tv |
| 3 | **从视频素材中提取模特优质帧** | 为 LoRA 训练或 InstantID 准备高质量参考照片 | `extract_face_frames.py`（已完成） |
| 4 | **注册并试用 liblib.tv 和 tapnow.ai** | 判断哪个平台更适合你的工作流，定下主力工具 | 两个都注册，各跑一个测试分镜 |

---

### 🟠 P1 — 主线工作流（确定工具后开始）

| # | 需求 | 目标 | 推荐工具 |
|---|------|------|---------|
| 5 | **静态分镜生产（现代剧）** | 娱乐圈场景的分镜图册，漫画风格，角色+环境一致 | TapNow 画布 / MJ `--sref --oref` |
| 6 | **静态分镜生产（古装剧）** | 志怪/仙侠场景分镜，古风画风统一 | 同上，古风 `--sref` 风格码 |
| 7 | **角色定妆照（正式出图）** | 每个主角至少3套造型，前/侧/全身 | liblib.tv / liblib.art InstantID |
| 8 | **环境一致性** | 同一场景（如古镇夜市、公司大厅）在不同镜头保持视觉统一 | TapNow 节点画布 / MJ `--sref` |

---

### 🟡 P2 — 效率工具（边做边建）

| # | 需求 | 目标 | 工具/文档 |
|---|------|------|---------|
| 9 | **灵感草图 → 提示词** | 把脑海中的场景快速转化为可出图的英文提示词 | `prompt-guide-image2-mj.md` + GPT Image2 |
| 10 | **拉片 → 提取可复现构图** | 看到好片，提炼镜头语言，存入自己的提示词库 | `film-analysis-prompt-extraction.md` + ffmpeg |
| 11 | **视频素材切割** | 把大体积视频（1G+）按时间段切成小片段，方便处理 | `cut_video.py`（已完成） |
| 12 | **构图灵感库建设** | 把拉片成果、好用的提示词持续积累到 `prompts-collection.md` | 手动维护，每次拉片后更新 |

---

### 🟢 P3 — 待探索（暂缓）

| # | 需求 | 说明 |
|---|------|------|
| 13 | **LoRA 训练** | 用提取的优质帧训练专属模型，角色还原度更高；需云端 GPU，等 P0 验证完再做 |
| 14 | **批量自动化出图** | GPT Image2 API 脚本化批量跑分镜草图；等工作流稳定后再考虑 |
| 15 | **视频生成** | 把分镜转为短视频片段（Kling/Runway）；现阶段只做静图，暂缓 |
| 16 | **AI 配音/音效** | 影片后期需求，不在当前范围 |

---

## 当前推荐工具栈

```
定妆照（精品）     → liblib.tv / TapNow + InstantID
分镜图册（主力）   → TapNow 画布 / liblib.tv
分镜草图（快速验证）→ GPT Image2 / Midjourney Basic
视频素材处理       → cut_video.py + extract_face_frames.py（本地脚本）
提示词参考         → prompt-guide-image2-mj.md
拉片分析           → film-analysis-prompt-extraction.md
```

**月度预算建议（验证期）：**
| 工具 | 费用 |
|------|------|
| ChatGPT Plus（GPT Image2） | $20/月 |
| Midjourney Basic | $10/月 |
| liblib.tv / TapNow 试用 | 免费起步 |
| **合计** | **$30/月** |

---

## 四周行动计划

### Week 1：验证工具
- [ ] 安装 ffmpeg + Python 依赖
- [ ] 用 `cut_video.py` 切出目标演员片段
- [ ] 用 `extract_face_frames.py` 提取优质参考帧
- [ ] 注册 liblib.tv + tapnow.ai，各跑一个分镜测试
- [ ] 注册 Midjourney Basic，测试 `--oref` 人脸锁定

### Week 2：定妆照
- [ ] 确定主力换脸工具（TapNow or liblib）
- [ ] 完成两部剧主角各1套定妆照（前/侧/全身）
- [ ] 验证角色一致性质量

### Week 3：分镜流程
- [ ] 选定分镜主力工具
- [ ] 完成一集（约30镜）分镜图册
- [ ] 验证环境一致性

### Week 4：流程固化
- [ ] 整理有效提示词存入 `prompts-collection.md`
- [ ] 评估是否需要升级订阅（MJ Standard / TapNow 付费）
- [ ] 评估是否需要 LoRA 训练

---

## 已完成的工具和文档

| 文件 | 说明 |
|------|------|
| `research/ai-film-preproduction-research.md` | AI影视前期制作全景调研 |
| `research/face-quality-assessment.md` | 人脸质量评估方法 + 模型谱系 |
| `research/prompt-guide-image2-mj.md` | 提示词速查手册 |
| `research/film-analysis-prompt-extraction.md` | 拉片指南 |
| `scripts/extract_face_frames.py` | 视频人脸帧提取脚本 |
| `scripts/cut_video.py` | 视频切割脚本 |

---

*整理：虾爬子🦐 | 基于2026-05-04对话内容提炼*
